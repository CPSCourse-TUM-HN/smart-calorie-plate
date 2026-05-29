from datetime import date
from sqlmodel import Field, SQLModel, create_engine

# 1. 定义数据模型（这既是 Pydantic 模型，也是数据库的表结构）
class Food(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name_zh: str
    name_en: str
    kcal_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float


class DietNote(SQLModel, table=True):
    """记录每日饮食笔记——包含目标与实际摄入，用于汇总与分析。"""
    id: int | None = Field(default=None, primary_key=True)
    log_date: date = Field(default_factory=date.today)

    # 用户预设/目标（前端可提交或由系统生成）
    target_calories: float | None = None
    target_protein_g: float | None = None
    target_carbs_g: float | None = None
    target_fat_g: float | None = None

    # 实际当日摄入（用于汇总）
    actual_calories: float | None = None
    actual_protein_g: float | None = None
    actual_carbs_g: float | None = None
    actual_fat_g: float | None = None

    advice: str | None = None


class UserProfile(SQLModel, table=True):
    """用户身体信息与系统计算出的目标值。"""
    id: int | None = Field(default=None, primary_key=True)
    age: int
    gender: str  # 'male' or 'female'
    height_cm: float
    weight_kg: float
    activity_level: float  # 活动系数，例如 1.2, 1.375, 1.55
    diet_mode: str  # 'fat_loss' | 'balance' | 'muscle_gain'

    # 系统计算后的目标值
    target_calories: float | None = None
    target_protein_g: float | None = None
    target_fat_g: float | None = None
    target_carbs_g: float | None = None

# 2. 指定数据库文件名称（它会在当前目录下生成）
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# 3. 创建引擎（连接数据库的桥梁）
engine = create_engine(sqlite_url, echo=True)

# 4. 初始化数据库的函数
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_db_and_tables()
    print("数据库和食物表 (Food) 初始化成功！")