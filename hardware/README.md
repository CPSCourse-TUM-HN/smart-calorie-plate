# Hardware integration (Jetson Orin Nano)

The on-device code that ran on the Jetson Orin Nano with the camera + Arduino scale
wired up. It talks to the same FastAPI backend as the desktop app (default
`http://localhost:8000`), so start the backend first:

```bash
cd ../src/calorie_plate && uvicorn main:app          # serves /meal/* and /api/*
```

Then install the Jetson-side deps and run one of the scripts:

```bash
pip install -r requirements.txt
```

## Serial protocol (source of truth: the Arduino firmware)

The weighing side follows [`arduino/smart_calorie_plate/smart_calorie_plate.ino`](../arduino/smart_calorie_plate/smart_calorie_plate.ino),
**not** the Python scripts. The firmware already calibrates the four HX711 load
cells on-device (the `C1_*/C2_*/C3_*` coefficients) and decomposes them into
three compartment weights. Baud is **9600**.

| Direction | Line | Meaning |
|---|---|---|
| Arduino → Jetson | `DATA,w1,w2,w3,total` | Per-compartment grams + total (already calibrated) |
| Arduino → Jetson | `Tare completed.` / `Nutrition received: ...` | Status messages |
| Jetson → Arduino | `NUTRI,kcal,protein,carbs,fat` | Show nutrition on the OLED |
| Jetson → Arduino | `t` or `T` | Manual tare (5 s countdown, then zero) |

## Scripts

| File | What it does |
|---|---|
| `scale_serial.py` | Reusable serial link that matches the firmware protocol (read `DATA`, send `NUTRI`, tare). Run directly to stream weights. |
| `run_camera.py` | Camera + YOLO preview + backend detection/nutrition. **Weights are dummy (100 g each)** — a quick vision-only check that doesn't need the scale. |
| `run_fullstack.py` | The real end-to-end loop: real scale weights + camera detection + backend nutrition + results pushed back to the OLED. |

### `run_fullstack.py` weight → food mapping

The firmware reports 3 compartment weights but not which food sits in which
compartment. The script pairs the non-zero compartment weights (in `C1, C2, C3`
order) with the detections in detection order; if the counts don't match it
splits the total weight evenly across the detected foods. Tweak
`weights_for()` to match how you physically load the plate.

## `legacy/` — old firmware only

These scripts target an **earlier firmware** that streamed raw per-load-cell
values (`L1=.. | L2=.. | L3=.. | L4=..`) and did calibration on the Python
side. The current firmware calibrates on-device and emits `DATA,...` instead,
so `calibrate.py`, `measure_compartments.py`, `diagnose.py` and
`scale_config.json` are kept for reference only and will **not** work as-is with
the committed `.ino`.
