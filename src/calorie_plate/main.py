from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import Session, SQLModel, select
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from datetime import date
import json

from database import engine, Food, DietNote, UserProfile, Meal
from inference import detect as run_detection
from utils import calculate_nutrition_targets

# 1. 初始化 FastAPI 应用（这就相当于建好了一个服务器外壳）
app = FastAPI(
    title="Smart Calorie Plate API",
    description="AI卡路里餐盘的后端接口",
    version="1.0.0",
)

# 跨域：开发时前端跑在 :3000，打包后前端由本服务同源托管。全部放行最省心。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    _migrate_add_columns()
    _ensure_seed_data()


def _migrate_add_columns():
    """轻量迁移：create_all 不会给已存在的表补新列，这里手动补齐。"""
    from sqlalchemy import text

    with engine.begin() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(userprofile)"))}
        if cols and "name" not in cols:
            conn.execute(text("ALTER TABLE userprofile ADD COLUMN name VARCHAR"))


# ---------------------------------------------------------------------------
# 输入归一化：前端用的是 sedentary/light/... 和 fatloss/maintain/bulk，
# 后端算法要的是活动系数(float)和 fat_loss/balance/muscle_gain。两边都兼容。
# ---------------------------------------------------------------------------
ACTIVITY_MAP = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
}
DIET_MAP = {
    "fatloss": "fat_loss",
    "maintain": "balance",
    "bulk": "muscle_gain",
    # 也接受后端原生写法
    "fat_loss": "fat_loss",
    "balance": "balance",
    "muscle_gain": "muscle_gain",
}


def normalize_activity(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    key = str(value).strip().lower()
    if key in ACTIVITY_MAP:
        return ACTIVITY_MAP[key]
    try:
        return float(key)
    except ValueError:
        return 1.375  # 合理默认值


def normalize_diet(value: str) -> str:
    return DIET_MAP.get(str(value).strip().lower(), "balance")


class FoodItem(BaseModel):
    food_id: int      # 食物在数据库里的 ID
    weight_g: float   # 称重传感器传来的克数


class MealRequest(BaseModel):
    items: List[FoodItem]


def get_session():
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# 共用营养累加 + 健康建议
# ---------------------------------------------------------------------------
def _compute_nutrition(items: List[FoodItem], session: Session) -> dict:
    total_kcal = total_protein = total_carbs = total_fat = 0.0
    breakdown = []

    for item in items:
        food = session.get(Food, item.food_id)
        if not food:
            raise HTTPException(status_code=404, detail=f"Food with ID {item.food_id} not found")

        ratio = item.weight_g / 100.0
        kcal = food.kcal_per_100g * ratio
        protein = food.protein_per_100g * ratio
        carbs = food.carbs_per_100g * ratio
        fat = food.fat_per_100g * ratio

        total_kcal += kcal
        total_protein += protein
        total_carbs += carbs
        total_fat += fat

        breakdown.append({
            "food_id": food.id,
            "name_en": food.name_en,
            "name_zh": food.name_zh,
            "weight_g": item.weight_g,
            "kcal": round(kcal, 1),
            "protein": round(protein, 1),
            "carbs": round(carbs, 1),
            "fat": round(fat, 1),
        })

    advice = []
    if total_protein < 20:
        advice.append("Protein intake is a bit low. Consider adding eggs, chicken breast, or soy products to your meal.")
    if total_carbs > 80:
        advice.append("Carbohydrate levels are high. Be mindful of your remaining starch portions for the rest of the day.")
    if not advice:
        advice.append("Great job! This meal is nutritionally well-balanced.")

    return {
        "total_kcal": round(total_kcal, 1),
        "total_protein": round(total_protein, 1),
        "total_carbs": round(total_carbs, 1),
        "total_fat": round(total_fat, 1),
        "items": breakdown,
        "advice": advice,
    }


def _ensure_seed_data():
    """启动时若食物表为空，自动灌入 18 种食物，省去手动跑 seed_data.py。"""
    with Session(engine) as session:
        if session.exec(select(Food)).first() is not None:
            return
        try:
            from seed_data import initial_foods
        except Exception:
            return
        for food in initial_foods:
            session.add(food)
        session.commit()


# ---------------------------------------------------------------------------
# 食物 / 营养计算接口
# ---------------------------------------------------------------------------
@app.get("/foods")
def get_all_foods(session: Session = Depends(get_session)):
    return session.exec(select(Food)).all()


@app.get("/foods/{food_id}")
def get_food_by_id(food_id: int, session: Session = Depends(get_session)):
    food = session.get(Food, food_id)
    if not food:
        raise HTTPException(status_code=404, detail="数据库里没有找到这个食物！")
    return food


@app.post("/meal/analyze")
def analyze_meal(request: MealRequest, session: Session = Depends(get_session)):
    return _compute_nutrition(request.items, session)


@app.post("/meal/detect")
async def detect_meal(
    image: UploadFile = File(...),
    conf: float = 0.25,
    session: Session = Depends(get_session),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件 (image/*)")

    image_bytes = await image.read()
    try:
        detections = run_detection(image_bytes, conf=conf)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    enriched = []
    for det in detections:
        food = session.get(Food, det["food_id"])
        enriched.append({
            **det,
            "name_zh": food.name_zh if food else None,
        })

    return {"detections": enriched}


@app.post("/meal/analyze-image")
async def analyze_meal_from_image(
    image: UploadFile = File(...),
    weights: str = Form(...),
    conf: float = Form(0.25),
    session: Session = Depends(get_session),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件 (image/*)")

    raw = weights.strip().strip('"').strip("'").strip()
    weight_list: list[float] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, str):
            parsed = json.loads(parsed.strip())
        if isinstance(parsed, list) and all(isinstance(w, (int, float)) for w in parsed):
            weight_list = [float(w) for w in parsed]
        else:
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        try:
            inner = raw.strip("[]")
            weight_list = [float(x) for x in inner.split(",") if x.strip()]
            if not weight_list:
                raise ValueError
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"weights 必须是数字列表，例如 [120, 80] 或 120,80（收到：{weights!r}）",
            )

    image_bytes = await image.read()
    try:
        detections = run_detection(image_bytes, conf=conf)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if len(detections) != len(weight_list):
        raise HTTPException(
            status_code=400,
            detail=f"检测到 {len(detections)} 个食物，但提供了 {len(weight_list)} 个重量",
        )

    items = [
        FoodItem(food_id=det["food_id"], weight_g=float(w))
        for det, w in zip(detections, weight_list)
    ]
    result = _compute_nutrition(items, session)
    result["detections"] = detections
    return result


# ---------------------------------------------------------------------------
# 用户档案：创建 + 列表 + 单查（支持多账号切换）
# ---------------------------------------------------------------------------
class UserProfileCreate(BaseModel):
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    activity_level: float | str
    diet_mode: str
    name: Optional[str] = None  # 账号显示名，可选


@app.post("/api/user-profile/")
def create_user_profile(
    profile: UserProfileCreate,
    session: Session = Depends(get_session),
):
    """接收用户身体数据，计算目标热量与三大营养素，并保存 UserProfile。"""
    activity = normalize_activity(profile.activity_level)
    diet = normalize_diet(profile.diet_mode)

    targets = calculate_nutrition_targets(
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=activity,
        diet_mode=diet,
    )

    user = UserProfile(
        name=profile.name,
        age=profile.age,
        gender=profile.gender,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        activity_level=activity,
        diet_mode=diet,
        target_calories=targets["target_calories"],
        target_protein_g=targets["target_protein_g"],
        target_fat_g=targets["target_fat_g"],
        target_carbs_g=targets["target_carbs_g"],
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    return {"user_profile": user, "targets": targets}


@app.get("/api/user-profiles/")
def list_user_profiles(session: Session = Depends(get_session)):
    """列出所有账号，供前端做账号切换。"""
    return session.exec(select(UserProfile).order_by(UserProfile.id.desc())).all()


@app.get("/api/user-profile/{user_id}")
def get_user_profile(user_id: int, session: Session = Depends(get_session)):
    user = session.get(UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="找不到该用户档案")
    return user


@app.delete("/api/user-profile/{user_id}")
def delete_user_profile(user_id: int, session: Session = Depends(get_session)):
    user = session.get(UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="找不到该用户档案")
    session.delete(user)
    session.commit()
    return {"ok": True, "deleted_id": user_id}


# ---------------------------------------------------------------------------
# 餐食记忆：确认摄入(写入) + 历史(读取) + 当日汇总
# ---------------------------------------------------------------------------
class MealCreate(BaseModel):
    user_id: Optional[int] = None
    total_kcal: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    items: List[dict] = []
    advice: Optional[str] = None


@app.post("/api/meals/")
def create_meal(payload: MealCreate, session: Session = Depends(get_session)):
    meal = Meal(
        user_id=payload.user_id,
        total_kcal=round(payload.total_kcal, 1),
        total_protein_g=round(payload.total_protein_g, 1),
        total_carbs_g=round(payload.total_carbs_g, 1),
        total_fat_g=round(payload.total_fat_g, 1),
        items_json=json.dumps(payload.items, ensure_ascii=False),
        advice=payload.advice,
    )
    session.add(meal)
    session.commit()
    session.refresh(meal)
    return _meal_to_dict(meal)


@app.get("/api/meals/")
def list_meals(
    user_id: Optional[int] = None,
    on_date: Optional[str] = None,
    session: Session = Depends(get_session),
):
    statement = select(Meal)
    if user_id is not None:
        statement = statement.where(Meal.user_id == user_id)
    if on_date:
        try:
            d = date.fromisoformat(on_date)
            statement = statement.where(Meal.log_date == d)
        except ValueError:
            raise HTTPException(status_code=400, detail="on_date 需为 YYYY-MM-DD")
    statement = statement.order_by(Meal.created_at.desc())
    return [_meal_to_dict(m) for m in session.exec(statement).all()]


@app.get("/api/meals/summary")
def meals_summary(
    user_id: Optional[int] = None,
    on_date: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """某天（默认今天）的累计摄入，用于 Dashboard 进度环/进度条。"""
    target_date = date.today()
    if on_date:
        try:
            target_date = date.fromisoformat(on_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="on_date 需为 YYYY-MM-DD")

    statement = select(Meal).where(Meal.log_date == target_date)
    if user_id is not None:
        statement = statement.where(Meal.user_id == user_id)
    meals = session.exec(statement).all()

    return {
        "date": target_date.isoformat(),
        "meal_count": len(meals),
        "total_kcal": round(sum(m.total_kcal for m in meals), 1),
        "total_protein_g": round(sum(m.total_protein_g for m in meals), 1),
        "total_carbs_g": round(sum(m.total_carbs_g for m in meals), 1),
        "total_fat_g": round(sum(m.total_fat_g for m in meals), 1),
    }


@app.delete("/api/meals/{meal_id}")
def delete_meal(meal_id: int, session: Session = Depends(get_session)):
    meal = session.get(Meal, meal_id)
    if not meal:
        raise HTTPException(status_code=404, detail="找不到该餐记录")
    session.delete(meal)
    session.commit()
    return {"ok": True, "deleted_id": meal_id}


def _meal_to_dict(meal: Meal) -> dict:
    try:
        items = json.loads(meal.items_json) if meal.items_json else []
    except json.JSONDecodeError:
        items = []
    return {
        "id": meal.id,
        "user_id": meal.user_id,
        "log_date": meal.log_date.isoformat(),
        "created_at": meal.created_at.isoformat(),
        "total_kcal": meal.total_kcal,
        "total_protein_g": meal.total_protein_g,
        "total_carbs_g": meal.total_carbs_g,
        "total_fat_g": meal.total_fat_g,
        "items": items,
        "advice": meal.advice,
    }


# ---------------------------------------------------------------------------
# 营养推荐：根据目标 vs 已摄入，给出建议 + 推荐补充的食物
# ---------------------------------------------------------------------------
class RecommendRequest(BaseModel):
    target_calories: float
    target_protein_g: float
    target_carbs_g: float
    target_fat_g: float
    actual_calories: float = 0.0
    actual_protein_g: float = 0.0
    actual_carbs_g: float = 0.0
    actual_fat_g: float = 0.0


@app.post("/api/recommend")
def recommend(payload: RecommendRequest, session: Session = Depends(get_session)):
    remaining = {
        "calories": round(payload.target_calories - payload.actual_calories, 1),
        "protein_g": round(payload.target_protein_g - payload.actual_protein_g, 1),
        "carbs_g": round(payload.target_carbs_g - payload.actual_carbs_g, 1),
        "fat_g": round(payload.target_fat_g - payload.actual_fat_g, 1),
    }

    tips: list[str] = []
    suggested_food_field = None

    if remaining["calories"] <= 0:
        tips.append("Calorie goal reached for today. Avoid overeating.")
    else:
        tips.append(f"About {remaining['calories']:.0f} kcal left for today.")

    # 找出缺口最大的宏量，给针对性建议 + 推荐高含量食物
    if remaining["protein_g"] > 15:
        tips.append(f"{remaining['protein_g']:.0f}g of protein still needed. Add some quality protein.")
        suggested_food_field = "protein_per_100g"
    elif remaining["protein_g"] < -10:
        tips.append("Protein is over target. Consider easing up on meat and eggs.")

    if remaining["carbs_g"] > 30:
        tips.append(f"{remaining['carbs_g']:.0f}g of carbs still needed. Add whole grains or fruit.")
        if suggested_food_field is None:
            suggested_food_field = "carbs_per_100g"
    elif remaining["carbs_g"] < -20:
        tips.append("Carbs are high. Consider reducing your staple portions.")

    if remaining["fat_g"] < -10:
        tips.append("Fat is high. Watch out for oils and fried foods.")

    if len(tips) == 1:  # 只有热量那一句，说明三大宏量都比较均衡
        tips.append("Your macros are well balanced. Keep it up!")

    suggestions = []
    if suggested_food_field:
        foods = session.exec(select(Food)).all()
        foods.sort(key=lambda f: getattr(f, suggested_food_field), reverse=True)
        for f in foods[:4]:
            suggestions.append({
                "food_id": f.id,
                "name_zh": f.name_zh,
                "name_en": f.name_en,
                "kcal_per_100g": f.kcal_per_100g,
                "protein_per_100g": f.protein_per_100g,
                "carbs_per_100g": f.carbs_per_100g,
                "fat_per_100g": f.fat_per_100g,
            })

    return {"remaining": remaining, "tips": tips, "suggested_foods": suggestions}


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# 静态前端托管：把 Next 导出的静态站点挂在根路径（必须放在所有 API 路由之后）。
# 打包后整个 app 同源访问，彻底规避 file:// / 跨端口带来的跳转失效问题。
# ---------------------------------------------------------------------------
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "smart-plate-ui" / "out"

if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
