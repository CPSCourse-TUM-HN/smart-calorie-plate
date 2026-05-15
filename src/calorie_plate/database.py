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