from pathlib import Path
from threading import Lock
from typing import List, Dict, Any

from ultralytics import YOLO


# YOLO classes are alphabetically ordered at training time, matching Food.id 0-17 in seed_data.py:
# banana=0, beef=1, bread=2, broccoli=3, carrot=4, chicken=5, cucumber=6,
# egg=7, fish=8, juice=9, lemon=10, noodles=11, pork=12, potato=13,
# rice=14, sausage=15, strawberry=16, tomato=17

MODEL_PATH = Path(__file__).resolve().parents[2] / "model" / "best.pt"

_model: YOLO | None = None
_model_lock = Lock()


def get_model() -> YOLO:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = YOLO(str(MODEL_PATH))
    return _model


def detect(image_bytes: bytes, conf: float = 0.25) -> List[Dict[str, Any]]:
    """Run one inference pass on the image and return the food_id and
    confidence for every detection box.

    YOLO's cls index maps directly to Food.id in the database (both are
    alphabetically ordered).
    """
    import numpy as np
    import cv2

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode the image. Please upload a valid image file.")

    model = get_model()
    results = model.predict(img, conf=conf, verbose=False)

    detections: List[Dict[str, Any]] = []
    for result in results:
        if result.boxes is None:
            continue
        names = result.names  # {0: 'banana', 1: 'beef', ...}
        for cls_tensor, conf_tensor in zip(result.boxes.cls, result.boxes.conf):
            food_id = int(cls_tensor.item())
            detections.append(
                {
                    "food_id": food_id,
                    "name_en": names.get(food_id, str(food_id)),
                    "confidence": round(float(conf_tensor.item()), 4),
                }
            )
    return detections
