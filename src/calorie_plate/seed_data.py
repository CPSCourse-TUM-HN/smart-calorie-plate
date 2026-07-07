from sqlmodel import Session
from database import engine, Food

# The 18 seed foods. Food.id must match the YOLO class index (alphabetical
# order of name_en). name_zh is bilingual display data returned by the API,
# so the Chinese values are intentional.
initial_foods = [
    Food(id=0, name_zh="香蕉", name_en="banana", kcal_per_100g=89, protein_per_100g=1.1, carbs_per_100g=22.8, fat_per_100g=0.3),
    Food(id=1, name_zh="牛肉", name_en="beef", kcal_per_100g=106, protein_per_100g=20.2, carbs_per_100g=1.2, fat_per_100g=2.3),
    Food(id=2, name_zh="面包", name_en="bread", kcal_per_100g=313, protein_per_100g=8.8, carbs_per_100g=58.6, fat_per_100g=4.1),
    Food(id=3, name_zh="西兰花", name_en="broccoli", kcal_per_100g=36, protein_per_100g=4.1, carbs_per_100g=4.3, fat_per_100g=0.6),
    Food(id=4, name_zh="胡萝卜", name_en="carrot", kcal_per_100g=32, protein_per_100g=1.0, carbs_per_100g=7.7, fat_per_100g=0.2),
    Food(id=5, name_zh="鸡肉", name_en="chicken", kcal_per_100g=133, protein_per_100g=19.4, carbs_per_100g=2.5, fat_per_100g=5.0),
    Food(id=6, name_zh="黄瓜", name_en="cucumber", kcal_per_100g=16, protein_per_100g=0.8, carbs_per_100g=2.9, fat_per_100g=0.2),
    Food(id=7, name_zh="鸡蛋", name_en="egg", kcal_per_100g=144, protein_per_100g=13.3, carbs_per_100g=2.8, fat_per_100g=8.8),
    Food(id=8, name_zh="鱼肉", name_en="fish", kcal_per_100g=113, protein_per_100g=16.6, carbs_per_100g=0.0, fat_per_100g=5.2),
    Food(id=9, name_zh="果汁", name_en="juice", kcal_per_100g=45, protein_per_100g=0.5, carbs_per_100g=10.4, fat_per_100g=0.1),
    Food(id=10, name_zh="柠檬", name_en="lemon", kcal_per_100g=29, protein_per_100g=1.1, carbs_per_100g=9.3, fat_per_100g=0.3),
    Food(id=11, name_zh="面条", name_en="noodles", kcal_per_100g=137, protein_per_100g=4.5, carbs_per_100g=28.5, fat_per_100g=0.4),
    Food(id=12, name_zh="猪肉", name_en="pork", kcal_per_100g=143, protein_per_100g=20.3, carbs_per_100g=1.5, fat_per_100g=6.2),
    Food(id=13, name_zh="土豆", name_en="potato", kcal_per_100g=81, protein_per_100g=2.6, carbs_per_100g=17.8, fat_per_100g=0.2),
    Food(id=14, name_zh="米饭", name_en="rice", kcal_per_100g=116, protein_per_100g=2.6, carbs_per_100g=25.9, fat_per_100g=0.3),
    Food(id=15, name_zh="香肠", name_en="sausage", kcal_per_100g=308, protein_per_100g=14.0, carbs_per_100g=15.0, fat_per_100g=21.0),
    Food(id=16, name_zh="草莓", name_en="strawberry", kcal_per_100g=32, protein_per_100g=0.7, carbs_per_100g=7.7, fat_per_100g=0.3),
    Food(id=17, name_zh="番茄", name_en="tomato", kcal_per_100g=15, protein_per_100g=0.9, carbs_per_100g=3.3, fat_per_100g=0.2)

]


def seed_foods():
    with Session(engine) as session:
        for food in initial_foods:
            session.add(food)
        session.commit()
        print(f"Successfully imported nutrition data for {len(initial_foods)} foods into the SQLite database!")

if __name__ == "__main__":
    seed_foods()