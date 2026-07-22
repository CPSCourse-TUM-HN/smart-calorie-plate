"""End-to-end Jetson loop: real scale weights + camera + backend + OLED.

Pipeline on each analysis:
  1. read the latest per-compartment weights from the Arduino (scale_serial)
  2. capture a camera frame and ask the backend to detect the foods
  3. send the image + real weights to the backend for the nutrition breakdown
  4. push the totals back to the Arduino so the OLED shows kcal/protein/carbs/fat

Weight -> food mapping (heuristic, documented on purpose):
  The firmware reports 3 compartment weights but not which food sits where.
  We pair the non-zero compartment weights (C1, C2, C3 order) with the
  detections in detection order. If the counts do not match, we fall back to
  splitting the total weight evenly across the detected foods. Adjust to match
  how you physically load the plate.

Keys:
  a = analyze (detect + real weights -> nutrition -> OLED)
  t = tare the scale
  q = quit
"""
import json
from pathlib import Path

import cv2
import requests
from ultralytics import YOLO

from scale_serial import ScaleSerial

BACKEND_URL = "http://localhost:8000"
MODEL_PATH = str(Path(__file__).resolve().parents[1] / "model" / "best.pt")

print("Loading model...")
model = YOLO(MODEL_PATH)
print("Model OK")

print("Connecting to scale...")
scale = ScaleSerial()
print(f"Scale on {scale.port}")

cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
if not cap.isOpened():
    print("Camera open failed"); exit()

print("=" * 60)
print("  a = analyze (detect + real weights -> nutrition -> OLED)")
print("  t = tare the scale")
print("  q = quit")
print("=" * 60)

last_analyze = None


def encode_jpg(frame):
    _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return jpg.tobytes()


def call_detect(frame):
    files = {"image": ("frame.jpg", encode_jpg(frame), "image/jpeg")}
    r = requests.post(f"{BACKEND_URL}/meal/detect", files=files, timeout=10)
    r.raise_for_status()
    return r.json()


def call_analyze_image(frame, weights):
    files = {"image": ("frame.jpg", encode_jpg(frame), "image/jpeg")}
    data = {"weights": json.dumps(weights), "conf": 0.25}
    r = requests.post(f"{BACKEND_URL}/meal/analyze-image", files=files, data=data, timeout=15)
    r.raise_for_status()
    return r.json()


def weights_for(n_foods, scale_reading):
    """Map the 3 compartment weights onto n detected foods (see module docstring)."""
    comp = [w for w in scale_reading["weights"] if w > 0]
    if n_foods == len(comp):
        return comp
    total = scale_reading["total"] or sum(scale_reading["weights"])
    if total <= 0:
        return [0.0] * n_foods
    return [round(total / n_foods, 1)] * n_foods


while True:
    ret, frame = cap.read()
    if not ret:
        print("Cannot read camera"); break

    results = model(frame, verbose=False)
    annotated = results[0].plot()

    # keep the scale reading fresh in the background
    reading = scale.read_latest()
    cv2.rectangle(annotated, (0, 0), (300, 26), (0, 0, 0), -1)
    w = reading["weights"]
    cv2.putText(annotated,
                f"C1={w[0]:.0f} C2={w[1]:.0f} C3={w[2]:.0f} tot={reading['total']:.0f}g",
                (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    if last_analyze:
        y = 46
        cv2.rectangle(annotated, (0, 30), (260, 130), (0, 0, 0), -1)
        cv2.putText(annotated, f"kcal: {last_analyze.get('total_kcal', 0):.0f}",
                    (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2); y += 22
        cv2.putText(annotated, f"P {last_analyze.get('total_protein', 0):.1f}g  "
                               f"C {last_analyze.get('total_carbs', 0):.1f}g  "
                               f"F {last_analyze.get('total_fat', 0):.1f}g",
                    (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 200, 0), 1)

    cv2.imshow("Smart Tray (fullstack)", annotated)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    elif key == ord("t"):
        print("\n>>> [t] taring scale (Arduino counts down 5 s)...")
        scale.tare()

    elif key == ord("a"):
        print("\n>>> [a] analyze...")
        try:
            det = call_detect(frame)
            n = len(det.get("detections", []))
            if n == 0:
                print("No food detected, nothing to analyze")
                continue

            reading = scale.read_latest()
            weights = weights_for(n, reading)
            print(f"  Detected {n} food(s); weights = {weights} g "
                  f"(scale total {reading['total']:.0f} g)")

            last_analyze = call_analyze_image(frame, weights)

            # push totals to the OLED
            scale.send_nutrition(
                last_analyze.get("total_kcal", 0),
                last_analyze.get("total_protein", 0),
                last_analyze.get("total_carbs", 0),
                last_analyze.get("total_fat", 0),
            )

            print(f"Total: {last_analyze.get('total_kcal'):.1f} kcal  "
                  f"P{last_analyze.get('total_protein'):.1f}g  "
                  f"C{last_analyze.get('total_carbs'):.1f}g  "
                  f"F{last_analyze.get('total_fat'):.1f}g")
            for item in last_analyze.get("items", []):
                print(f"    {item['name_en']:>12s}  {item['weight_g']:>5}g  "
                      f"{item['kcal']:>5}kcal")
            for a in last_analyze.get("advice", []):
                print(f"    - {a}")
        except Exception as e:
            print(f"Error: {e}")

cap.release()
cv2.destroyAllWindows()
scale.close()
