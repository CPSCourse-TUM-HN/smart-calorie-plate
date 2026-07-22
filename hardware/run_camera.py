"""Live camera loop on the Jetson: YOLO preview + backend nutrition calls.

Opens /dev/video0, runs the local YOLO model for an on-screen preview, and
talks to the FastAPI backend for the "official" detection / nutrition results.

Keys:
  c = detect only (no nutrition math)
  a = detect + full nutrition analysis (every food is assumed to be 100 g)
  q = quit

The scale is NOT wired into this loop: every food is billed at DUMMY_WEIGHT_G.
Real per-compartment grams come from the Arduino load cells (see
weigh_via_usb.py); fusing the two is left as a follow-up.
"""
import json
from pathlib import Path

import cv2
import requests
from ultralytics import YOLO

BACKEND_URL = "http://localhost:8000"
# Model lives at <repo>/model/best.pt. This file is <repo>/hardware/run_camera.py,
# so the repo root is one directory up.
MODEL_PATH = str(Path(__file__).resolve().parents[1] / "model" / "best.pt")
DUMMY_WEIGHT_G = 100.0  # every food is billed at 100 g until the scale is fused in

print("Loading model...")
model = YOLO(MODEL_PATH)
print("Model OK")

cap = cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

if not cap.isOpened():
    print("Camera open failed"); exit()

print("=" * 60)
print("  c = detect only (no nutrition math)")
print("  a = detect + full nutrition analysis (every food billed at 100 g)")
print("  q = quit")
print("=" * 60)

last_detect = None
last_analyze = None


def encode_jpg(frame):
    _, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return jpg.tobytes()


def call_detect(frame):
    files = {"image": ("frame.jpg", encode_jpg(frame), "image/jpeg")}
    r = requests.post(f"{BACKEND_URL}/meal/detect", files=files, timeout=10)
    r.raise_for_status()
    return r.json()


def call_analyze_image(frame, n_foods):
    """1 image + N dummy weights -> full nutrition breakdown."""
    weights = [DUMMY_WEIGHT_G] * n_foods
    files = {"image": ("frame.jpg", encode_jpg(frame), "image/jpeg")}
    data = {
        "weights": json.dumps(weights),
        "conf": 0.25,
    }
    r = requests.post(f"{BACKEND_URL}/meal/analyze-image", files=files, data=data, timeout=15)
    r.raise_for_status()
    return r.json()


while True:
    ret, frame = cap.read()
    if not ret:
        print("Cannot read camera"); break

    results = model(frame, verbose=False)
    annotated = results[0].plot()

    # Overlay the last detection result (top-left)
    if last_detect:
        y = 30
        cv2.rectangle(annotated, (0, 0), (500, 30 + len(last_detect.get("detections", [])) * 22),
                      (0, 0, 0), -1)
        cv2.putText(annotated, "Detect:", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        y += 22
        for det in last_detect.get("detections", []):
            text = f"  {det.get('name_en','?'):>12s} conf={det.get('confidence',0):.2f}"
            cv2.putText(annotated, text, (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y += 22

    # Overlay the last nutrition result (top-right)
    if last_analyze:
        y = 30
        w_start = 250
        cv2.rectangle(annotated, (w_start, 0), (640, 130), (0, 0, 0), -1)
        cv2.putText(annotated, f"kcal: {last_analyze.get('total_kcal', 0):.0f}",
                    (w_start + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        y += 22
        cv2.putText(annotated, f"protein: {last_analyze.get('total_protein', 0):.1f} g",
                    (w_start + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
        y += 22
        cv2.putText(annotated, f"carbs: {last_analyze.get('total_carbs', 0):.1f} g",
                    (w_start + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)
        y += 22
        cv2.putText(annotated, f"fat: {last_analyze.get('total_fat', 0):.1f} g",
                    (w_start + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 1)

    cv2.imshow("Smart Tray YOLO", annotated)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    elif key == ord("c"):
        print("\n>>> [c] detect only...")
        try:
            last_detect = call_detect(frame)
            dets = last_detect.get("detections", [])
            print(f"Detected {len(dets)} food(s):")
            for d in dets:
                print(f"    id={d.get('food_id')} {d.get('name_en'):>12s} "
                      f"/ {d.get('name_zh','?')}  conf={d.get('confidence'):.2f}")
        except Exception as e:
            print(f"Error: {e}")

    elif key == ord("a"):
        print("\n>>> [a] detect + nutrition analysis...")
        try:
            # Step 1: detect first, just to count how many foods there are
            det_result = call_detect(frame)
            n = len(det_result.get("detections", []))
            if n == 0:
                print("No food detected, nothing to analyze")
                continue
            print(f"  Detected {n} food(s), billing each at {DUMMY_WEIGHT_G} g...")
            # Step 2: call analyze-image with N dummy weights
            last_analyze = call_analyze_image(frame, n)
            last_detect = {"detections": last_analyze.get("detections", [])}
            print(f"Total energy: {last_analyze.get('total_kcal'):.1f} kcal")
            print(f"  protein: {last_analyze.get('total_protein'):.1f} g  "
                  f"carbs: {last_analyze.get('total_carbs'):.1f} g  "
                  f"fat: {last_analyze.get('total_fat'):.1f} g")
            print(f"  breakdown:")
            for item in last_analyze.get("items", []):
                print(f"    {item['name_en']:>12s}  {item['weight_g']:>4}g  "
                      f"{item['kcal']:>5}kcal  P{item['protein']:>4}g  "
                      f"C{item['carbs']:>4}g  F{item['fat']:>4}g")
            print(f"  advice:")
            for a in last_analyze.get("advice", []):
                print(f"    - {a}")
        except Exception as e:
            print(f"Error: {e}")

cap.release()
cv2.destroyAllWindows()
