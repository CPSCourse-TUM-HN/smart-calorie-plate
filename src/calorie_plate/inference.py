from pathlib import Path
from threading import Lock
from typing import List, Dict, Any

from ultralytics import YOLO


# YOLO 训练时的类别按字母序排列，正好对应 seed_data.py 中 Food.id 0-17
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
    """对图片做一次推理，返回每个检测框对应的 food_id + 置信度。

    YOLO 的 cls 索引直接对应数据库里的 Food.id（按字母序排列）。
    """
    import numpy as np
    import cv2

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("无法解码图像，请确认上传的是有效的图片文件")

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
