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

VALID_WEATHERS = ("hot", "mild", "cold", "rainy")
VALID_EVENTS = ("casual", "smart-casual", "formal", "sport")
VALID_MOODS = ("energetic", "professional", "relaxed", "calm")


WEATHER_MAP = {
    "hot": {
        "tops": ["tank", "tank top", "sleeveless top", "tshirt", "male t-shirt", "top", "blouse", "male polos"],
        "bottoms": ["shorts", "male knee-length shorts", "skirt", "tennis skirt", "male swim shorts"],
        # Casual open shoes first; flat sandals last (more formal-looking)
        "shoes": ["flip-flops", "male flip-flops", "flats", "sandals", "flat sandals"],
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
        # shirt/male shirt removed — button-down shirts are smart-casual, not casual
        "tops": ["tshirt", "male t-shirt", "male polos", "hoodie", "sweatshirt", "top", "tank top"],
        "bottoms": ["jeans", "male jeans", "shorts", "male knee-length shorts", "sweatpants", "male sweatpants"],
        # Sneakers first; no flat sandals in casual event pool
        "shoes": ["sneakers", "male sneakers", "flats", "flip-flops", "male flip-flops"],
        "all-body": ["dress", "romper", "jumpsuit"],
        "outerwear": ["jacket", "male jacket", "cardigan", "track jacket", "male track jacket"],
    },
    "smart-casual": {
        "tops": ["blouse", "shirt", "male shirt", "long-sleeve shirt", "male polos", "male t-shirt", "sweater"],
        "bottoms": ["pants", "male pants", "skirt", "long skirt", "jeans", "male jeans", "male suit pants"],
        # Sneakers and flats first; flat sandals only as fallback (warm weather)
        "shoes": ["sneakers", "male sneakers", "flats", "closed shoes", "male loafers", "flat sandals"],
        "all-body": ["dress", "set/suit", "jumpsuit", "male suit"],
        "outerwear": ["blazer", "jacket", "cardigan", "male formal jacket", "male suit jacket", "male jacket"],
    },
    "formal": {
        "tops": ["blouse", "shirt", "male shirt", "long-sleeve shirt", "turtleneck sweater"],
        "bottoms": ["pants", "male suit pants", "skirt", "long skirt"],
        # Heels/pump first; flat sandals as fallback
        "shoes": ["heels", "pump", "closed shoes", "male formal shoes", "male loafers", "flat sandals"],
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
    "energetic": {
        "tops": ["tshirt", "male t-shirt", "blouse", "tank top", "top", "male polos"],
        "bottoms": ["skirt", "shorts", "male knee-length shorts", "jeans", "male jeans"],
        # Sneakers first; flat sandals only for hot weather fallback
        "shoes": ["sneakers", "male sneakers", "flats", "flip-flops", "male flip-flops"],
        "all-body": ["dress", "romper"],
        "outerwear": ["cardigan", "jacket", "male jacket"],
    },
    "professional": {
        "tops": ["blouse", "shirt", "male shirt", "long-sleeve shirt"],
        "bottoms": ["pants", "male pants", "male suit pants", "skirt"],
        # Heels/pump first for professional; flat sandals as last resort
        "shoes": ["heels", "pump", "closed shoes", "male formal shoes", "male loafers", "flat sandals"],
        "all-body": ["dress", "set/suit", "male suit"],
        "outerwear": ["blazer", "male formal jacket", "male suit jacket"],
    },
    "relaxed": {
        "tops": ["sweater", "male sweater", "tshirt", "male t-shirt", "hoodie", "sweatshirt"],
        "bottoms": ["sweatpants", "male sweatpants", "jeans", "male jeans", "shorts"],
        # No flat sandals for relaxed mood
        "shoes": ["sneakers", "male sneakers", "flats", "flip-flops", "male flip-flops"],
        "all-body": ["jumpsuit", "romper"],
        "outerwear": ["cardigan", "jacket", "male jacket"],
    },
    "calm": {
        "tops": ["sweater", "male sweater", "shirt", "male shirt", "blouse", "top", "male polos"],
        "bottoms": ["pants", "male pants", "jeans", "male jeans", "long skirt"],
        "shoes": ["flats", "sneakers", "male sneakers", "closed shoes", "male loafers", "male shoes"],
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
    "blouse", "bodie", "coverup", "dress", "gown", "heeled boots", "heels",
    "kimono", "long skirt", "one-piece swimsuit", "over-the-knee boots", "platform shoes",
    "pump", "pyjama/slip/chemise", "romper", "skirt", "sports bra", "swimsuit",
    "swimsuit bottom", "swimsuit top", "tank", "tank top", "tennis skirt", "tunic",
}
UNISEX_SUBCATS = {
    "blazer", "boots", "cardigan", "closed shoes", "coat", "flat boots", "flat sandals",
    "flats", "flip-flops", "hoodie", "jacket", "jacket/coat", "jeans", "jumpsuit",
    "long-sleeve shirt", "pants", "set/suit", "shirt", "shorts", "sneakers",
    "sweater", "sweathirt", "sweatpants", "top", "track jacket", "trench coat", "vest",
}
SHORT_SUBCATS = {"shorts", "male knee-length shorts", "sports shorts", "male sports shorts", "male swim shorts"}
OPEN_SHOE_SUBCATS = {"flat sandals", "sandals", "flip-flops", "male flip-flops", "slippers", "male slippers"}
RAIN_SAFE_SHOE_SUBCATS = {"boots", "flat boots", "heeled boots", "closed shoes", "male formal shoes"}
FORMAL_SHOE_SUBCATS = {
    "heels", "pump", "closed shoes", "male formal shoes", "male loafers", "flat sandals",
}
# Shoes that look out of place in casual / relaxed / sport contexts
DRESSY_SHOE_SUBCATS = {"heels", "pump", "male formal shoes", "male loafers", "closed shoes"}
CASUAL_BLOCKED_SHOE_SUBCATS = {"heels", "pump", "male formal shoes", "male loafers"}
FLAT_SANDAL_SUBCATS = {"flat sandals"}
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
RAIN_OUTERWEAR_PRIORITY = ("trench coat", "coat", "jacket/coat", "parka", "jacket", "male jacket")
# Outerwear is inappropriate in hot weather. If the user explicitly requires
# outerwear on hot days, return no outfit instead of forcing a bad layer.
HOT_BLOCKED_OUTERWEAR_SUBCATS = {
    "blazer", "cardigan", "coat", "jacket", "jacket/coat", "kimono",
    "male formal jacket", "male jacket", "male suit jacket", "male track jacket",
    "male vest", "parka", "track jacket", "trench coat", "vest",
}
# Warm tops are inappropriate in hot weather regardless of event/mood/favorite.
HOT_BLOCKED_TOP_SUBCATS = {
    "hoodie", "sweatshirt", "sweathirt", "sweater", "male sweater",
    "sports long-sleeve shirt", "long-sleeve shirt", "turtleneck sweater",
}
# Light-layer tops / sleeveless items that are wrong for cold/rainy weather.
COLD_BLOCKED_TOP_SUBCATS = {
    "tshirt", "male t-shirt", "tank", "tank top", "sleeveless top",
    "sports bra", "swimsuit top",
}
RAIN_BLOCKED_SHOE_SUBCATS = {
    "sneakers", "male sneakers", "flat sandals", "sandals", "flats",
    "flip-flops", "male flip-flops", "slippers", "male slippers",
}
FORMAL_BLOCKED_SUBCATS = {
    "tshirt", "male t-shirt", "tank", "tank top", "sleeveless top",
    "hoodie", "sweatshirt", "sweathirt", "sweatpants", "male sweatpants",
    "track pants", "male track pants", "track jacket", "male track jacket",
    "sports bra", "sports long-sleeve shirt", "male sports shirt",
    "sports shorts", "male sports shorts", "shorts", "male knee-length shorts",
    "male swim shorts", "sandals", "flip-flops", "male flip-flops", "sneakers", "male sneakers",
}
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


def _dedupe_items(items: list[WardrobeItem]) -> list[WardrobeItem]:
    seen: set[str] = set()
    unique: list[WardrobeItem] = []
    for item in items:
        if item.id in seen:
            continue
        seen.add(item.id)
        unique.append(item)
    return unique


def _context_pool(items: list[WardrobeItem], main_cat: str, ctx: RecommendContext) -> list[WardrobeItem]:
    weather_set = set(WEATHER_MAP.get(ctx.weather, {}).get(main_cat, []))
    event_set = set(EVENT_MAP.get(ctx.event, {}).get(main_cat, []))
    mood_set = set(MOOD_MAP.get(ctx.mood, {}).get(main_cat, []))

    strict = [item for item in items if _sub(item) in weather_set and _sub(item) in event_set]
    weather_only = [item for item in items if _sub(item) in weather_set]
    event_only = [item for item in items if _sub(item) in event_set]
    mood_only = [item for item in items if _sub(item) in mood_set]

    # Items whose subcat is "unknown" are kept as an absolute last resort.
    # Known-but-wrong items (coat in hot, shorts in cold, hoodie in formal)
    # must NEVER enter the pool — the template will simply fail for this
    # category and we try the next template or return nothing.
    unknown_only = [item for item in items if _sub(item) == "unknown"]

    if main_cat == MAIN_OUTERWEAR and ctx.outerwear_required:
        if ctx.weather == "rainy":
            base = _dedupe_items(weather_only + strict + event_only + mood_only) or unknown_only
        elif ctx.event == "formal" or ctx.mood == "professional":
            base = _dedupe_items(event_only + mood_only + strict + weather_only) or unknown_only
        else:
            base = _dedupe_items(strict + weather_only + event_only + mood_only) or unknown_only
    elif ctx.event == "formal" or ctx.mood == "professional":
        # Formal/professional: event pool first, then mood, then weather
        base = _dedupe_items(event_only + mood_only + strict + weather_only) or unknown_only
    elif ctx.event in {"sport", "casual", "smart-casual"}:
        # For these events the event definition is strict enough:
        # event_only comes first so sneakers beat flat sandals from weather pool
        base = _dedupe_items(event_only + strict + mood_only + weather_only) or unknown_only
    else:
        base = _dedupe_items(strict + event_only + mood_only + weather_only) or unknown_only
    # Keep unknown-subcat items in the pool but push them to the end so
    # context-appropriate items are always tried first.
    known_in_base = [item for item in base if _sub(item) != "unknown"]
    unknown_in_base = [item for item in base if _sub(item) == "unknown"]
    base = known_in_base + unknown_in_base

    mood_first = [item for item in base if _sub(item) in mood_set]
    rest = [item for item in base if _sub(item) not in mood_set]
    ordered = mood_first + rest if mood_first else base

    # For formal/professional shoes, allow flat sandals to win in warm/mild
    # weather while keeping sneakers and flip-flops blocked.
    if main_cat == MAIN_SHOES and (ctx.event == "formal" or ctx.mood == "professional"):
        dressy = [item for item in ordered if _sub(item) in FORMAL_SHOE_SUBCATS and _sub(item) not in FLAT_SANDAL_SUBCATS]
        sandals = [item for item in ordered if _sub(item) in FLAT_SANDAL_SUBCATS]
        rest_shoes = [item for item in ordered if _sub(item) not in FORMAL_SHOE_SUBCATS and _sub(item) not in FLAT_SANDAL_SUBCATS]
        if sandals and ctx.weather in {"hot", "mild"}:
            return sandals + dressy + rest_shoes
        if dressy or sandals:
            return dressy + sandals + rest_shoes
    if main_cat == MAIN_OUTERWEAR and ctx.outerwear_required:
        if ctx.weather == "rainy":
            priority = {sub: index for index, sub in enumerate(RAIN_OUTERWEAR_PRIORITY)}
            return sorted(ordered, key=lambda item: priority.get(_sub(item), len(priority)))
        if ctx.event == "formal" or ctx.mood == "professional":
            formal_layers = [item for item in ordered if _sub(item) in FORMAL_LAYER_SUBCATS]
            if formal_layers:
                return formal_layers + [item for item in ordered if _sub(item) not in FORMAL_LAYER_SUBCATS]
    return ordered


def _gender_pool(items: list[WardrobeItem], gender: str) -> list[WardrobeItem]:
    if gender == "no preference":
        return items
    if gender == "male":
        return [item for item in items if _sub(item) in MALE_SUBCATS or _sub(item) in UNISEX_SUBCATS]
    if gender == "female":
        preferred = [item for item in items if _sub(item) in FEMALE_SUBCATS or _sub(item) in UNISEX_SUBCATS]
        if preferred:
            return preferred
        non_male = [item for item in items if _sub(item) not in MALE_SUBCATS]
        return non_male
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
        strict_formal = ctx.event == "formal" or ctx.mood == "professional"
        if hot:
            # Hot weather: no blazer — even formal outfits skip the jacket.
            return [(MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES), (MAIN_ALL_BODY, MAIN_SHOES)]
        if strict_formal:
            # Blazer-inclusive templates first so the compatibility check that
            # requires a formal layer finds valid candidates quickly.
            if cold:
                return [
                    (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
                    (MAIN_ALL_BODY, MAIN_OUTERWEAR, MAIN_SHOES),
                    (MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES),
                    (MAIN_ALL_BODY, MAIN_SHOES),
                ]
            return [
                (MAIN_TOPS, MAIN_OUTERWEAR, MAIN_BOTTOMS, MAIN_SHOES),
                (MAIN_ALL_BODY, MAIN_OUTERWEAR, MAIN_SHOES),
                (MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES),
                (MAIN_ALL_BODY, MAIN_SHOES),
            ]
        # Smart-casual without professional mood: original order.
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


_CASUAL_BOTTOMS = {
    "jeans", "male jeans", "shorts", "male knee-length shorts",
    "sweatpants", "male sweatpants", "track pants", "male track pants",
    "sports shorts", "male sports shorts", "male swim shorts",
}
_FORMAL_BOTTOMS = {"pants", "male pants", "male suit pants", "skirt", "long skirt"}


def _is_context_compatible(items: tuple[WardrobeItem, ...], ctx: RecommendContext) -> bool:
    subcats = {_sub(item) for item in items}
    main_to_sub = {_main(item): _sub(item) for item in items}

    if "unknown" in subcats:
        return False

    if ctx.weather == "hot":
        top = main_to_sub.get(MAIN_TOPS)
        if top is not None and top in HOT_BLOCKED_TOP_SUBCATS:
            return False
        outerwear = main_to_sub.get(MAIN_OUTERWEAR)
        if outerwear is not None and outerwear in HOT_BLOCKED_OUTERWEAR_SUBCATS:
            return False
    if ctx.weather in {"cold", "rainy"}:
        top = main_to_sub.get(MAIN_TOPS)
        if top is not None and top in COLD_BLOCKED_TOP_SUBCATS:
            return False
        bottom = main_to_sub.get(MAIN_BOTTOMS)
        if bottom is not None and bottom in SHORT_SUBCATS:
            return False
    if ctx.weather == "cold":
        shoe = main_to_sub.get(MAIN_SHOES)
        if shoe is not None and shoe in OPEN_SHOE_SUBCATS:
            return False
    if ctx.weather == "rainy":
        shoe = main_to_sub.get(MAIN_SHOES)
        if shoe is not None and shoe in RAIN_BLOCKED_SHOE_SUBCATS:
            return False

    if ctx.event == "sport":
        top = main_to_sub.get(MAIN_TOPS)
        if top is not None and top not in EVENT_MAP["sport"][MAIN_TOPS]:
            return False
        bottom = main_to_sub.get(MAIN_BOTTOMS)
        if bottom is not None and bottom not in EVENT_MAP["sport"][MAIN_BOTTOMS]:
            return False
        shoe = main_to_sub.get(MAIN_SHOES)
        if shoe is not None and shoe not in EVENT_MAP["sport"][MAIN_SHOES]:
            return False
        outerwear = main_to_sub.get(MAIN_OUTERWEAR)
        if outerwear is not None and outerwear not in EVENT_MAP["sport"][MAIN_OUTERWEAR]:
            return False
    if ctx.event == "casual":
        shoe = main_to_sub.get(MAIN_SHOES)
        if shoe is not None and shoe in CASUAL_BLOCKED_SHOE_SUBCATS:
            return False

    strict_formal = ctx.event == "formal" or ctx.mood == "professional"
    if strict_formal:
        if ctx.event == "formal":
            # Formal EVENT: full block — sneakers, flip-flops, sportswear all out.
            if subcats & FORMAL_BLOCKED_SUBCATS:
                return False
            # Shoes must be dressy (heels, closed shoes, flat sandals, etc.).
            shoe = main_to_sub.get(MAIN_SHOES)
            if shoe is not None and shoe not in FORMAL_SHOE_SUBCATS:
                return False
            # Tops must come from the formal top list (shirt, blouse, not t-shirt).
            top = main_to_sub.get(MAIN_TOPS)
            if top is not None and top not in EVENT_MAP["formal"][MAIN_TOPS]:
                return False
        else:
            # Professional MOOD only (e.g. smart-casual + professional):
            # block obvious sportswear/extreme casual and sneakers.
            if subcats & FORMAL_BLOCKED_SUBCATS:
                return False

        # Casual bottoms (jeans, shorts, sweatpants) are inappropriate for both
        # formal events and a professional mood, regardless of the occasion.
        bottom = main_to_sub.get(MAIN_BOTTOMS)
        if bottom is not None and bottom in _CASUAL_BOTTOMS:
            return False

        # Formal / professional outfits with a separate top require a blazer or
        # suit jacket — except in hot weather where wearing a jacket is impractical.
        # All-body garments (dress, gown) are exempt: they are formal on their own.
        mains = {_main(item) for item in items}
        if MAIN_TOPS in mains and ctx.weather != "hot":
            if not (subcats & FORMAL_LAYER_SUBCATS):
                return False

    # Style coherence: blazer must not pair with casual bottoms in any context
    if subcats & FORMAL_LAYER_SUBCATS:
        bottom = main_to_sub.get(MAIN_BOTTOMS)
        if bottom is not None and bottom in _CASUAL_BOTTOMS:
            return False

    return True


def _heuristic_score(items: tuple[WardrobeItem, ...], ctx: RecommendContext) -> float:
    score = 0.50
    categories = {_main(item) for item in items}
    subcats = {_sub(item) for item in items}
    main_to_sub = {_main(item): _sub(item) for item in items}
    male_count = len(subcats & MALE_SUBCATS)
    female_count = len(subcats & FEMALE_SUBCATS)

    if {MAIN_TOPS, MAIN_BOTTOMS, MAIN_SHOES}.issubset(categories):
        score += 0.08

    has_outerwear = bool(subcats & OUTERWEAR_SUBCATS)
    if has_outerwear and ctx.weather in {"cold", "rainy"}:
        score += 0.18
    if ctx.weather == "rainy" and "trench coat" in subcats:
        score += 0.12
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
        if subcats & FLAT_SANDAL_SUBCATS and ctx.weather in {"hot", "mild"}:
            score += 0.06
        if (subcats & FORMAL_SHIRT_SUBCATS) and (subcats & FORMAL_LAYER_SUBCATS):
            score += 0.10
        if subcats & FORMAL_LAYER_SUBCATS and ctx.mood == "professional":
            score += 0.14
        if "male t-shirt" in subcats and (subcats & FORMAL_LAYER_SUBCATS):
            score -= 0.12

        # Style cohesion bonuses for formal/smart-casual
        # Dress + blazer = classic elegant combo
        if MAIN_ALL_BODY in categories and subcats & FORMAL_LAYER_SUBCATS:
            score += 0.10
        # Dress alone (no blazer) + formal shoes = elegant simplicity
        if MAIN_ALL_BODY in categories and MAIN_OUTERWEAR not in categories:
            if subcats & {"heels", "pump", "flat sandals", "closed shoes"}:
                score += 0.07
        # Formal skirt + formal top = classic femininity
        bottom = main_to_sub.get(MAIN_BOTTOMS)
        if bottom in {"skirt", "long skirt"}:
            if subcats & FORMAL_SHIRT_SUBCATS or subcats & FORMAL_LAYER_SUBCATS:
                score += 0.08
        # Dressy shoes (heels/pump) with a formal outfit
        if subcats & {"heels", "pump"}:
            if subcats & FORMAL_LAYER_SUBCATS or MAIN_ALL_BODY in categories:
                score += 0.08
        # Formal bottoms (pants/skirt) + blazer = power look
        if subcats & FORMAL_LAYER_SUBCATS and bottom in _FORMAL_BOTTOMS:
            score += 0.07

    if ctx.event == "sport":
        if subcats & FORMAL_SUBCATS:
            score -= 0.30
        if subcats & SPORT_SUBCATS:
            score += 0.08
        if subcats & SNEAKER_SUBCATS:
            score += 0.10
        if subcats & FLAT_SANDAL_SUBCATS:
            score -= 0.20
        if subcats & DRESSY_SHOE_SUBCATS:
            score -= 0.25

    # Penalize dressy/formal shoes in casual or relaxed contexts
    if ctx.event in {"casual", "sport"} or ctx.mood in {"relaxed", "energetic"}:
        if subcats & DRESSY_SHOE_SUBCATS:
            score -= 0.25
        # Flat sandals are out of place in casual/relaxed regardless of weather
        if subcats & FLAT_SANDAL_SUBCATS:
            score -= 0.18
        # Button-down shirts are smart-casual; penalize in casual/relaxed
        if {"shirt", "male shirt"} & subcats:
            score -= 0.14

    if ctx.gender == "male":
        score += 0.05 * male_count
        score -= 0.22 * female_count
    elif ctx.gender == "female":
        score += 0.04 * female_count
        score -= 0.22 * male_count
    elif ctx.gender != "no preference" and male_count and female_count:
        score -= 0.26 * min(male_count, female_count)

    # Bonus for favorite items — user explicitly marked these as preferred
    for item in items:
        if item.favorite:
            score += 0.18

    # Very slight penalty for frequently worn items — just enough to break ties
    # and gently rotate the wardrobe, not enough to hide good items.
    for item in items:
        if item.times_worn and item.times_worn > 0:
            wear_penalty = min(item.times_worn * 0.002, 0.015)
            score -= wear_penalty

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
    exclude_item_ids: set[str] | None = None,
    top_k: int = 1,
    max_candidates: int = 5000,
    model_scorer: Callable[[tuple[WardrobeItem, ...]], float | None] | None = None,
) -> list[dict[str, Any]]:
    excluded = exclude_item_ids or set()
    available_items = [item for item in wardrobe_items if item.id not in excluded]
    all_pools = _pool_by_main(available_items)

    pools: dict[str, list[WardrobeItem]] = {}
    for cat, cat_items in all_pools.items():
        pools[cat] = _gender_pool(_context_pool(cat_items, cat, ctx), ctx.gender)

    candidates: list[tuple[float | None, float, tuple[WardrobeItem, ...]]] = []
    seen: set[tuple[str, ...]] = set()

    def _minimally_compatible(outfit: tuple[WardrobeItem, ...]) -> bool:
        """Relaxed check used only in the fallback pass.

        We still block the most embarrassing mismatches (t-shirts in formal,
        sportswear in professional) but drop combination-level requirements
        (blazer mandatory, shoe type) so that a result can be returned.
        Blazer is not required here — the user may simply not own one.
        """
        _subcats = {_sub(item) for item in outfit}
        if "unknown" in _subcats:
            return False
        if ctx.event == "formal" or ctx.mood == "professional":
            # Never show sportswear or extreme casual in a formal context.
            if _subcats & FORMAL_BLOCKED_SUBCATS:
                return False
            if _subcats & {"male jacket", "jacket", "cardigan"}:
                return False
        return True

    # Two-pass candidate search:
    #   Pass 1 (strict=True):  only combinations that pass _is_context_compatible.
    #   Pass 2 (strict=False): fallback — uses _minimally_compatible so we always
    #     return something but still never show a t-shirt in a formal context.
    for strict in (True, False):
        if candidates:
            break  # Pass 1 succeeded — no need for the relaxed fallback.

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

                outfit = tuple(combo)
                if strict:
                    if not _is_context_compatible(outfit, ctx):
                        continue
                else:
                    if not _minimally_compatible(outfit):
                        continue

                seen.add(key)
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

    scored: list[tuple[float, int, tuple[WardrobeItem, ...]]] = []
    for model_score, heuristic, outfit in candidates:
        if model_score is None or model_range < 0.05:
            combined = heuristic
        else:
            normalized_model = (model_score - model_min) / model_range
            combined = 0.30 * normalized_model + 0.70 * heuristic
        favorite_count = sum(1 for item in outfit if item.favorite)
        scored.append((max(0.05, min(combined, 0.99)), favorite_count, outfit))

    scored.sort(key=lambda row: (row[1], row[0]), reverse=True)

    # Pick top_k outfits ensuring each uses different items where possible
    selected: list[tuple[float, tuple[WardrobeItem, ...]]] = []
    used_ids: set[str] = set()
    # First pass: prefer outfits with no item overlap
    for score, _, combo in scored:
        if len(selected) >= top_k:
            break
        combo_ids = {item.id for item in combo}
        if not combo_ids & used_ids:
            selected.append((score, combo))
            used_ids |= combo_ids
    # Second pass: fill remaining slots if not enough diverse outfits
    if len(selected) < top_k:
        for score, _, combo in scored:
            if len(selected) >= top_k:
                break
            if (score, combo) not in selected:
                selected.append((score, combo))

    return [
        {
            "rank": rank,
            "score": round(float(score), 4),
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
        for rank, (score, combo) in enumerate(selected[:top_k], start=1)
    ]
