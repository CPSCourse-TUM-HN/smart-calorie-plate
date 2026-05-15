import os
from pathlib import Path
from roboflow import Roboflow
from ultralytics import YOLO

rf = Roboflow(api_key="0LFib4ka2wwwN6UMEV2U")
project = rf.workspace("ie-yifei-wang-tum-de").project("smart-tray")
version = project.version(2)
dataset = version.download("yolov11")   # 确认项目是 Instance Segmentation
data_yaml = Path(dataset.location) / "data.yaml"

print("Dataset location:", dataset.location)
print("Data yaml:", data_yaml)

model = YOLO("yolo11n-seg.pt")
model.train(
    data=str(data_yaml),
    epochs=50,
    imgsz=640,
    batch=8,
    name="smart_tray_yolo11n_seg",
    project="/workspace/smart-tray/runs",
)
