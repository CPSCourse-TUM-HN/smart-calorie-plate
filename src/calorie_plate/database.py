from datetime import date, datetime
from pathlib import Path
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


class Meal(SQLModel, table=True):
    """一次"确认摄入"的记录——数据记忆的核心，可按用户/日期回溯每一餐。"""
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, index=True)
    log_date: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.now)

    total_kcal: float = 0.0
    total_protein_g: float = 0.0
    total_carbs_g: float = 0.0
    total_fat_g: float = 0.0

    # 这一餐的食物明细（JSON 字符串：[{food_id,name_zh,weight_g,kcal,...}]）
    items_json: str | None = None
    advice: str | None = None


class UserProfile(SQLModel, table=True):
    """用户身体信息与系统计算出的目标值。"""
    id: int | None = Field(default=None, primary_key=True)
    name: str | None = None  # 账号显示名（用户可手填，留空则前端生成随机名）
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

# 2. 数据库文件用绝对路径，固定放在本模块同级目录，
#    这样无论从哪个工作目录启动（开发 / 打包后的 app）都指向同一个库。
DB_PATH = Path(__file__).resolve().parent / "database.db"
sqlite_file_name = str(DB_PATH)
sqlite_url = f"sqlite:///{sqlite_file_name}"

# 3. 创建引擎（连接数据库的桥梁）
engine = create_engine(sqlite_url, echo=False)

# 4. 初始化数据库的函数
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

if __name__ == "__main__":
    create_db_and_tables()
    print("数据库和食物表 (Food) 初始化成功！")