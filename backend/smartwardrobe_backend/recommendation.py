from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Callable

from .storage import WardrobeItem


@dataclass(frozen=True)
class RecommendContext:
    weather: str
    event: str
    mood: str
    gender: str
    outerwear_required: bool


MAIN_TOPS = "tops"
MAIN_BOTTOMS = "bottoms"
MAIN_OUTERWEAR = "outerwear"
MAIN_ALL_BODY = "all-body"
MAIN_SHOES = "shoes"


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
    "smart-casual": {
        "tops": ["blouse", "shirt", "male shirt", "long-sleeve shirt", "male polos", "male t-shirt", "sweater"],
        "bottoms": ["pants", "male pants", "male suit pants", "jeans", "male jeans", "skirt", "long skirt"],
        "shoes": ["closed shoes", "male formal shoes", "male loafers", "flats", "sneakers", "male sneakers"],
        "all-body": ["dress", "set/suit", "jumpsuit", "male suit"],
        "outerwear": ["blazer", "jacket", "cardigan", "male formal jacket", "male suit jacket", "male jacket"],
    },
    "formal": {
        "tops": ["blouse", "shirt", "male shirt", "long-sleeve shirt", "turtleneck sweater"],
        "bottoms": ["pants", "male suit pants", "skirt", "long skirt"],
        "shoes": ["heels", "pump", "closed shoes", "male formal shoes", "male loafers"],
        "all-body": ["dress", "gown", "set/suit", "jumpsuit", "male suit"],
        "outerwear": ["blazer", "coat", "trench coat", "male formal jacket", "male suit jacket"],
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
    "calm": {
        "tops": ["sweater", "male sweater", "shirt", "male shirt", "blouse", "top", "male polos"],
        "bottoms": ["pants", "male pants", "jeans", "male jeans", "long skirt"],
        "shoes": ["flats", "closed shoes", "male loafers", "male shoes", "sneakers", "male sneakers"],
        "all-body": ["dress", "jumpsuit", "set/suit"],
        "outerwear": ["cardigan", "jacket", "male jacket", "blazer"],
    },
}

MALE_SUBCATS = {
    "male flip-flops", "male formal jacket", "male formal shoes", "male jacket", "male jeans",
    "male knee-length shorts", "male loafers", "male pants", "male polos", "male shirt",
    "male shoes", "male slippers", "male sneakers", "male sports shirt", "male sports shorts",
    "male suit", "male suit jacket", "male suit pants", "male sweater", "male sweatpants",
    "male swim shorts", "male t-shirt", "male track jacket", "male track pants", "male vest",
}
FEMALE_SUBCATS = {
    "blouse", "bodie", "coverup", "dress", "flat sandals", "gown", "heeled boots", "heels",
    "kimono", "long skirt", "one-piece swimsuit", "over-the-knee boots", "platform shoes",
    "pump", "pyjama/slip/chemise", "romper", "skirt", "sports bra", "swimsuit",
    "swimsuit bottom", "swimsuit top", "tank", "tank top", "tennis skirt", "tunic",
}
UNISEX_SUBCATS = {
    "boots", "cardigan", "closed shoes", "flat boots", "flats", "flip-flops", "hoodie",
    "jacket/coat", "jeans", "jumpsuit", "pants", "set/suit", "shorts", "sneakers",
    "sweater", "sweathirt", "sweatpants", "top", "track jacket", "trench coat", "vest",
}
SHORT_SUBCATS = {"shorts", "male knee-length shorts", "sports shorts", "male sports shorts", "male swim shorts"}
OPEN_SHOE_SUBCATS = {"flat sandals", "sandals", "flip-flops", "male flip-flops", "slippers", "male slippers"}
RAIN_SAFE_SHOE_SUBCATS = {"boots", "flat boots", "heeled boots", "closed shoes", "male formal shoes"}
FORMAL_SHOE_SUBCATS = {"heels", "pump", "closed shoes", "male formal shoes", "male loafers", "flats"}
BOOT_SUBCATS = {"boots", "flat boots", "heeled boots", "over-the-knee boots"}
SNEAKER_SUBCATS = {"sneakers", "male sneakers"}
CASUAL_SPORT_SUBCATS = {
    "hoodie", "sweatshirt", "sweathirt", "sweatpants", "male sweatpants",
    "track pants", "male track pants", "track jacket", "male track jacket",
    "sports bra", "sports long-sleeve shirt", "male sports shirt",
    "sports shorts", "male sports shorts",
}
FORMAL_SUBCATS = {
    "blazer", "male formal jacket", "male suit jacket", "male suit pants",
    "male formal shoes", "male loafers", "heels", "pump", "gown",
    "set/suit", "male suit",
}
SPORT_SUBCATS = {
    "sports bra", "sports long-sleeve shirt", "male sports shirt", "sports shorts",
    "male sports shorts", "track pants", "male track pants", "track jacket",
    "male track jacket", "sneakers", "male sneakers",
}
FORMAL_SHIRT_SUBCATS = {"shirt", "male shirt", "blouse", "long-sleeve shirt"}
FORMAL_LAYER_SUBCATS = {"blazer", "male formal jacket", "male suit jacket"}
WARM_TOP_SUBCATS = {"hoodie", "sweater", "male sweater", "sweatshirt", "sweathirt"}
LIGHT_LAYERABLE_TOP_SUBCATS = {
    "blouse", "long-sleeve shirt", "male polos", "male shirt", "male t-shirt",
    "shirt", "sleeveless top", "tank", "tank top", "top",
}
OUTERWEAR_SUBCATS = {
    "blazer", "cardigan", "coat", "jacket", "jacket/coat", "kimono",
    "male formal jacket", "male jacket", "male suit jacket", "male track jacket",
    "male vest", "parka", "track jacket", "trench coat", "vest",
}


def _sub(item: WardrobeItem) -> str:
    return item.sub_category.strip().lower()


def _main(item: WardrobeItem) -> str:
    return item.main_category.strip().lower()


def _context_pool(items: list[WardrobeItem], main_cat: str, ctx: RecommendContext) -> list[WardrobeItem]:
    weather_set = set(WEATHER_MAP.get(ctx.weather, {}).get(main_cat, []))
    event_set = set(EVENT_MAP.get(ctx.event, {}).get(main_cat, []))
    mood_set = set(MOOD_MAP.get(ctx.mood, {}).get(main_cat, []))

    strict = [item for item in items if _sub(item) in weather_set and _sub(item) in event_set]
    weather_only = [item for item in items if _sub(item) in weather_set]
    event_only = [item for item in items if _sub(item) in event_set]

    base = strict or weather_only or event_only or items
    known = [item for item in base if _sub(item) != "unknown"]
    base = known or base

    mood_first = [item for item in base if _sub(item) in mood_set]
    rest = [item for item in base if _sub(item) not in mood_set]
    return mood_first + rest if mood_first else base


def _gender_pool(items: list[WardrobeItem], gender: str) -> list[WardrobeItem]:
    if gender == "no preference":
        return items
    if gender == "male":
        preferred = [item for item in items if _sub(item) in MALE_SUBCATS]
        if preferred:
            return preferred
        unisex = [item for item in items if _sub(item) in UNISEX_SUBCATS]
        return unisex or items
    if gender == "female":
        preferred = [item for item in items if _sub(item) in FEMALE_SUBCATS or _sub(item) in UNISEX_SUBCATS]
        if preferred:
            return preferred
        non_male = [item for item in items if _sub(item) not in MALE_SUBCATS]
        return non_male or items
    return items


def _outfit_templates(ctx: RecommendContext) -> list[tuple[str, ...]]:
    hot = ctx.weather == "hot"
    cold = ctx.weather == "cold"
    rainy = ctx.weather == "rainy"

    if ctx.outerwear_required:
        if ctx.event in {"formal", "smart-casual"}:
            return [
                (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
                (MAIN_ALL_BODY, MAIN_OUTERWEAR, MAIN_SHOES),
            ]
        if ctx.event == "sport":
            return [(MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES)]
        return [
            (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
            (MAIN_ALL_BODY, MAIN_OUTERWEAR, MAIN_SHOES),
        ]

    if ctx.event in {"formal", "smart-casual"}:
        if hot:
            return [(MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES), (MAIN_ALL_BODY, MAIN_SHOES)]
        if cold:
            return [
                (MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES),
                (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
                (MAIN_ALL_BODY, MAIN_SHOES),
                (MAIN_ALL_BODY, MAIN_OUTERWEAR, MAIN_SHOES),
            ]
        return [
            (MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES),
            (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
            (MAIN_ALL_BODY, MAIN_OUTERWEAR, MAIN_SHOES),
            (MAIN_ALL_BODY, MAIN_SHOES),
        ]

    if ctx.event == "sport":
        if rainy:
            return [
                (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
                (MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES),
            ]
        return [
            (MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES),
            (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
        ]

    if hot:
        return [(MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES), (MAIN_ALL_BODY, MAIN_SHOES)]
    if cold:
        return [
            (MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES),
            (MAIN_ALL_BODY, MAIN_SHOES),
            (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
            (MAIN_ALL_BODY, MAIN_OUTERWEAR, MAIN_SHOES),
        ]
    return [
        (MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES),
        (MAIN_ALL_BODY, MAIN_SHOES),
        (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
        (MAIN_ALL_BODY, MAIN_OUTERWEAR, MAIN_SHOES),
    ]


def _pool_by_main(items: list[WardrobeItem]) -> dict[str, list[WardrobeItem]]:
    pools: dict[str, list[WardrobeItem]] = {}
    for item in items:
        pools.setdefault(_main(item), []).append(item)
    return pools


def _heuristic_score(items: tuple[WardrobeItem, ...], ctx: RecommendContext) -> float:
    score = 0.50
    categories = {_main(item) for item in items}
    subcats = {_sub(item) for item in items}
    male_count = len(subcats & MALE_SUBCATS)
    female_count = len(subcats & FEMALE_SUBCATS)

    if {MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES}.issubset(categories):
        score += 0.08

    has_outerwear = bool(subcats & OUTERWEAR_SUBCATS)
    if has_outerwear and ctx.weather in {"cold", "rainy"}:
        score += 0.18
    if has_outerwear and ctx.weather == "hot":
        score -= 0.25
    if has_outerwear and ctx.weather == "mild":
        if subcats & WARM_TOP_SUBCATS:
            score -= 0.22
        elif subcats & LIGHT_LAYERABLE_TOP_SUBCATS:
            score -= 0.04
        else:
            score -= 0.10

    for item in items:
        main = _main(item)
        sub = _sub(item)
        if sub in WEATHER_MAP.get(ctx.weather, {}).get(main, []):
            score += 0.06
        if sub in EVENT_MAP.get(ctx.event, {}).get(main, []):
            score += 0.08
        if sub in MOOD_MAP.get(ctx.mood, {}).get(main, []):
            score += 0.04

    if ctx.weather in {"cold", "rainy"} and subcats & SHORT_SUBCATS:
        score -= 0.28
    if ctx.weather == "rainy" and subcats & OPEN_SHOE_SUBCATS:
        score -= 0.30
    if ctx.weather == "rainy" and subcats & RAIN_SAFE_SHOE_SUBCATS:
        score += 0.08

    if ctx.event in {"formal", "smart-casual"}:
        if subcats & CASUAL_SPORT_SUBCATS:
            score -= 0.30
        if subcats & SNEAKER_SUBCATS and ctx.event == "formal":
            score -= 0.16
        if ctx.weather in {"cold", "rainy"} and subcats & BOOT_SUBCATS:
            score += 0.07
        if subcats & FORMAL_SHOE_SUBCATS:
            score += 0.08
        if (subcats & FORMAL_SHIRT_SUBCATS) and (subcats & FORMAL_LAYER_SUBCATS):
            score += 0.10
        if "male t-shirt" in subcats and (subcats & FORMAL_LAYER_SUBCATS):
            score -= 0.12

    if ctx.event == "sport":
        if subcats & FORMAL_SUBCATS:
            score -= 0.30
        if subcats & SPORT_SUBCATS:
            score += 0.08

    if ctx.gender == "male":
        score += 0.05 * male_count
        score -= 0.22 * female_count
    elif ctx.gender == "female":
        score += 0.04 * female_count
        score -= 0.22 * male_count
    elif male_count and female_count:
        score -= 0.26 * min(male_count, female_count)

    return max(0.05, min(score, 0.99))


def _combined_score(
    items: tuple[WardrobeItem, ...],
    ctx: RecommendContext,
    model_scorer: Callable[[tuple[WardrobeItem, ...]], float | None] | None,
) -> float:
    heuristic = _heuristic_score(items, ctx)
    if model_scorer is None:
        return heuristic

    model_score = model_scorer(items)
    if model_score is None:
        return heuristic

    return 0.65 * model_score + 0.35 * heuristic


def generate_recommendations(
    *,
    wardrobe_items: list[WardrobeItem],
    ctx: RecommendContext,
    anchor_item_id: str | None = None,
    top_k: int = 1,
    max_candidates: int = 5000,
    model_scorer: Callable[[tuple[WardrobeItem, ...]], float | None] | None = None,
) -> list[dict[str, Any]]:
    all_pools = _pool_by_main(wardrobe_items)
    pools = {
        cat: _gender_pool(_context_pool(items, cat, ctx), ctx.gender)
        for cat, items in all_pools.items()
    }

    candidates: list[tuple[float | None, float, tuple[WardrobeItem, ...]]] = []
    seen: set[tuple[str, ...]] = set()

    for template in _outfit_templates(ctx):
        choices: list[list[WardrobeItem]] = []
        valid = True

        for cat in template:
            cat_pool = pools.get(cat, [])
            if anchor_item_id is not None:
                anchor_pool = [item for item in cat_pool if item.id == anchor_item_id]
                if anchor_pool:
                    choices.append(anchor_pool)
                    continue
            if cat_pool:
                choices.append(cat_pool)
            else:
                valid = False
                break

        if not valid:
            continue

        for combo in itertools.product(*choices):
            ids = [item.id for item in combo]
            if len(ids) != len(set(ids)):
                continue
            if anchor_item_id is not None and anchor_item_id not in ids:
                continue

            key = tuple(sorted(ids))
            if key in seen:
                continue
            seen.add(key)

            outfit = tuple(combo)
            model_score = model_scorer(outfit) if model_scorer is not None else None
            candidates.append((model_score, _heuristic_score(outfit, ctx), outfit))
            if len(seen) >= max_candidates:
                break

        if len(seen) >= max_candidates:
            break

    model_values = [score for score, _, _ in candidates if score is not None]
    if len(model_values) >= 2:
        model_min = min(model_values)
        model_max = max(model_values)
        model_range = model_max - model_min
    else:
        model_min = 0.0
        model_range = 0.0

    scored: list[tuple[float, tuple[WardrobeItem, ...]]] = []
    for model_score, heuristic, outfit in candidates:
        if model_score is None or model_range < 0.05:
            combined = heuristic
        else:
            normalized_model = (model_score - model_min) / model_range
            combined = 0.50 * normalized_model + 0.50 * heuristic
        scored.append((combined, outfit))

    scored.sort(key=lambda row: row[0], reverse=True)
    return [
        {
            "rank": rank,
            "items": [
                {
                    "id": item.id,
                    "main_category": item.main_category,
                    "sub_category": item.sub_category,
                    "image_path": item.image_path,
                }
                for item in combo
            ],
        }
        for rank, (_, combo) in enumerate(scored[:top_k], start=1)
    ]
