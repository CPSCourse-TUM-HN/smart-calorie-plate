# smart-calorie-plate

AI-powered calorie plate: YOLOv11 food recognition + FastAPI nutrition backend.

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/xsn30/smart-calorie-plate.git
cd smart-calorie-plate
```

### 2. Create a virtual environment (recommended)
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize the database and seed the 18 foods
```bash
cd src/calorie_plate
python database.py        # create tables
python seed_data.py       # insert seed data
```
This creates `database.db` in the current directory.

### 5. Start the backend server
```bash
uvicorn main:app --reload
```
You should see `Uvicorn running on http://127.0.0.1:8000`.

### 6. Try the API

Open **http://127.0.0.1:8000/docs** in your browser. FastAPI ships with
Swagger UI, so you can test every endpoint visually without writing code.

#### A. Verify the database first: `GET /foods`

1. Expand the `GET /foods` row → click **Try it out** (top right, turns into an Execute button)
2. Click **Execute**
3. The response body should contain 18 food records (banana / beef / ...), confirming the database works.

#### B. Detection only (no calorie math): `POST /meal/detect`

1. Prepare a photo containing food (JPG or PNG). The `photo/` folder ships a few samples (`mix.png`, `sausage.jpeg`, `strawberry.png`), or use any photo from your phone or the web.
2. Expand `POST /meal/detect` → **Try it out**
3. For the `image` field click **Choose File** and pick a photo; leave `conf` at the default `0.25` (confidence threshold — lower values detect more)
4. Click **Execute**
5. Example response:
   ```json
   {
     "detections": [
       {"food_id": 14, "name_en": "rice",     "name_zh": "米饭",   "confidence": 0.92},
       {"food_id": 3,  "name_en": "broccoli", "name_zh": "西兰花", "confidence": 0.81}
     ]
   }
   ```
   Note: the first call takes 5–10 seconds (loading `best.pt`); subsequent calls are near-instant.

#### C. Detection + calorie math in one call: `POST /meal/analyze-image`

Following the detection result from step B, suppose you want to tell the
backend "150 g of rice and 80 g of broccoli":

1. Expand `POST /meal/analyze-image` → **Try it out**
2. `image`: pick the same photo
3. `weights`: enter `[150, 80]` — **the order must match the order of the detections from step B**
4. `conf`: leave at `0.25`
5. Click **Execute**. The response looks like:
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

#### D. Prefer the command line? curl works too:

```bash
# Detection only → returns a list of food_ids
curl -X POST http://127.0.0.1:8000/meal/detect \
  -F "image=@/path/to/photo.jpg"

# Detection + calorie math (weights in grams, ordered like the detect response)
curl -X POST http://127.0.0.1:8000/meal/analyze-image \
  -F "image=@/path/to/photo.jpg" \
  -F "weights=[150,80]"

# Skip the model and compute directly from food_ids (when you know what was eaten)
curl -X POST http://127.0.0.1:8000/meal/analyze \
  -H "Content-Type: application/json" \
  -d '{"items":[{"food_id":14,"weight_g":150},{"food_id":3,"weight_g":80}]}'
```

#### Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Food with ID X not found` | `seed_data.py` was never run | Go back to step 4 and initialize the database |
| `weights must be a list of numbers` | Swagger UI sometimes quietly adds quotes | Try the bracket-free form: `150,80` |
| `Detected N foods but received M weights` | Weight count does not match the detection count | Call `/meal/detect` first to see how many boxes there are, then send that many weights |
| `No module named 'cv2' / 'ultralytics'` | Missing dependencies | Re-run `pip install -r requirements.txt` |
| No / few detections | Foods are outside the 18 classes, or bad angle/lighting | Try another photo, or lower `conf` to `0.1` |

## API Overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/foods` | List all foods |
| GET | `/foods/{id}` | Fetch one food |
| POST | `/meal/analyze` | Compute nutrition from `food_id + weight_g` |
| POST | `/meal/detect` | Upload a photo → list of detected food_ids |
| POST | `/meal/analyze-image` | Upload a photo + weights → full nutrition + advice |

## Project Layout

```
.
├── model/
│   ├── best.pt              # YOLOv11-seg trained weights (18 food classes)
│   ├── last.pt
│   └── train_yolo11_seg.py  # training script (reads ROBOFLOW_API_KEY from env)
├── src/calorie_plate/
│   ├── main.py              # FastAPI entry point
│   ├── inference.py         # YOLO inference wrapper
│   ├── database.py          # SQLModel table definitions
│   ├── seed_data.py         # initial data for the 18 foods
│   ├── utils.py             # BMR/TDEE/macro target calculation
│   └── nutrition.py
├── smart-plate-ui/          # Next.js frontend + PyWebView desktop shell
├── arduino/                 # Arduino firmware for the 4-load-cell scale + OLED
├── hardware/                # Jetson-side integration (camera + scale + backend)
├── photo/                   # sample food photos for testing /meal/detect
├── tests/
└── requirements.txt
```

## Recognized Foods (18 classes, food_id 0–17)

banana, beef, bread, broccoli, carrot, chicken, cucumber, egg, fish, juice, lemon, noodles, pork, potato, rice, sausage, strawberry, tomato

---

## Desktop App (one-command run)

> Frontend (Next.js) + PyWebView desktop shell: FastAPI starts locally and
> **serves the static frontend from the same origin**, and PyWebView opens a
> window pointed at it. Because frontend and backend share one origin, there
> is no separate `next dev` process, and the packaged app avoids the
> "pages cannot navigate / only works on localhost" problem entirely.

### How to run

```bash
# 1) Install backend + desktop dependencies (requirements.txt already includes pywebview)
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) Build the static frontend site (outputs to smart-plate-ui/out/)
cd smart-plate-ui
npm install
npm run build                      # equivalent to next build --webpack; output works in old WebViews
cd ..

# 3) Launch the desktop app
python run_app.py
```

`run_app.py` starts uvicorn on a background thread (127.0.0.1:8000), waits
for `/api/health` to respond, then opens the PyWebView window. On first
launch the database `database.db` is **created and seeded with the 18 foods
automatically** — no need to run `database.py` / `seed_data.py` by hand.

### Frontend dev mode (hot reload, optional)

```bash
# Terminal A: backend
cd src/calorie_plate && uvicorn main:app --reload
# Terminal B: frontend dev server (connects to 127.0.0.1:8000 automatically)
cd smart-plate-ui && npm run dev   # http://localhost:3000
```

### Desktop features

- **Setup screen**: enter body metrics + optional username (a random name is generated when blank) → personalized nutrition targets
- **Recognition workbench**: upload a plate photo / use the camera → YOLO detection → enter the weight of each food → calories and macros
- **Diet Notes**: every meal is persisted (meal history) and can be reviewed later
- **Nutrition Analysis**: recommendations based on today's intake vs. targets, plus suggested foods
- **Account Settings**: switch between accounts, delete individual accounts

### Additional endpoints (used by the frontend)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check (startup probe) |
| POST | `/api/user-profile/` | Create an account + compute targets |
| GET | `/api/user-profiles/` | List accounts (for switching) |
| GET | `/api/user-profile/{id}` | Fetch one account |
| DELETE | `/api/user-profile/{id}` | Delete an account |
| POST | `/api/meals/` | Confirm intake (write one meal record) |
| GET | `/api/meals/` | Meal history |
| GET | `/api/meals/summary` | Daily intake summary |
| POST | `/api/recommend` | Nutrition recommendation |

---

## Embedded / Hardware (Jetson Orin Nano + Arduino scale)

The physical device pairs an Arduino (4× HX711 load cells → 3 compartment
weights + OLED) with a Jetson Orin Nano (camera + YOLO) that calls this same backend.

- `arduino/smart_calorie_plate/` — firmware. It calibrates the load cells
  on-device and streams `DATA,w1,w2,w3,total`; it accepts `NUTRI,kcal,protein,carbs,fat`
  back to show on the OLED.
- `hardware/` — Jetson-side scripts: `scale_serial.py` (serial link matching the
  firmware protocol), `run_camera.py` (camera + detection preview), and
  `run_fullstack.py` (real scale weights + detection + nutrition → OLED). See
  [hardware/README.md](hardware/README.md) for wiring and the serial protocol.

## Running the tests

```bash
pip install pytest
PYTHONPATH=src python -m pytest        # same command the CI workflow runs
```
