from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torchvision.transforms as transforms
from PIL import Image, ImageOps
from ultralytics import YOLO

from .model_assets import ModelAssets, load_json_if_exists
from .torch_utils import load_resnet_state_dict_model, load_backbone_scorer_state_dict_model


@dataclass(frozen=True)
class LoadedModels:
    yolo: YOLO | None
    resnet18_subcat: torch.nn.Module | None
    resnet50_compat: torch.nn.Module | None

    # mapping files
    subcat_mapping: dict[str, str] | None
    subcat_to_main: dict[str, str] | None
    main_to_subcat_ids: dict[str, list[int]] | None

    errors: dict[str, str]
    warnings: dict[str, str]


def load_models(assets: ModelAssets) -> LoadedModels:
    errors: dict[str, str] = {}
    warnings: dict[str, str] = {}

    yolo = None
    if assets.yolo_path.exists():
        try:
            yolo = YOLO(str(assets.yolo_path))
        except Exception as e:
            errors["yolo"] = str(e)
    else:
        errors["yolo"] = f"Model file not found: {assets.yolo_path}"

    resnet18 = None
    if assets.resnet18_subcat_path.exists():
        try:
            resnet18 = load_resnet_state_dict_model(assets.resnet18_subcat_path)
        except Exception as e:
            # Some checkpoints are saved as custom backbone+scorer state_dict.
            try:
                resnet18 = load_backbone_scorer_state_dict_model(assets.resnet18_subcat_path)
            except Exception as e2:
                errors["resnet18"] = f"{e} | fallback failed: {e2}"
    else:
        errors["resnet18"] = f"Model file not found: {assets.resnet18_subcat_path}"

    resnet50 = None
    if assets.resnet50_compat_path.exists():
        try:
            resnet50 = load_backbone_scorer_state_dict_model(assets.resnet50_compat_path)
        except Exception as e:
            errors["resnet50"] = str(e)
    else:
        errors["resnet50"] = f"Model file not found: {assets.resnet50_compat_path}"

    subcat_mapping_any = load_json_if_exists(assets.subcat_mapping_path)
    subcat_to_main_any = load_json_if_exists(assets.subcat_to_main_path)
    main_to_subcat_ids_any = load_json_if_exists(assets.main_to_subcat_ids_path)

    subcat_mapping = subcat_mapping_any if isinstance(subcat_mapping_any, dict) else None
    subcat_to_main = subcat_to_main_any if isinstance(subcat_to_main_any, dict) else None

    main_to_subcat_ids: dict[str, list[int]] | None = None
    if isinstance(main_to_subcat_ids_any, dict):
        parsed: dict[str, list[int]] = {}
        for k, v in main_to_subcat_ids_any.items():
            if isinstance(k, str) and isinstance(v, list) and all(isinstance(x, int) for x in v):
                parsed[k] = v
        main_to_subcat_ids = parsed

    if subcat_mapping is None:
        warnings["subcat_mapping"] = (
            "subcat_mapping_improved.json not found; sub_category ids cannot be mapped to names. "
            "Provide the mapping JSON from the guide for readable subcategories."
        )
    if subcat_to_main is None:
        warnings["subcat_to_main"] = (
            "subcat_to_main_improved.json not found; main_category cannot be corrected from subcategory."
        )
    if main_to_subcat_ids is None:
        warnings["main_to_subcat_ids"] = (
            "main_to_subcat_ids_improved.json not found; subcategory predictions cannot be constrained by main_category."
        )

    # Probe subcategory model output shape to catch binary/incorrect checkpoints early.
    if resnet18 is not None:
        try:
            dummy = torch.zeros((1, 3, 224, 224), dtype=torch.float32)
            with torch.no_grad():
                logits = resnet18(dummy)

            if hasattr(logits, "numel") and int(logits.numel()) == 1:
                warnings["resnet18_subcat_checkpoint"] = (
                    "Loaded subcategory model outputs a single logit (binary). "
                    "The guide expects a multi-class classifier (resnet18_subcat_improved.pth) producing many subcategory ids. "
                    "This checkpoint is treated as incompatible for subcategory classification."
                )
                resnet18 = None
            elif subcat_mapping is not None and logits.ndim == 2:
                class_count = int(logits.shape[1])
                if class_count != len(subcat_mapping):
                    warnings["resnet18_class_count"] = (
                        f"Subcategory model outputs {class_count} classes, "
                        f"but mapping has {len(subcat_mapping)} entries."
                    )
        except Exception as e:
            warnings["resnet18_probe"] = f"Could not probe resnet18 output shape: {e}"

    return LoadedModels(
        yolo=yolo,
        resnet18_subcat=resnet18,
        resnet50_compat=resnet50,
        subcat_mapping=subcat_mapping,
        subcat_to_main=subcat_to_main,
        main_to_subcat_ids=main_to_subcat_ids,
        errors=errors,
        warnings=warnings,
    )


_transform_224 = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


def _constrained_subcat_id(
    logits: torch.Tensor,
    *,
    main_cat: str,
    main_to_subcat_ids: dict[str, list[int]] | None,
) -> int:
    # logits: [1, C]
    if logits.ndim == 2:
        logits_1d = logits[0]
    else:
        logits_1d = logits.reshape(-1)

    allowed = []
    if main_to_subcat_ids is not None:
        allowed = main_to_subcat_ids.get(main_cat, [])

    if not allowed:
        return int(torch.argmax(logits_1d).item())

    valid_allowed = [idx for idx in allowed if 0 <= idx < int(logits_1d.numel())]
    if not valid_allowed:
        return int(torch.argmax(logits_1d).item())

    best_idx = max(valid_allowed, key=lambda idx: float(logits_1d[idx].item()))
    return int(best_idx)


def analyze_single_item(
    *,
    models: LoadedModels,
    image: Image.Image,
    yolo_conf: float,
    yolo_iou: float,
    yolo_main_categories: tuple[str, ...],
    forced_main_category: str | None = None,
) -> dict[str, Any]:
    """Implements the guide pipeline for one garment image.

    Returns: {main_category, sub_category, bbox, model_confidence}
    """

    if models.yolo is None:
        raise RuntimeError("YOLO model not loaded")

    image = ImageOps.exif_transpose(image).convert("RGB")

    # YOLO detect
    yolo_results = models.yolo(image, conf=yolo_conf, iou=yolo_iou)

    # pick best box by confidence
    best = None
    for result in yolo_results:
        for box in result.boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            xyxy = box.xyxy[0].tolist()
            name = None
            try:
                # ultralytics typically exposes a dict-like names mapping
                name = result.names.get(cls_id) if hasattr(result, "names") and isinstance(result.names, dict) else None
                if name is None and hasattr(result, "names") and isinstance(result.names, (list, tuple)):
                    name = result.names[cls_id]
            except Exception:
                name = None
            if best is None or conf > best["conf"]:
                best = {"conf": conf, "cls_id": cls_id, "bbox": xyxy, "name": name}

    if best is None:
        yolo_main = "tops"
        bbox = [0.0, 0.0, float(image.width), float(image.height)]
        crop = image
        yolo_confidence = 0.0
    else:
        cls_id = best["cls_id"]
        raw_name = best.get("name")
        expected = set(yolo_main_categories)

        if isinstance(raw_name, str) and raw_name.strip().lower() in expected:
            yolo_main = raw_name.strip().lower()
        else:
            yolo_main = yolo_main_categories[cls_id] if 0 <= cls_id < len(yolo_main_categories) else "tops"
        bbox = [float(x) for x in best["bbox"]]
        crop = image.crop((bbox[0], bbox[1], bbox[2], bbox[3]))
        yolo_confidence = float(best["conf"])

    main_cat = forced_main_category if forced_main_category and forced_main_category != "auto" else yolo_main

    # If ResNet18 isn't available, still return a valid wardrobe item.
    if models.resnet18_subcat is None:
        return {
            "main_category": main_cat,
            "sub_category": "unknown",
            "bbox": bbox,
            "model_confidence": None,
            "yolo_confidence": yolo_confidence,
        }

    # ResNet18 logits
    input_tensor = _transform_224(crop).unsqueeze(0)
    with torch.no_grad():
        logits = models.resnet18_subcat(input_tensor)

    # If model returns scalar, treat as "unknown" subcat
    if not hasattr(logits, "shape") or logits.numel() == 1:
        subcat_id = 0
        subcat_name = "unknown"
        model_conf = float(torch.sigmoid(logits.reshape(-1)[0]).item()) if hasattr(logits, "numel") else None
    else:
        subcat_id = _constrained_subcat_id(logits, main_cat=main_cat, main_to_subcat_ids=models.main_to_subcat_ids)

        subcat_name = str(subcat_id)
        if models.subcat_mapping is not None:
            mapped = models.subcat_mapping.get(str(subcat_id))
            if isinstance(mapped, str):
                subcat_name = mapped

        # Fix main category if mapping exists
        if models.subcat_to_main is not None:
            corrected = models.subcat_to_main.get(subcat_name)
            if isinstance(corrected, str):
                main_cat = corrected

        # confidence estimate from softmax
        probs = torch.nn.functional.softmax(logits, dim=1)
        model_conf = float(probs[0, subcat_id].item())

    return {
        "main_category": main_cat,
        "sub_category": subcat_name,
        "bbox": bbox,
        "model_confidence": model_conf,
        "yolo_confidence": yolo_confidence,
    }


def bbox_to_json(bbox: list[float]) -> str:
    return json.dumps([float(x) for x in bbox])


def embedding_to_json(embedding: list[float]) -> str:
    return json.dumps([float(x) for x in embedding])


def extract_item_embedding(
    *,
    models: LoadedModels,
    image: Image.Image,
    bbox: list[float] | None = None,
) -> list[float] | None:
    """Extract and L2-normalize the ResNet50 backbone embedding for one item."""

    model = models.resnet50_compat
    if model is None or not all(hasattr(model, attr) for attr in ("backbone", "pool")):
        return None

    image = ImageOps.exif_transpose(image).convert("RGB")
    if bbox is not None and len(bbox) == 4:
        x1, y1, x2, y2 = [float(x) for x in bbox]
        if x2 > x1 and y2 > y1:
            image = image.crop((x1, y1, x2, y2))

    tensor = _transform_224(image).unsqueeze(0)
    with torch.no_grad():
        features = model.backbone(tensor)
        features = model.pool(features)
        features = torch.flatten(features, 1)[0]
        features = torch.nn.functional.normalize(features, dim=0)

    return [float(x) for x in features.cpu().tolist()]


def score_outfit_compatibility(
    *,
    models: LoadedModels,
    image_paths: list[str],
) -> float | None:
    """Return the ResNet50 compatibility score used to rank candidate outfits."""

    model = models.resnet50_compat
    if model is None or not image_paths:
        return None

    images: list[Image.Image] = []
    for path in image_paths[:8]:
        try:
            images.append(ImageOps.exif_transpose(Image.open(path)).convert("RGB"))
        except Exception:
            continue

    if not images:
        return None

    batch = torch.stack([_transform_224(img) for img in images], dim=0)

    with torch.no_grad():
        if all(hasattr(model, attr) for attr in ("backbone", "pool", "scorer")):
            features = model.backbone(batch)
            features = model.pool(features)
            features = torch.flatten(features, 1).mean(dim=0, keepdim=True)
            raw = model.scorer(features)
        else:
            raw = model(batch)
            if raw.ndim > 0 and raw.numel() > 1:
                raw = raw.reshape(-1).mean().reshape(1)

    value = float(raw.reshape(-1)[0].item())
    if 0.0 <= value <= 1.0:
        return value
    return float(torch.sigmoid(torch.tensor(value)).item())


def score_outfit_embeddings(
    *,
    models: LoadedModels,
    embeddings: list[list[float]],
) -> float | None:
    """Score an outfit from cached item embeddings without reopening images."""

    model = models.resnet50_compat
    if model is None or not embeddings or not hasattr(model, "scorer"):
        return None

    try:
        tensor = torch.tensor(embeddings, dtype=torch.float32)
    except Exception:
        return None

    if tensor.ndim != 2 or tensor.shape[0] == 0:
        return None

    with torch.no_grad():
        avg = tensor.mean(dim=0, keepdim=True)
        raw = model.scorer(avg)

    value = float(raw.reshape(-1)[0].item())
    if 0.0 <= value <= 1.0:
        return value
    return float(torch.sigmoid(torch.tensor(value)).item())
