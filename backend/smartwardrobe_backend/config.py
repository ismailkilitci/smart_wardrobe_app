from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    backend_dir: Path
    model_dir: Path
    upload_dir: Path
    db_path: Path

    # YOLO tuning
    yolo_conf: float
    yolo_iou: float

    # Expected YOLO main category mapping (guide default)
    yolo_main_categories: tuple[str, ...]


def get_settings() -> Settings:
    backend_dir = Path(__file__).resolve().parent.parent
    repo_root = backend_dir.parent

    # Default backend models dir. If it contains the guide modelw files, keep it
    # active. Otherwise fall back to the Flutter-side modelw copy.
    model_dir = backend_dir / "models"

    # Optional override
    model_dir_override = os.getenv("MODEL_DIR", "").strip()
    if model_dir_override:
        model_dir = Path(model_dir_override).expanduser().resolve()
    else:
        required_names = [
            "YOLOV8_best.pt",
            "resnet18_subcat_improved.pth",
            "resnet50.pth",
            "subcat_mapping_improved.json",
            "subcat_to_main_improved.json",
            "main_to_subcat_ids_improved.json",
        ]
        backend_has_models = all((model_dir / name).exists() for name in required_names)
        if not backend_has_models:
            candidate = repo_root / "lib" / "data" / "models" / "modelw"
            if candidate.exists() and all((candidate / name).exists() for name in required_names):
                model_dir = candidate
    upload_dir = backend_dir / "uploads"
    db_path = backend_dir / "wardrobe.db"

    yolo_conf = float(os.getenv("YOLO_CONF", "0.10"))
    yolo_iou = float(os.getenv("YOLO_IOU", "0.45"))

    # SmartWardrobe guide mapping
    yolo_main_categories = (
        "tops",
        "bottoms",
        "outerwear",
        "all-body",
        "shoes",
    )

    return Settings(
        backend_dir=backend_dir,
        model_dir=model_dir,
        upload_dir=upload_dir,
        db_path=db_path,
        yolo_conf=yolo_conf,
        yolo_iou=yolo_iou,
        yolo_main_categories=yolo_main_categories,
    )
