import os
from pathlib import Path
from roboflow import Roboflow
from ultralytics import YOLO

# Read the Roboflow API key from the environment so no secret is committed:
#   export ROBOFLOW_API_KEY=your_key    # Windows: set ROBOFLOW_API_KEY=your_key
api_key = os.environ.get("ROBOFLOW_API_KEY")
if not api_key:
    raise SystemExit(
        "Set the ROBOFLOW_API_KEY environment variable before training, e.g.\n"
        "  export ROBOFLOW_API_KEY=your_key"
    )

rf = Roboflow(api_key=api_key)
project = rf.workspace("ie-yifei-wang-tum-de").project("smart-tray")
version = project.version(2)
dataset = version.download("yolov11")   # make sure the project type is Instance Segmentation
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
