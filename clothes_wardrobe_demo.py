"""
Clothes folder wardrobe demo.

Run:
    python clothes_wardrobe_demo.py

Required for the web UI:
    pip install gradio pillow

Optional model-based classification/scoring:
    pip install torch torchvision ultralytics opencv-python
"""

from __future__ import annotations

import itertools
import math
import random
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
CLOTHES_DIR = ROOT / "clothes"
MODEL_DIR = ROOT / "MODELLER"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp"}
MAIN_CATS = ["tops", "bottoms", "outerwear", "all-body", "shoes"]
CLASS_NAMES = {0: "tops", 1: "bottoms", 2: "outerwear", 3: "all-body", 4: "shoes"}
WARDROBE_CACHE = {"signature": None, "wardrobe": None}


def preferred_model_paths(root: Path = ROOT) -> dict[str, Path]:
    model_dir = root / "MODELLER"
    improved_resnet18 = model_dir / "resnet18_subcat_improved.pth"
    improved_mapping = model_dir / "subcat_mapping_improved.json"
    improved_subcat_to_main = model_dir / "subcat_to_main_improved.json"
    improved_main_to_subcat_ids = model_dir / "main_to_subcat_ids_improved.json"

    return {
        "yolo": model_dir / "YOLOV8_best.pt",
        "resnet18": improved_resnet18 if improved_resnet18.exists() else model_dir / "resnet18_subcat.pth",
        "resnet50": model_dir / "resnet50.pth",
        "subcat_mapping": improved_mapping if improved_mapping.exists() else model_dir / "subcat_mapping.json",
        "subcat_to_main": improved_subcat_to_main if improved_subcat_to_main.exists() else model_dir / "subcat_to_main.json",
        "main_to_subcat_ids": (
            improved_main_to_subcat_ids
            if improved_main_to_subcat_ids.exists()
            else model_dir / "main_to_subcat_ids.json"
        ),
    }


def constrained_subcat_id(logits, main_cat: str, main_to_subcat_ids: dict[str, list[int]]) -> int:
    try:
        scores = logits.detach().cpu().tolist()
    except AttributeError:
        scores = list(logits)

    allowed = main_to_subcat_ids.get(main_cat) or []
    allowed = [int(idx) for idx in allowed if 0 <= int(idx) < len(scores)]
    if not allowed:
        return int(max(range(len(scores)), key=lambda idx: scores[idx]))
    return int(max(allowed, key=lambda idx: scores[idx]))


WEATHER_MAP = {
    "hot": {
        "tops": ["tank", "tank top", "sleeveless top", "tshirt", "male t-shirt", "top", "blouse", "male polos"],
        "bottoms": ["shorts", "male knee-length shorts", "skirt", "tennis skirt", "male swim shorts"],
        "shoes": ["flat sandals", "sandals", "flip-flops", "flats", "male flip-flops"],
        "all-body": ["dress", "romper", "swimsuit", "one-piece swimsuit"],
        "outerwear": [],
    },
    "mild": {
        "tops": ["shirt", "male shirt", "blouse", "tshirt", "male t-shirt", "sweater", "top", "male polos"],
        "bottoms": ["jeans", "male jeans", "pants", "male pants", "skirt", "long skirt"],
        "shoes": ["sneakers", "male sneakers", "flats", "closed shoes", "male shoes", "male loafers"],
        "all-body": ["dress", "jumpsuit", "set/suit", "male suit"],
        "outerwear": ["blazer", "jacket", "cardigan", "male formal jacket", "male jacket", "male vest"],
    },
    "cold": {
        "tops": ["sweater", "male sweater", "long-sleeve shirt", "sweatshirt", "sweathirt", "hoodie"],
        "bottoms": ["jeans", "male jeans", "pants", "male pants", "sweatpants", "male sweatpants", "track pants"],
        "shoes": ["boots", "flat boots", "closed shoes", "sneakers", "male sneakers"],
        "all-body": ["set/suit", "jumpsuit", "male suit"],
        "outerwear": ["coat", "trench coat", "jacket/coat", "jacket", "male jacket", "male formal jacket", "cardigan"],
    },
    "rainy": {
        "tops": ["sweater", "long-sleeve shirt", "hoodie", "sweatshirt"],
        "bottoms": ["jeans", "male jeans", "pants", "male pants"],
        "shoes": ["boots", "flat boots", "closed shoes"],
        "all-body": ["dress", "jumpsuit", "set/suit"],
        "outerwear": ["trench coat", "coat", "jacket/coat", "jacket", "parka"],
    },
}

EVENT_MAP = {
    "casual": {
        "tops": ["tshirt", "male t-shirt", "shirt", "male shirt", "male polos", "hoodie", "sweatshirt", "top"],
        "bottoms": ["jeans", "male jeans", "shorts", "male knee-length shorts", "sweatpants", "male sweatpants"],
        "shoes": ["sneakers", "male sneakers", "flats", "male flip-flops"],
        "all-body": ["dress", "romper", "jumpsuit"],
        "outerwear": ["jacket", "male jacket", "cardigan", "track jacket", "male track jacket"],
    },
    "formal": {
        "tops": ["blouse", "shirt", "male shirt", "long-sleeve shirt", "turtleneck sweater"],
        "bottoms": ["pants", "male suit pants", "skirt", "long skirt"],
        "shoes": ["heels", "pump", "closed shoes", "male formal shoes", "male loafers"],
        "all-body": ["dress", "gown", "set/suit", "jumpsuit", "male suit"],
        "outerwear": ["blazer", "coat", "trench coat", "male formal jacket", "male suit jacket"],
    },
    "business": {
        "tops": ["blouse", "shirt", "male shirt", "long-sleeve shirt", "male polos"],
        "bottoms": ["pants", "male pants", "male suit pants", "skirt"],
        "shoes": ["heels", "pump", "closed shoes", "male formal shoes", "male loafers"],
        "all-body": ["dress", "set/suit", "male suit"],
        "outerwear": ["blazer", "jacket", "male formal jacket", "male suit jacket"],
    },
    "sport": {
        "tops": ["sports bra", "sports long-sleeve shirt", "male sports shirt", "tshirt", "male t-shirt", "tank"],
        "bottoms": ["shorts", "sports shorts", "male sports shorts", "sweatpants", "track pants", "male track pants"],
        "shoes": ["sneakers", "male sneakers"],
        "all-body": ["set/suit"],
        "outerwear": ["track jacket", "male track jacket"],
    },
}

MOOD_MAP = {
    "happy": {
        "tops": ["tshirt", "male t-shirt", "blouse", "tank top", "top", "male polos"],
        "bottoms": ["skirt", "shorts", "male knee-length shorts", "jeans", "male jeans"],
        "shoes": ["sneakers", "male sneakers", "flat sandals", "flats"],
        "all-body": ["dress", "romper"],
        "outerwear": ["cardigan", "jacket", "male jacket"],
    },
    "professional": {
        "tops": ["blouse", "shirt", "male shirt", "long-sleeve shirt"],
        "bottoms": ["pants", "male pants", "male suit pants", "skirt"],
        "shoes": ["heels", "pump", "closed shoes", "male formal shoes", "male loafers"],
        "all-body": ["dress", "set/suit", "male suit"],
        "outerwear": ["blazer", "male formal jacket", "male suit jacket"],
    },
    "relaxed": {
        "tops": ["sweater", "male sweater", "tshirt", "male t-shirt", "hoodie", "sweatshirt"],
        "bottoms": ["sweatpants", "male sweatpants", "jeans", "male jeans", "shorts"],
        "shoes": ["sneakers", "male sneakers", "flats", "flip-flops", "male flip-flops"],
        "all-body": ["jumpsuit", "romper"],
        "outerwear": ["cardigan", "jacket", "male jacket"],
    },
    "romantic": {
        "tops": ["blouse", "sleeveless top", "top", "shirt"],
        "bottoms": ["skirt", "long skirt"],
        "shoes": ["heels", "sandals", "flats", "pump"],
        "all-body": ["dress", "gown"],
        "outerwear": ["cardigan", "blazer"],
    },
}

SHORT_SUBCATS = {"shorts", "male knee-length shorts", "sports shorts", "male sports shorts", "male swim shorts"}
OPEN_SHOE_SUBCATS = {"flat sandals", "sandals", "flip-flops", "male flip-flops", "slippers", "male slippers"}
RAIN_SAFE_SHOE_SUBCATS = {"boots", "flat boots", "heeled boots", "closed shoes", "male formal shoes"}
FORMAL_SHOE_SUBCATS = {"heels", "pump", "closed shoes", "male formal shoes", "male loafers", "flats"}
BOOT_SUBCATS = {"boots", "flat boots", "heeled boots", "over-the-knee boots"}
SNEAKER_SUBCATS = {"sneakers", "male sneakers"}
CASUAL_SPORT_SUBCATS = {
    "hoodie",
    "sweatshirt",
    "sweathirt",
    "sweatpants",
    "male sweatpants",
    "track pants",
    "male track pants",
    "track jacket",
    "male track jacket",
    "sports bra",
    "sports long-sleeve shirt",
    "male sports shirt",
    "sports shorts",
    "male sports shorts",
}
FORMAL_SUBCATS = {
    "blazer",
    "male formal jacket",
    "male suit jacket",
    "male suit pants",
    "male formal shoes",
    "male loafers",
    "heels",
    "pump",
    "gown",
    "set/suit",
    "male suit",
}
SPORT_SUBCATS = {
    "sports bra",
    "sports long-sleeve shirt",
    "male sports shirt",
    "sports shorts",
    "male sports shorts",
    "track pants",
    "male track pants",
    "track jacket",
    "male track jacket",
    "sneakers",
    "male sneakers",
}
FORMAL_SHIRT_SUBCATS = {"shirt", "male shirt", "blouse", "long-sleeve shirt"}
FORMAL_LAYER_SUBCATS = {"blazer", "male formal jacket", "male suit jacket"}
WARM_TOP_SUBCATS = {"hoodie", "sweater", "male sweater", "sweatshirt", "sweathirt"}
LIGHT_LAYERABLE_TOP_SUBCATS = {
    "blouse",
    "long-sleeve shirt",
    "male polos",
    "male shirt",
    "male t-shirt",
    "shirt",
    "sleeveless top",
    "tank",
    "tank top",
    "top",
}
OUTERWEAR_SUBCATS = {
    "blazer",
    "cardigan",
    "coat",
    "jacket",
    "jacket/coat",
    "kimono",
    "male formal jacket",
    "male jacket",
    "male suit jacket",
    "male track jacket",
    "male vest",
    "parka",
    "track jacket",
    "trench coat",
    "vest",
}
MALE_SUBCATS = {
    "male flip-flops",
    "male formal jacket",
    "male formal shoes",
    "male jacket",
    "male jeans",
    "male knee-length shorts",
    "male loafers",
    "male pants",
    "male polos",
    "male shirt",
    "male shoes",
    "male slippers",
    "male sneakers",
    "male sports shirt",
    "male sports shorts",
    "male suit",
    "male suit jacket",
    "male suit pants",
    "male sweater",
    "male sweatpants",
    "male swim shorts",
    "male t-shirt",
    "male track jacket",
    "male track pants",
    "male vest",
}
FEMALE_SUBCATS = {
    "blouse",
    "bodie",
    "coverup",
    "dress",
    "flat sandals",
    "gown",
    "heeled boots",
    "heels",
    "kimono",
    "long skirt",
    "one-piece swimsuit",
    "over-the-knee boots",
    "platform shoes",
    "pump",
    "pyjama/slip/chemise",
    "romper",
    "skirt",
    "sports bra",
    "swimsuit",
    "swimsuit bottom",
    "swimsuit top",
    "tank",
    "tank top",
    "tennis skirt",
    "tunic",
}
UNISEX_SUBCATS = {
    "boots",
    "cardigan",
    "closed shoes",
    "flat boots",
    "flats",
    "flip-flops",
    "hoodie",
    "jacket/coat",
    "jeans",
    "jumpsuit",
    "pants",
    "set/suit",
    "shorts",
    "sneakers",
    "sweater",
    "sweathirt",
    "sweatpants",
    "top",
    "track jacket",
    "trench coat",
    "vest",
}
SUBCAT_MAIN_CATEGORY = {
    **{subcat: "outerwear" for subcat in OUTERWEAR_SUBCATS},
    **{
        subcat: "tops"
        for subcat in {
            "blouse",
            "bodie",
            "hoodie",
            "long-sleeve shirt",
            "male polos",
            "male shirt",
            "male sports shirt",
            "male sweater",
            "male t-shirt",
            "shirt",
            "sleeveless top",
            "sports bra",
            "sports long-sleeve shirt",
            "sweater",
            "sweathirt",
            "tank",
            "tank top",
            "top",
            "tunic",
        }
    },
    **{
        subcat: "bottoms"
        for subcat in {
            "jeans",
            "long skirt",
            "male jeans",
            "male knee-length shorts",
            "male pants",
            "male sports shorts",
            "male suit pants",
            "male sweatpants",
            "male swim shorts",
            "male track pants",
            "pants",
            "pyjama pants",
            "shorts",
            "skirt",
            "sports shorts",
            "sweatpants",
            "tennis skirt",
            "track pants",
        }
    },
    **{
        subcat: "shoes"
        for subcat in {
            "boots",
            "closed shoes",
            "flat boots",
            "flat sandals",
            "flats",
            "flip-flops",
            "heeled boots",
            "heels",
            "male flip-flops",
            "male formal shoes",
            "male loafers",
            "male shoes",
            "male slippers",
            "male sneakers",
            "over-the-knee boots",
            "platform shoes",
            "pump",
            "slippers",
            "sneakers",
        }
    },
    **{
        subcat: "all-body"
        for subcat in {
            "coverup",
            "dress",
            "gown",
            "jumpsuit",
            "male suit",
            "one-piece swimsuit",
            "pyjama/slip/chemise",
            "romper",
            "set/suit",
            "swimsuit",
        }
    },
}


@dataclass(frozen=True)
class WardrobeItem:
    path: Path | None
    name: str
    main_cat: str
    sub_cat: str
    image: object
    tensor: object | None = None


class OptionalModels:
    def __init__(self) -> None:
        self.ready = False
        self.reason = "Model dependencies are not loaded."
        self.device = None
        self.transform = None
        self.yolo = None
        self.resnet18 = None
        self.resnet50 = None
        self.id_to_subcat = {}
        self.subcat_to_main = {}
        self.main_to_subcat_ids = {}
        self._load()

    def _load(self) -> None:
        try:
            import json
            import torch
            import torch.nn as nn
            from torchvision import models, transforms
            from ultralytics import YOLO
        except Exception as exc:
            self.reason = f"Model mode disabled: {exc}"
            return

        paths = preferred_model_paths(ROOT)
        required = [
            paths["yolo"],
            paths["resnet18"],
            paths["resnet50"],
            paths["subcat_mapping"],
        ]
        missing = [p.name for p in required if not p.exists()]
        if missing:
            self.reason = f"Model mode disabled; missing files: {', '.join(missing)}"
            return

        class CompatibilityModelResNet50(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                resnet = models.resnet50(weights=None)
                self.backbone = nn.Sequential(*list(resnet.children())[:-1])
                self.feature_dim = resnet.fc.in_features
                self.scorer = nn.Sequential(
                    nn.Linear(self.feature_dim, 256),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(256, 1),
                    nn.Sigmoid(),
                )

            def forward(self, images, num_items):
                batch, item_count, channels, height, width = images.size()
                feats = self.backbone(images.view(-1, channels, height, width)).view(batch, item_count, -1)
                mask = (
                    torch.arange(item_count, device=images.device)[None, :] < num_items[:, None]
                ).float().unsqueeze(-1)
                avg = (feats * mask).sum(dim=1) / torch.clamp(num_items.unsqueeze(-1).float(), min=1.0)
                return self.scorer(avg)

        self.torch = torch
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.yolo = YOLO(str(paths["yolo"]))
        with open(paths["subcat_mapping"], "r", encoding="utf-8") as file:
            self.id_to_subcat = {int(k): v for k, v in json.load(file).items()}
        if paths["subcat_to_main"].exists():
            with open(paths["subcat_to_main"], "r", encoding="utf-8") as file:
                self.subcat_to_main = json.load(file)
        if paths["main_to_subcat_ids"].exists():
            with open(paths["main_to_subcat_ids"], "r", encoding="utf-8") as file:
                self.main_to_subcat_ids = {k: [int(v) for v in vals] for k, vals in json.load(file).items()}

        self.resnet18 = models.resnet18(weights=None)
        self.resnet18.fc = nn.Linear(self.resnet18.fc.in_features, len(self.id_to_subcat))
        self.resnet18.load_state_dict(torch.load(paths["resnet18"], map_location=self.device))
        self.resnet18.to(self.device).eval()

        self.resnet50 = CompatibilityModelResNet50()
        self.resnet50.load_state_dict(torch.load(paths["resnet50"], map_location=self.device))
        self.resnet50.to(self.device).eval()

        self.transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ]
        )
        self.ready = True
        constraint_state = "with constrained subcategory mapping" if self.main_to_subcat_ids else "without constrained mapping"
        self.reason = f"Model mode enabled ({constraint_state})."

    def classify(self, pil_image, fallback_name: str, forced_main_cat: str | None = None) -> tuple[str, str, object | None]:
        if not self.ready:
            main, sub = infer_item_from_name(fallback_name)
            if forced_main_cat is not None:
                main = forced_main_cat
            return consistent_main_category(main, sub), sub, None

        import numpy as np

        image_rgb = np.array(pil_image.convert("RGB"))
        detections = self.yolo(image_rgb, verbose=False)
        crop = pil_image.convert("RGB")
        main_cat = "tops"

        if len(detections[0].boxes) > 0:
            box = detections[0].boxes[0]
            main_cat = CLASS_NAMES.get(int(box.cls[0]), "tops")
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            if x2 > x1 and y2 > y1:
                crop = pil_image.crop((x1, y1, x2, y2)).convert("RGB")
        if forced_main_cat is not None:
            main_cat = forced_main_cat

        tensor = self.transform(crop).cpu()
        with self.torch.no_grad():
            logits = self.resnet18(tensor.unsqueeze(0).to(self.device))[0]
            pred = constrained_subcat_id(logits, main_cat, self.main_to_subcat_ids)
        sub_cat = self.id_to_subcat.get(pred, main_cat)
        corrected_main = self.subcat_to_main.get(sub_cat, consistent_main_category(main_cat, sub_cat))
        return corrected_main, sub_cat, tensor

    def score(self, items: Iterable[WardrobeItem]) -> float | None:
        items = list(items)
        if not self.ready or any(item.tensor is None for item in items):
            return None
        with self.torch.no_grad():
            tensors = [item.tensor for item in items[:8]]
            count = len(tensors)
            stack = self.torch.stack(tensors)
            if count < 8:
                stack = self.torch.cat([stack, self.torch.zeros(8 - count, 3, 224, 224)], dim=0)
            inp = stack.unsqueeze(0).to(self.device)
            num = self.torch.tensor([count], dtype=self.torch.long, device=self.device)
            return float(self.resnet50(inp, num).item())


MODELS = OptionalModels()


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value.lower()


def consistent_main_category(main_cat: str, sub_cat: str) -> str:
    return SUBCAT_MAIN_CATEGORY.get(sub_cat, main_cat)


def infer_item_from_name(name: str) -> tuple[str, str]:
    text = normalize_text(Path(name).stem)
    rules = [
        ("outerwear", "male formal jacket", ["blazer", "ceket", "suit-jacket", "formal-jacket"]),
        ("outerwear", "coat", ["mont", "kaban", "coat", "parka", "trench"]),
        ("tops", "hoodie", ["kapuson", "hoodie"]),
        ("tops", "sweatshirt", ["sweatshirt", "sweattshirt", "sweathirt"]),
        ("tops", "male shirt", ["gomlek", "shirt", "oxford", "flanel"]),
        ("tops", "male polos", ["polo"]),
        ("tops", "male t-shirt", ["tisort", "tshirt", "t-shirt", "tişört"]),
        ("bottoms", "male knee-length shorts", ["sort", "short"]),
        ("bottoms", "male jeans", ["kot", "jean"]),
        ("bottoms", "male track pants", ["esofman", "track", "fleece"]),
        ("bottoms", "male suit pants", ["klasik", "kumas-pantolon", "pantolon"]),
        ("shoes", "boots", ["bot", "postal", "boot"]),
        ("shoes", "male formal shoes", ["klasik-ayakkabi", "formal-shoe"]),
        ("shoes", "male sneakers", ["ayakkabi", "sneaker", "spor", "shoes", "adidas", "nike"]),
    ]
    for main_cat, sub_cat, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return main_cat, sub_cat
    return "tops", "top"


def load_pil(path: Path):
    from PIL import Image

    return Image.open(path).convert("RGB")


def item_from_path(path: Path) -> WardrobeItem:
    image = load_pil(path)
    main_cat, sub_cat, tensor = MODELS.classify(image, path.name)
    return WardrobeItem(path=path, name=path.name, main_cat=main_cat, sub_cat=sub_cat, image=image, tensor=tensor)


def wardrobe_signature() -> tuple[tuple[str, int, int], ...]:
    if not CLOTHES_DIR.exists():
        return tuple()
    signature = []
    for path in sorted(CLOTHES_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            stat = path.stat()
            signature.append((path.name, int(stat.st_size), int(stat.st_mtime)))
    return tuple(signature)


def cached_wardrobe(signature=None) -> dict[str, list[WardrobeItem]] | None:
    if signature is None:
        signature = wardrobe_signature()
    if WARDROBE_CACHE.get("signature") == signature and WARDROBE_CACHE.get("wardrobe") is not None:
        return WARDROBE_CACHE["wardrobe"]
    return None


def refresh_wardrobe_cache():
    WARDROBE_CACHE["signature"] = None
    WARDROBE_CACHE["wardrobe"] = None
    return "Wardrobe cache cleared. The next recommendation will rescan clothes."


def build_wardrobe() -> dict[str, list[WardrobeItem]]:
    signature = wardrobe_signature()
    cached = cached_wardrobe(signature)
    if cached is not None:
        return cached

    wardrobe = {cat: [] for cat in MAIN_CATS}
    if not CLOTHES_DIR.exists():
        return wardrobe
    for path in sorted(CLOTHES_DIR.iterdir()):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            try:
                item = item_from_path(path)
                wardrobe[item.main_cat].append(item)
            except Exception as exc:
                print(f"Skipped {path.name}: {exc}")
    WARDROBE_CACHE["signature"] = signature
    WARDROBE_CACHE["wardrobe"] = wardrobe
    return wardrobe


def context_pool(items: list[WardrobeItem], main_cat: str, weather: str, event: str, mood: str) -> list[WardrobeItem]:
    weather_set = set(WEATHER_MAP.get(weather, {}).get(main_cat, []))
    event_set = set(EVENT_MAP.get(event, {}).get(main_cat, []))
    mood_set = set(MOOD_MAP.get(mood, {}).get(main_cat, []))

    strict = [item for item in items if item.sub_cat in weather_set and item.sub_cat in event_set]
    weather_only = [item for item in items if item.sub_cat in weather_set]
    event_only = [item for item in items if item.sub_cat in event_set]

    base = strict or weather_only or event_only or items
    mood_first = [item for item in base if item.sub_cat in mood_set]
    rest = [item for item in base if item.sub_cat not in mood_set]
    return mood_first + rest if mood_first else base


def gender_pool(items: list[WardrobeItem], gender: str) -> list[WardrobeItem]:
    if gender == "no preference":
        return items
    if gender == "male":
        preferred = [item for item in items if item.sub_cat in MALE_SUBCATS]
        if preferred:
            return preferred
        unisex = [item for item in items if item.sub_cat in UNISEX_SUBCATS]
        return unisex or items
    if gender == "female":
        preferred = [item for item in items if item.sub_cat in FEMALE_SUBCATS or item.sub_cat in UNISEX_SUBCATS]
        if preferred:
            return preferred
        non_male = [item for item in items if item.sub_cat not in MALE_SUBCATS]
        return non_male or items
    return items


def outfit_templates(weather: str, event: str, outerwear_required: bool = False) -> list[list[str]]:
    hot = weather == "hot"
    cold = weather == "cold"
    rainy = weather == "rainy"

    if outerwear_required:
        if event in {"formal", "business"}:
            return [
                ["tops", "outerwear", "bottoms", "shoes"],
                ["all-body", "outerwear", "shoes"],
            ]
        if event == "sport":
            return [
                ["tops", "outerwear", "bottoms", "shoes"],
            ]
        return [
            ["tops", "outerwear", "bottoms", "shoes"],
            ["all-body", "outerwear", "shoes"],
        ]

    if event in {"formal", "business"}:
        if hot:
            return [
                ["tops", "bottoms", "shoes"],
                ["all-body", "shoes"],
            ]
        if cold:
            return [
                ["tops", "bottoms", "shoes"],
                ["tops", "outerwear", "bottoms", "shoes"],
                ["all-body", "shoes"],
                ["all-body", "outerwear", "shoes"],
            ]
        return [
            ["tops", "bottoms", "shoes"],
            ["tops", "outerwear", "bottoms", "shoes"],
            ["all-body", "outerwear", "shoes"],
            ["all-body", "shoes"],
        ]
    if event == "sport":
        if rainy:
            return [
                ["tops", "outerwear", "bottoms", "shoes"],
                ["tops", "bottoms", "shoes"],
            ]
        return [
            ["tops", "bottoms", "shoes"],
            ["tops", "outerwear", "bottoms", "shoes"],
        ]
    if hot:
        return [
            ["tops", "bottoms", "shoes"],
            ["all-body", "shoes"],
        ]
    if cold:
        return [
            ["tops", "bottoms", "shoes"],
            ["all-body", "shoes"],
            ["tops", "outerwear", "bottoms", "shoes"],
            ["all-body", "outerwear", "shoes"],
        ]
    return [
        ["tops", "bottoms", "shoes"],
        ["all-body", "shoes"],
        ["tops", "outerwear", "bottoms", "shoes"],
        ["all-body", "outerwear", "shoes"],
    ]


def template_matches_anchor(template: list[str], anchor: WardrobeItem | None) -> bool:
    return anchor is None or anchor.main_cat in template


def heuristic_score(
    items: tuple[WardrobeItem, ...],
    weather: str,
    event: str,
    mood: str,
    gender: str = "no preference",
) -> float:
    score = 0.50
    categories = {item.main_cat for item in items}
    subcats = {item.sub_cat for item in items}
    if {"tops", "bottoms", "shoes"}.issubset(categories):
        score += 0.08
    has_outerwear_subcat = bool(subcats & OUTERWEAR_SUBCATS)
    if has_outerwear_subcat and weather in {"cold", "rainy"}:
        score += 0.18
    if has_outerwear_subcat and weather == "hot":
        score -= 0.25
    if has_outerwear_subcat and weather == "mild":
        if subcats & WARM_TOP_SUBCATS:
            score -= 0.22
        elif subcats & LIGHT_LAYERABLE_TOP_SUBCATS:
            score -= 0.04
        else:
            score -= 0.10

    for item in items:
        if item.sub_cat in WEATHER_MAP.get(weather, {}).get(item.main_cat, []):
            score += 0.06
        if item.sub_cat in EVENT_MAP.get(event, {}).get(item.main_cat, []):
            score += 0.08
        if item.sub_cat in MOOD_MAP.get(mood, {}).get(item.main_cat, []):
            score += 0.04

    if weather in {"cold", "rainy"} and subcats & SHORT_SUBCATS:
        score -= 0.28
    if weather == "rainy" and subcats & OPEN_SHOE_SUBCATS:
        score -= 0.30
    if weather == "rainy" and subcats & RAIN_SAFE_SHOE_SUBCATS:
        score += 0.08

    if event in {"formal", "business"}:
        if subcats & CASUAL_SPORT_SUBCATS:
            score -= 0.30
        if subcats & SNEAKER_SUBCATS:
            score -= 0.16
        if weather in {"cold", "rainy"} and subcats & BOOT_SUBCATS:
            score += 0.07
        if subcats & FORMAL_SHOE_SUBCATS:
            score += 0.08
        if (subcats & FORMAL_SHIRT_SUBCATS) and (subcats & FORMAL_LAYER_SUBCATS):
            score += 0.10
        if "male t-shirt" in subcats and (subcats & FORMAL_LAYER_SUBCATS):
            score -= 0.12

    if event == "sport":
        if subcats & FORMAL_SUBCATS:
            score -= 0.30
        if subcats & SPORT_SUBCATS:
            score += 0.08

    if gender == "male":
        score += 0.05 * len(subcats & MALE_SUBCATS)
        score -= 0.18 * len(subcats & FEMALE_SUBCATS)
    elif gender == "female":
        score += 0.04 * len(subcats & FEMALE_SUBCATS)
        score -= 0.18 * len(subcats & MALE_SUBCATS)

    return max(0.05, min(score, 0.99))


def score_outfit(items: tuple[WardrobeItem, ...], weather: str, event: str, mood: str, gender: str) -> float:
    model_score = MODELS.score(items)
    if model_score is None:
        return heuristic_score(items, weather, event, mood, gender)
    return 0.65 * model_score + 0.35 * heuristic_score(items, weather, event, mood, gender)


def display_scores(scored_outfits: list[tuple[float, tuple[WardrobeItem, ...]]]) -> list[float]:
    if not scored_outfits:
        return []
    raw_scores = [score for score, _ in scored_outfits]
    high = max(raw_scores)
    low = min(raw_scores)
    if high == low:
        ranked = [0.96, 0.88, 0.80]
        return ranked[: len(scored_outfits)]
    return [0.72 + 0.24 * ((score - low) / (high - low)) for score in raw_scores]


def gallery_labels(rank: int, display_score: float, combo: tuple[WardrobeItem, ...]) -> list[str]:
    labels = []
    for index, item in enumerate(combo):
        prefix = f"Outfit {rank} - {display_score * 100:.1f}%" if index == 0 else f"Outfit {rank}"
        labels.append(f"{prefix} | {item.main_cat} / {item.sub_cat} | {item.name}")
    return labels


def recommend_outfits(
    weather: str,
    event: str,
    mood: str,
    gender: str,
    outerwear_required: bool,
    anchor: WardrobeItem | None,
    top_k: int = 3,
    max_trials_per_template: int = 220,
) -> tuple[list[tuple[float, tuple[WardrobeItem, ...]]], dict[str, list[WardrobeItem]]]:
    wardrobe = build_wardrobe()
    pools = {
        cat: gender_pool(context_pool(items, cat, weather, event, mood), gender)
        for cat, items in wardrobe.items()
    }
    scored: list[tuple[float, tuple[WardrobeItem, ...]]] = []
    seen: set[tuple[str, ...]] = set()

    for template in outfit_templates(weather, event, outerwear_required=outerwear_required):
        if not template_matches_anchor(template, anchor):
            continue

        choices = []
        valid = True
        for cat in template:
            if anchor is not None and anchor.main_cat == cat:
                choices.append([anchor])
            elif pools.get(cat):
                choices.append(pools[cat])
            else:
                valid = False
                break
        if not valid:
            continue

        combo_count = math.prod(len(pool) for pool in choices)
        if combo_count <= max_trials_per_template:
            combos = itertools.product(*choices)
        else:
            combos = (tuple(random.choice(pool) for pool in choices) for _ in range(max_trials_per_template))

        for combo in combos:
            key = tuple(sorted(str(item.path or item.name) for item in combo))
            if key in seen:
                continue
            seen.add(key)
            scored.append((score_outfit(tuple(combo), weather, event, mood, gender), tuple(combo)))

    scored.sort(key=lambda row: row[0], reverse=True)
    return scored[:top_k], wardrobe


def uploaded_to_item(uploaded_image, uploaded_category: str) -> WardrobeItem | None:
    if uploaded_image is None:
        return None

    image = uploaded_image.convert("RGB")
    if uploaded_category == "auto":
        main_cat, sub_cat, tensor = MODELS.classify(image, "uploaded_item.jpg")
    else:
        main_cat = uploaded_category
        fallback_sub = {
            "tops": "top",
            "bottoms": "pants",
            "outerwear": "jacket",
            "all-body": "dress",
            "shoes": "male shoes",
        }[uploaded_category]
        _, sub_cat, tensor = (
            MODELS.classify(image, fallback_sub, forced_main_cat=main_cat)
            if MODELS.ready
            else (main_cat, fallback_sub, None)
        )
    return WardrobeItem(path=None, name="uploaded_item", main_cat=main_cat, sub_cat=sub_cat, image=image, tensor=tensor)


def gallery_result(
    weather: str,
    event: str,
    mood: str,
    gender: str,
    outerwear_required: bool,
    uploaded_image,
    uploaded_category: str,
):
    anchor = uploaded_to_item(uploaded_image, uploaded_category)
    recs, wardrobe = recommend_outfits(weather, event, mood, gender, outerwear_required, anchor)
    counts = " | ".join(f"{cat}: {len(items)}" for cat, items in wardrobe.items())
    status = f"{MODELS.reason}\nGender: {gender}\nOuterwear required: {outerwear_required}\nWardrobe: {counts}"
    if anchor:
        status += f"\nUploaded item: {anchor.main_cat} / {anchor.sub_cat}"

    if not recs:
        return [], status + "\nNo valid outfit found. Add missing categories to clothes or choose a softer context."

    gallery = []
    for rank, ((raw_score, combo), shown_score) in enumerate(zip(recs, display_scores(recs)), 1):
        for item, label in zip(combo, gallery_labels(rank, shown_score, combo)):
            gallery.append((item.image, label))
    return gallery, status


def launch() -> None:
    try:
        import gradio as gr
        from PIL import Image  # noqa: F401
    except Exception as exc:
        print("This demo needs gradio and pillow for the upload UI.")
        print("Install them with: pip install gradio pillow")
        print(f"Import error: {exc}")
        return

    with gr.Blocks(title="Smart Wardrobe Clothes Demo") as app:
        gr.Markdown("# Smart Wardrobe - Clothes Folder Demo")
        with gr.Row():
            weather = gr.Dropdown(["hot", "mild", "cold", "rainy"], value="mild", label="Weather")
            event = gr.Dropdown(["casual", "formal", "business", "sport"], value="casual", label="Event")
            mood = gr.Dropdown(["happy", "professional", "relaxed", "romantic"], value="happy", label="Mood")
            gender = gr.Dropdown(["male", "female", "no preference"], value="no preference", label="Gender")
            outerwear_required = gr.Checkbox(value=False, label="Require outerwear")
        with gr.Row():
            uploaded = gr.Image(type="pil", label="Upload a clothing item")
            uploaded_category = gr.Dropdown(
                ["auto", "tops", "bottoms", "outerwear", "all-body", "shoes"],
                value="auto",
                label="Uploaded item category",
            )
        button = gr.Button("Recommend 3 outfits", variant="primary")
        refresh_button = gr.Button("Refresh wardrobe")
        status = gr.Textbox(label="Status", lines=4)
        gallery = gr.Gallery(label="Recommended outfits", columns=4, height="auto")
        button.click(
            gallery_result,
            inputs=[weather, event, mood, gender, outerwear_required, uploaded, uploaded_category],
            outputs=[gallery, status],
        )
        refresh_button.click(refresh_wardrobe_cache, outputs=status)

    app.launch()


if __name__ == "__main__":
    launch()
