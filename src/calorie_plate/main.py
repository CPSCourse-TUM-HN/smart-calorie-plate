from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List
from database import engine, Food

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
    total_kcal = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fat = 0.0
    
    for item in request.items:
        food = session.get(Food, item.food_id)
        if not food:
            raise HTTPException(status_code=404, detail=f"Food with ID {item.food_id} not found")
            
        ratio = item.weight_g / 100.0
        total_kcal += food.kcal_per_100g * ratio
        total_protein += food.protein_per_100g * ratio
        total_carbs += food.carbs_per_100g * ratio
        total_fat += food.fat_per_100g * ratio
        
    # M5.7 Health Advice Rule Engine (English Version)
    advice = []
    
    # Logic for low protein
    if total_protein < 20:
         advice.append("Protein intake is a bit low. Consider adding eggs, chicken breast, or soy products to your meal.")
    
    # Logic for high carbohydrates
    if total_carbs > 80:
         advice.append("Carbohydrate levels are high. Be mindful of your remaining starch portions for the rest of the day.")
    
    # Default positive feedback
    if not advice:
         advice.append("Great job! This meal is nutritionally well-balanced.")

    return {
        "total_kcal": round(total_kcal, 1),
        "total_protein": round(total_protein, 1),
        "total_carbs": round(total_carbs, 1),
        "total_fat": round(total_fat, 1),
        "advice": advice
    }
