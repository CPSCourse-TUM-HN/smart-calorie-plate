# smart-calorie-plate

AI 卡路里餐盘:YOLOv11 视觉识别 + FastAPI 营养计算后端。

## 快速开始

### 1. 拉代码
```bash
git clone https://github.com/xsn30/smart-calorie-plate.git
cd smart-calorie-plate
```

### 2. 建虚拟环境（推荐）
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

### 3. 装依赖
```bash
pip install -r requirements.txt
```

### 4. 初始化数据库 + 灌入 18 种食物的营养数据
```bash
cd src/calorie_plate
python database.py        # 建表
python seed_data.py       # 写入种子数据
```
执行完会在当前目录生成 `database.db`。

### 5. 启动后端服务
```bash
uvicorn main:app --reload
```
看到 `Uvicorn running on http://127.0.0.1:8000` 即可。

### 6. 试用接口
打开浏览器访问 **http://127.0.0.1:8000/docs**,FastAPI 自带 Swagger UI,可直接上传图片测试。

或者命令行:
```bash
# 只识别食物 → 返回 food_id 列表
curl -X POST http://127.0.0.1:8000/meal/detect \
  -F "image=@/path/to/photo.jpg"

# 识别 + 算热量（weights 按 detect 返回顺序，单位克）
curl -X POST http://127.0.0.1:8000/meal/analyze-image \
  -F "image=@/path/to/photo.jpg" \
  -F "weights=[150,80]"
```

## 接口一览

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/foods` | 列出所有食物 |
| GET | `/foods/{id}` | 查单个食物 |
| POST | `/meal/analyze` | 用 `food_id + weight_g` 算营养 |
| POST | `/meal/detect` | 上传图片 → 识别出的 food_id 列表 |
| POST | `/meal/analyze-image` | 上传图片 + 重量 → 完整营养 + 建议 |

## 目录结构

```
.
├── model/
│   ├── best.pt              # YOLOv11-seg 训练权重（18 类食物）
│   ├── last.pt
│   └── train_yolo11_seg.py  # 训练脚本
├── src/calorie_plate/
│   ├── main.py              # FastAPI 入口
│   ├── inference.py         # YOLO 推理封装
│   ├── database.py          # SQLModel 表定义
│   ├── seed_data.py         # 18 种食物初始数据
│   └── nutrition.py
├── tests/
└── requirements.txt
```

## 支持识别的食物（18 类，food_id 0–17）

banana, beef, bread, broccoli, carrot, chicken, cucumber, egg, fish, juice, lemon, noodles, pork, potato, rice, sausage, strawberry, tomato
