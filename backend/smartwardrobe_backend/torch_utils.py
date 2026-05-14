from __future__ import annotations

from pathlib import Path
import torch
import torchvision.models as tv_models


def _safe_torch_load(path: Path):
    """Best-effort safe torch.load.

    Uses weights_only=True when available to avoid unpickling arbitrary code.
    Falls back to regular torch.load for older Torch or non-weights checkpoints.
    """

    try:
        return torch.load(
            str(path),
            map_location=torch.device("cpu"),
            weights_only=True,  # torch>=2.0
        )
    except Exception:
        # Fallback for checkpoints that include non-tensor metadata or are not
        # compatible with weights_only.
        return torch.load(str(path), map_location=torch.device("cpu"))


def _strip_module_prefix(state_dict: dict) -> dict:
    if not state_dict:
        return state_dict
    if any(k.startswith("module.") for k in state_dict.keys()):
        return {k[len("module.") :]: v for k, v in state_dict.items()}
    return state_dict


def _infer_resnet_variant_from_state_dict(state_dict: dict) -> str:
    keys = list(state_dict.keys())
    has_bottleneck = any(".conv3." in k for k in keys)

    def _max_block_index(layer_prefix: str) -> int:
        max_idx = -1
        prefix = layer_prefix + "."
        for k in keys:
            if not k.startswith(prefix):
                continue
            rest = k[len(prefix) :]
            parts = rest.split(".", 1)
            if not parts:
                continue
            try:
                idx = int(parts[0])
            except ValueError:
                continue
            max_idx = max(max_idx, idx)
        return max_idx

    layer3_blocks = _max_block_index("layer3") + 1

    if not has_bottleneck:
        return "resnet34" if layer3_blocks > 2 else "resnet18"

    if layer3_blocks <= 6:
        return "resnet50"
    if layer3_blocks <= 23:
        return "resnet101"
    return "resnet152"


def _infer_resnet_variant_from_backbone_state_dict(state_dict: dict) -> str:
    keys = [k for k in state_dict.keys() if isinstance(k, str) and k.startswith("backbone.")]
    has_bottleneck = any(".conv3." in k for k in keys)

    def _max_block_index(layer_prefix: str) -> int:
        max_idx = -1
        prefix = layer_prefix + "."
        for k in keys:
            if not k.startswith(prefix):
                continue
            rest = k[len(prefix) :]
            parts = rest.split(".", 1)
            if not parts:
                continue
            try:
                idx = int(parts[0])
            except ValueError:
                continue
            max_idx = max(max_idx, idx)
        return max_idx

    # backbone.6 corresponds to torchvision resnet layer3
    layer3_blocks = _max_block_index("backbone.6") + 1

    if not has_bottleneck:
        return "resnet34" if layer3_blocks > 2 else "resnet18"

    if layer3_blocks <= 6:
        return "resnet50"
    if layer3_blocks <= 23:
        return "resnet101"
    return "resnet152"


class _BackboneScorer(torch.nn.Module):
    def __init__(self, backbone: torch.nn.Module, scorer: torch.nn.Module):
        super().__init__()
        self.backbone = backbone
        self.pool = torch.nn.AdaptiveAvgPool2d((1, 1))
        self.scorer = scorer

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.backbone(x)
        x = self.pool(x)
        x = torch.flatten(x, 1)
        return self.scorer(x)


def load_backbone_scorer_state_dict_model(model_path: Path) -> torch.nn.Module:
    loaded = _safe_torch_load(model_path)

    if isinstance(loaded, torch.nn.Module):
        loaded.eval()
        return loaded

    if isinstance(loaded, dict) and "state_dict" in loaded and isinstance(loaded["state_dict"], dict):
        state_dict = loaded["state_dict"]
    else:
        state_dict = loaded

    if not isinstance(state_dict, dict):
        raise TypeError(f"Unsupported checkpoint type: {type(loaded)}")

    state_dict = _strip_module_prefix(state_dict)

    if not any(isinstance(k, str) and k.startswith("backbone.") for k in state_dict.keys()):
        raise ValueError("Checkpoint does not look like a backbone/scorer state_dict")
    if not any(isinstance(k, str) and k.startswith("scorer.") for k in state_dict.keys()):
        raise ValueError("Checkpoint does not look like a backbone/scorer state_dict")

    variant = _infer_resnet_variant_from_backbone_state_dict(state_dict)
    if not hasattr(tv_models, variant):
        raise ValueError(f"Unsupported inferred ResNet variant for backbone: {variant}")

    model_fn = getattr(tv_models, variant)
    base = model_fn(weights=None)
    backbone = torch.nn.Sequential(*list(base.children())[:8])

    # Build scorer (assumes at least scorer.0 and scorer.3 Linear layers as commonly used)
    w0 = state_dict.get("scorer.0.weight")
    b0 = state_dict.get("scorer.0.bias")
    w_last = state_dict.get("scorer.3.weight")
    b_last = state_dict.get("scorer.3.bias")

    if not (hasattr(w0, "shape") and len(w0.shape) == 2 and hasattr(w_last, "shape") and len(w_last.shape) == 2):
        # Fallback: create a simple Linear head sized from the last available 2D scorer weight
        scorer_weights = []
        for k, v in state_dict.items():
            if isinstance(k, str) and k.startswith("scorer.") and k.endswith(".weight") and hasattr(v, "shape") and len(v.shape) == 2:
                try:
                    idx = int(k.split(".")[1])
                except Exception:
                    continue
                scorer_weights.append((idx, k, v))
        scorer_weights.sort(key=lambda t: t[0])
        if not scorer_weights:
            raise ValueError("No scorer Linear weights found")
        _, k_last, w_any = scorer_weights[-1]
        num_classes = int(w_any.shape[0])
        in_features = int(w_any.shape[1])
        scorer = torch.nn.Sequential(torch.nn.Linear(in_features, num_classes))
    else:
        in_features = int(w0.shape[1])
        hidden = int(w0.shape[0])
        num_classes = int(w_last.shape[0])
        scorer = torch.nn.Sequential(
            torch.nn.Linear(in_features, hidden, bias=b0 is not None),
            torch.nn.ReLU(),
            torch.nn.Dropout(p=0.0),
            torch.nn.Linear(hidden, num_classes, bias=b_last is not None),
        )

    model = _BackboneScorer(backbone=backbone, scorer=scorer)
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    return model


def load_resnet_state_dict_model(model_path: Path) -> torch.nn.Module:
    loaded = _safe_torch_load(model_path)

    if isinstance(loaded, torch.nn.Module):
        loaded.eval()
        return loaded

    if isinstance(loaded, dict) and "state_dict" in loaded and isinstance(loaded["state_dict"], dict):
        state_dict = loaded["state_dict"]
    else:
        state_dict = loaded

    if not isinstance(state_dict, dict):
        raise TypeError(f"Unsupported checkpoint type: {type(loaded)}")

    state_dict = _strip_module_prefix(state_dict)

    # Determine variant and class count
    variant = _infer_resnet_variant_from_state_dict(state_dict)
    if not hasattr(tv_models, variant):
        raise ValueError(f"Unsupported inferred ResNet variant: {variant}")

    model_fn = getattr(tv_models, variant)
    model = model_fn(weights=None)

    fc_weight = state_dict.get("fc.weight")
    if fc_weight is None or not hasattr(fc_weight, "shape"):
        # Some custom heads may not be standard resnet; in that case, try strict load and fail loudly.
        model.load_state_dict(state_dict, strict=True)
        model.eval()
        return model

    num_classes = int(fc_weight.shape[0])
    in_features = model.fc.in_features
    model.fc = torch.nn.Linear(in_features, num_classes)

    model.load_state_dict(state_dict, strict=True)
    model.eval()
    return model
