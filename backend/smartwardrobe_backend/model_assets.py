from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelAssets:
    # Model files (may or may not exist)
    yolo_path: Path
    resnet18_subcat_path: Path
    resnet50_compat_path: Path

    # Mapping json files
    subcat_mapping_path: Path
    subcat_to_main_path: Path
    main_to_subcat_ids_path: Path


def resolve_assets(model_dir: Path) -> ModelAssets:
    # Guide names
    yolo_path = model_dir / "YOLOV8_best.pt"
    resnet18_subcat_path = model_dir / "resnet18_subcat_improved.pth"
    resnet50_compat_path = model_dir / "resnet50.pth"

    subcat_mapping_path = model_dir / "subcat_mapping_improved.json"
    subcat_to_main_path = model_dir / "subcat_to_main_improved.json"
    main_to_subcat_ids_path = model_dir / "main_to_subcat_ids_improved.json"

    # Backward compatible existing names
    if not yolo_path.exists() and (model_dir / "yolo_model.pt").exists():
        yolo_path = model_dir / "yolo_model.pt"
    if not resnet18_subcat_path.exists() and (model_dir / "resnet_model.pth").exists():
        resnet18_subcat_path = model_dir / "resnet_model.pth"

    return ModelAssets(
        yolo_path=yolo_path,
        resnet18_subcat_path=resnet18_subcat_path,
        resnet50_compat_path=resnet50_compat_path,
        subcat_mapping_path=subcat_mapping_path,
        subcat_to_main_path=subcat_to_main_path,
        main_to_subcat_ids_path=main_to_subcat_ids_path,
    )


def load_json_if_exists(path: Path) -> Any | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
