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

打开浏览器访问 **http://127.0.0.1:8000/docs**,FastAPI 自带 Swagger UI,可视化测试,不用写代码。

#### A. 先确认数据库通了:`GET /foods`

1. 点开 `GET /foods` 那一行 → 右上角 **Try it out**(变成 Execute 按钮)
2. 点 **Execute**
3. 下方 Response body 应该返回 18 条食物记录(banana / beef / ...),说明数据库 OK。

#### B. 只识别食物(不算热量):`POST /meal/detect`

1. 准备一张含食物的图片(JPG/PNG 都行)。仓库里 `photo/` 是空的,你可以随便从手机里传一张,或用网图。
2. 点开 `POST /meal/detect` → **Try it out**
3. `image` 字段点 **Choose File**,选一张图;`conf` 留默认 `0.25`(置信度阈值,越低识别越多)
4. 点 **Execute**
5. 返回示例:
   ```json
   {
     "detections": [
       {"food_id": 14, "name_en": "rice",     "name_zh": "米饭",   "confidence": 0.92},
       {"food_id": 3,  "name_en": "broccoli", "name_zh": "西兰花", "confidence": 0.81}
     ]
   }
   ```
   ⚠️ 第一次调用要等 5–10 秒(在加载 `best.pt`),之后毫秒级。

#### C. 识别 + 算热量(一站式):`POST /meal/analyze-image`

接着 B 步的检测结果,假设你想告诉后端"米饭 150g、西兰花 80g":

1. 点开 `POST /meal/analyze-image` → **Try it out**
2. `image`:选同一张图
3. `weights`:填 `[150, 80]` —— **顺序必须和 B 步 detections 的顺序一致**
4. `conf`:留 `0.25`
5. 点 **Execute**,返回:
   ```json
   {
     "total_kcal": 202.8,
     "total_protein": 7.2,
     "total_carbs": 42.3,
     "total_fat": 0.9,
     "items": [
       {"name_zh":"米饭","weight_g":150,"kcal":174.0, ...},
       {"name_zh":"西兰花","weight_g":80, "kcal":28.8, ...}
     ],
     "advice": ["Protein intake is a bit low. Consider adding ..."],
     "detections": [...]
   }
   ```

#### D. 不想用浏览器?命令行 curl 同样能用:

```bash
# 只识别食物 → 返回 food_id 列表
curl -X POST http://127.0.0.1:8000/meal/detect \
  -F "image=@/path/to/photo.jpg"

# 识别 + 算热量（weights 按 detect 返回顺序，单位克）
curl -X POST http://127.0.0.1:8000/meal/analyze-image \
  -F "image=@/path/to/photo.jpg" \
  -F "weights=[150,80]"

# 也可以跳过模型，直接用 food_id 算（已知吃了啥的场景）
curl -X POST http://127.0.0.1:8000/meal/analyze \
  -H "Content-Type: application/json" \
  -d '{"items":[{"food_id":14,"weight_g":150},{"food_id":3,"weight_g":80}]}'
```

#### 常见报错

| 报错 | 原因 | 处理 |
|---|---|---|
| `Food with ID X not found` | 没跑 `seed_data.py` | 回到第 4 步初始化数据库 |
| `weights 必须是数字列表` | Swagger UI 偶尔会偷偷加引号 | 试试不带方括号的写法:`150,80` |
| `检测到 N 个食物，但提供了 M 个重量` | weights 数量和检测框对不上 | 先调 `/meal/detect` 看清楚有几个框,再按相同数量填 weights |
| `No module named 'cv2' / 'ultralytics'` | 依赖没装全 | `pip install -r requirements.txt` 重跑 |
| 识别不出来 / 框很少 | 图里食物不在 18 类里,或角度光线太差 | 换图;或把 `conf` 调低到 `0.1` 试试 |

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
