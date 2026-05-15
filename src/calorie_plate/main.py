from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional
import json

from database import engine, Food
from inference import detect as run_detection

# 1. 初始化 FastAPI 应用（这就相当于建好了一个服务器外壳）
app = FastAPI(
    title="Smart Calorie Plate API",
    description="AI卡路里餐盘的后端接口",
    version="1.0.0"
)
class FoodItem(BaseModel):
    food_id: int      # 食物在数据库里的 ID
    weight_g: float   # 称重传感器传来的克数

# 定义一整盘饭的接收格式（一个列表）
class MealRequest(BaseModel):
    items: List[FoodItem]

# 2. 数据库对话管家（依赖项）：每次有人来查数据，它负责开门，查完自动关门
def get_session():
    with Session(engine) as session:
        yield session


def _compute_nutrition(items: List[FoodItem], session: Session) -> dict:
    """共用的营养累加 + 健康建议逻辑。"""
    total_kcal = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
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


# 3. 接口一：获取所有食物列表（给前端 UI 渲染列表用的）
@app.get("/foods")
def get_all_foods(session: Session = Depends(get_session)):
    statement = select(Food)
    foods = session.exec(statement).all()
    return foods

# 4. 接口二：通过 ID 查询单个食物（给视觉模型识别后调用的）
@app.get("/foods/{food_id}")
def get_food_by_id(food_id: int, session: Session = Depends(get_session)):
    food = session.get(Food, food_id)
    if not food:
        # 如果找不到这个 ID，返回 404 报错
        raise HTTPException(status_code=404, detail="数据库里没有找到这个食物！")
    return food

# 5. Core Analysis Engine: Receives food items and weights, returns total nutrition and health advice
@app.post("/meal/analyze")
def analyze_meal(request: MealRequest, session: Session = Depends(get_session)):
    return _compute_nutrition(request.items, session)


# 6. 视觉识别接口：上传图片 → YOLO 模型识别 → 返回检测到的 food_id 列表
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

    # 用数据库里的中文名做一下补充，前端展示更友好
    enriched = []
    for det in detections:
        food = session.get(Food, det["food_id"])
        enriched.append({
            **det,
            "name_zh": food.name_zh if food else None,
        })

    return {"detections": enriched}


# 7. 一站式接口：上传图片 + 每个检测框对应的重量 → 直接返回完整营养分析
#    weights 形如 JSON 字符串 "[120, 80]"，按 detect 返回的顺序对齐
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
        # Swagger UI 有时会把字符串再包一层引号，json.loads 后还是 str
        if isinstance(parsed, str):
            parsed = json.loads(parsed.strip())
        if isinstance(parsed, list) and all(isinstance(w, (int, float)) for w in parsed):
            weight_list = [float(w) for w in parsed]
        else:
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        # 回退：支持 "120, 80, 50" 这样的逗号分隔写法
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
