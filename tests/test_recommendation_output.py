from __future__ import annotations

import unittest

from backend.smartwardrobe_backend.recommendation import (
    RecommendContext,
    generate_recommendations,
    _heuristic_score,
)
from backend.smartwardrobe_backend.storage import WardrobeItem


def item(item_id: str, main: str, sub: str, *, favorite: bool = False) -> WardrobeItem:
    return WardrobeItem(
        id=item_id,
        image_path=f"/tmp/{item_id}.jpg",
        main_category=main,
        sub_category=sub,
        manual_override=False,
        bbox_json=None,
        embedding_json=None,
        model_confidence=None,
        favorite=favorite,
        times_worn=0,
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
    )


class RecommendationOutputTest(unittest.TestCase):
    def test_no_preference_does_not_penalize_mixed_gender_items(self) -> None:
        outfit = (
            item("top-1", "tops", "male shirt"),
            item("bottom-1", "bottoms", "skirt"),
            item("shoe-1", "shoes", "male sneakers"),
        )
        base = RecommendContext(
            weather="mild",
            event="casual",
            mood="relaxed",
            gender="no preference",
            outerwear_required=False,
        )
        self.assertGreater(_heuristic_score(outfit, base), 0.7)

    def test_recommendations_return_single_outfit_with_score_by_default(self) -> None:
        wardrobe = [
            item("top-1", "tops", "male shirt"),
            item("top-2", "tops", "male t-shirt"),
            item("top-3", "tops", "male polos"),
            item("bottom-1", "bottoms", "male pants"),
            item("bottom-2", "bottoms", "male jeans"),
            item("shoe-1", "shoes", "male formal shoes"),
            item("shoe-2", "shoes", "male sneakers"),
            item("shoe-3", "shoes", "flats"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="casual",
            mood="relaxed",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(
            wardrobe_items=wardrobe,
            ctx=ctx,
        )

        self.assertEqual(len(outfits), 1)
        self.assertTrue(all("score" in outfit for outfit in outfits))
        self.assertTrue(all(0.0 <= outfit["score"] <= 1.0 for outfit in outfits))

    def test_formal_professional_rejects_tshirt_and_sneakers(self) -> None:
        wardrobe = [
            item("top-casual", "tops", "male t-shirt"),
            item("top-formal", "tops", "male shirt"),
            item("outer-1", "outerwear", "blazer"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-casual", "shoes", "sneakers"),
            item("shoe-formal", "shoes", "male formal shoes"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="professional",
            gender="no preference",
            outerwear_required=False,
        )

        def model_scorer(outfit):
            subcats = {row.sub_category for row in outfit}
            return 1.0 if "coat" in subcats else 0.1

        outfits = generate_recommendations(
            wardrobe_items=wardrobe,
            ctx=ctx,
            model_scorer=model_scorer,
        )

        self.assertEqual(len(outfits), 1)
        subcats = {row["sub_category"] for row in outfits[0]["items"]}
        self.assertIn("male shirt", subcats)
        self.assertIn("male formal shoes", subcats)
        self.assertNotIn("male t-shirt", subcats)
        self.assertNotIn("sneakers", subcats)

    def test_formal_professional_returns_empty_without_formal_shoes(self) -> None:
        wardrobe = [
            item("top-formal", "tops", "male shirt"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-casual", "shoes", "sneakers"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="professional",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(outfits, [])

    def test_formal_event_can_prefer_flat_sandals(self) -> None:
        wardrobe = [
            item("top-formal", "tops", "blouse"),
            item("outer-1", "outerwear", "blazer"),
            item("bottom-1", "bottoms", "skirt"),
            item("shoe-flat-sandal", "shoes", "flat sandals"),
            item("shoe-formal", "shoes", "closed shoes"),
            item("shoe-casual", "shoes", "sneakers"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="calm",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        subcats = {row["sub_category"] for row in outfits[0]["items"]}
        self.assertIn("flat sandals", subcats)
        self.assertNotIn("sneakers", subcats)

    def test_professional_mood_can_prefer_flat_sandals(self) -> None:
        wardrobe = [
            item("top-formal", "tops", "blouse"),
            item("outer-1", "outerwear", "blazer"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-flat-sandal", "shoes", "flat sandals"),
            item("shoe-formal", "shoes", "closed shoes"),
            item("shoe-casual", "shoes", "sneakers"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="smart-casual",
            mood="professional",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        subcats = {row["sub_category"] for row in outfits[0]["items"]}
        self.assertIn("flat sandals", subcats)
        self.assertNotIn("sneakers", subcats)

    def test_formal_professional_outerwear_prefers_blazer_layer(self) -> None:
        wardrobe = [
            item("top-formal", "tops", "blouse"),
            item("outer-blazer", "outerwear", "blazer"),
            item("outer-coat", "outerwear", "coat"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-formal", "shoes", "closed shoes"),
        ]
        ctx = RecommendContext(
            weather="cold",
            event="formal",
            mood="professional",
            gender="no preference",
            outerwear_required=True,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        subcats = {row["sub_category"] for row in outfits[0]["items"]}
        self.assertIn("blazer", subcats)
        self.assertNotIn("coat", subcats)

    def test_required_outerwear_respects_rainy_context(self) -> None:
        wardrobe = [
            item("top-1", "tops", "sweater"),
            item("outer-rain", "outerwear", "trench coat"),
            item("outer-casual", "outerwear", "jacket"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-1", "shoes", "boots"),
        ]
        ctx = RecommendContext(
            weather="rainy",
            event="casual",
            mood="relaxed",
            gender="no preference",
            outerwear_required=True,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        subcats = {row["sub_category"] for row in outfits[0]["items"]}
        self.assertIn("trench coat", subcats)
        self.assertNotIn("jacket", subcats)

    def test_favorite_item_is_prioritized_within_valid_context(self) -> None:
        wardrobe = [
            item("top-fav", "tops", "tshirt", favorite=True),
            item("top-other", "tops", "male t-shirt"),
            item("bottom-1", "bottoms", "jeans"),
            item("shoe-1", "shoes", "sneakers"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="casual",
            mood="relaxed",
            gender="no preference",
            outerwear_required=False,
        )

        def model_scorer(outfit):
            subcats = {row.sub_category for row in outfit}
            return 1.0 if "male t-shirt" in subcats else 0.1

        outfits = generate_recommendations(
            wardrobe_items=wardrobe,
            ctx=ctx,
            model_scorer=model_scorer,
        )

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("top-fav", ids)
        self.assertNotIn("top-other", ids)

    def test_favorite_item_cannot_override_weather_mood_or_event(self) -> None:
        wardrobe = [
            item("top-bad-fav", "tops", "male t-shirt", favorite=True),
            item("top-formal", "tops", "male shirt"),
            item("outer-1", "outerwear", "blazer"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-1", "shoes", "closed shoes"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="professional",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("top-formal", ids)
        self.assertNotIn("top-bad-fav", ids)

    def test_hot_weather_rejects_warm_tops_even_when_favorite(self) -> None:
        wardrobe = [
            item("top-bad-fav", "tops", "hoodie", favorite=True),
            item("top-hot", "tops", "tank top"),
            item("bottom-1", "bottoms", "shorts"),
            item("shoe-1", "shoes", "flat sandals"),
        ]
        ctx = RecommendContext(
            weather="hot",
            event="casual",
            mood="energetic",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("top-hot", ids)
        self.assertNotIn("top-bad-fav", ids)

    def test_hot_weather_rejects_long_sleeve_formal_tops(self) -> None:
        wardrobe = [
            item("top-bad-fav", "tops", "long-sleeve shirt", favorite=True),
            item("top-hot", "tops", "blouse"),
            item("bottom-1", "bottoms", "skirt"),
            item("shoe-1", "shoes", "flat sandals"),
        ]
        ctx = RecommendContext(
            weather="hot",
            event="formal",
            mood="calm",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("top-hot", ids)
        self.assertNotIn("top-bad-fav", ids)

    def test_cold_weather_rejects_tshirt_even_when_favorite(self) -> None:
        wardrobe = [
            item("top-bad-fav", "tops", "male t-shirt", favorite=True),
            item("top-cold", "tops", "sweater"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-1", "shoes", "boots"),
        ]
        ctx = RecommendContext(
            weather="cold",
            event="casual",
            mood="relaxed",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("top-cold", ids)
        self.assertNotIn("top-bad-fav", ids)

    def test_rainy_weather_rejects_tshirt_and_prefers_boots(self) -> None:
        wardrobe = [
            item("top-bad-fav", "tops", "male t-shirt", favorite=True),
            item("top-rain", "tops", "sweater"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-bad-fav", "shoes", "sneakers", favorite=True),
            item("shoe-rain", "shoes", "boots"),
        ]
        ctx = RecommendContext(
            weather="rainy",
            event="casual",
            mood="relaxed",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("top-rain", ids)
        self.assertIn("shoe-rain", ids)
        self.assertNotIn("top-bad-fav", ids)
        self.assertNotIn("shoe-bad-fav", ids)

    def test_cold_weather_rejects_shorts_even_when_favorite(self) -> None:
        wardrobe = [
            item("top-1", "tops", "sweater"),
            item("bottom-bad-fav", "bottoms", "shorts", favorite=True),
            item("bottom-cold", "bottoms", "pants"),
            item("shoe-1", "shoes", "boots"),
        ]
        ctx = RecommendContext(
            weather="cold",
            event="casual",
            mood="relaxed",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("bottom-cold", ids)
        self.assertNotIn("bottom-bad-fav", ids)

    def test_cold_weather_rejects_open_shoes_even_when_favorite(self) -> None:
        wardrobe = [
            item("top-1", "tops", "sweater"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-bad-fav", "shoes", "flip-flops", favorite=True),
            item("shoe-cold", "shoes", "boots"),
        ]
        ctx = RecommendContext(
            weather="cold",
            event="casual",
            mood="relaxed",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("shoe-cold", ids)
        self.assertNotIn("shoe-bad-fav", ids)

    def test_casual_event_rejects_dressy_shoes_even_when_favorite(self) -> None:
        wardrobe = [
            item("top-1", "tops", "male t-shirt"),
            item("bottom-1", "bottoms", "jeans"),
            item("shoe-bad-fav", "shoes", "male loafers", favorite=True),
            item("shoe-casual", "shoes", "sneakers"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="casual",
            mood="energetic",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("shoe-casual", ids)
        self.assertNotIn("shoe-bad-fav", ids)

    def test_sport_event_rejects_formal_items_and_requires_sport_shoes(self) -> None:
        wardrobe = [
            item("top-bad-fav", "tops", "blouse", favorite=True),
            item("top-sport", "tops", "male sports shirt"),
            item("bottom-1", "bottoms", "track pants"),
            item("shoe-bad-fav", "shoes", "male formal shoes", favorite=True),
            item("shoe-sport", "shoes", "sneakers"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="sport",
            mood="energetic",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("top-sport", ids)
        self.assertIn("shoe-sport", ids)
        self.assertNotIn("top-bad-fav", ids)
        self.assertNotIn("shoe-bad-fav", ids)

    def test_gender_selection_does_not_fall_back_to_opposite_gender_items(self) -> None:
        wardrobe = [
            item("top-bad-fav", "tops", "blouse", favorite=True),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-1", "shoes", "sneakers"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="casual",
            mood="energetic",
            gender="male",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(outfits, [])

    def test_male_formal_can_use_generic_shirt_and_blazer(self) -> None:
        wardrobe = [
            item("top-1", "tops", "shirt"),
            item("outer-1", "outerwear", "blazer"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-1", "shoes", "closed shoes"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="professional",
            gender="male",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        subcats = {row["sub_category"] for row in outfits[0]["items"]}
        self.assertIn("shirt", subcats)
        self.assertIn("blazer", subcats)

    def test_male_gender_keeps_formal_constraints_and_unisex_items(self) -> None:
        wardrobe = [
            item("top-1", "tops", "male shirt"),
            item("outer-bad", "outerwear", "male jacket", favorite=True),
            item("outer-good", "outerwear", "blazer"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-bad", "shoes", "male sneakers", favorite=True),
            item("shoe-good", "shoes", "closed shoes"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="professional",
            gender="male",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("outer-good", ids)
        self.assertIn("shoe-good", ids)
        self.assertNotIn("outer-bad", ids)
        self.assertNotIn("shoe-bad", ids)

    def test_male_formal_can_use_blazer_and_flat_sandals_without_sneakers(self) -> None:
        wardrobe = [
            item("top-1", "tops", "male shirt"),
            item("outer-bad", "outerwear", "male jacket", favorite=True),
            item("outer-good", "outerwear", "blazer"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-bad", "shoes", "male sneakers", favorite=True),
            item("shoe-good", "shoes", "flat sandals"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="professional",
            gender="male",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("outer-good", ids)
        self.assertIn("shoe-good", ids)
        self.assertNotIn("outer-bad", ids)
        self.assertNotIn("shoe-bad", ids)

    def test_blazer_and_flat_sandals_are_unisex_for_male_scoring(self) -> None:
        outfit = (
            item("top-1", "tops", "male shirt"),
            item("outer-1", "outerwear", "blazer"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-1", "shoes", "flat sandals"),
        )
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="professional",
            gender="male",
            outerwear_required=False,
        )

        self.assertGreater(_heuristic_score(outfit, ctx), 0.90)

    def test_professional_mood_rejects_sneakers_even_when_favorite(self) -> None:
        wardrobe = [
            item("top-1", "tops", "blouse"),
            item("outer-1", "outerwear", "blazer"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-bad-fav", "shoes", "sneakers", favorite=True),
            item("shoe-good", "shoes", "closed shoes"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="smart-casual",
            mood="professional",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("shoe-good", ids)
        self.assertNotIn("shoe-bad-fav", ids)

    def test_hot_weather_outerwear_required_falls_back_to_available_items(self) -> None:
        wardrobe = [
            item("top-1", "tops", "tank top"),
            item("outer-bad-fav", "outerwear", "jacket", favorite=True),
            item("bottom-1", "bottoms", "shorts"),
            item("shoe-1", "shoes", "flat sandals"),
        ]
        ctx = RecommendContext(
            weather="hot",
            event="casual",
            mood="energetic",
            gender="no preference",
            outerwear_required=True,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(len(outfits), 1)
        ids = {row["id"] for row in outfits[0]["items"]}
        self.assertIn("outer-bad-fav", ids)

    def test_unknown_subcategory_does_not_bypass_formal_constraints(self) -> None:
        wardrobe = [
            item("top-unknown", "tops", "unknown", favorite=True),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-1", "shoes", "closed shoes"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="professional",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(outfits, [])

    def test_unknown_shoe_does_not_bypass_rainy_constraints(self) -> None:
        wardrobe = [
            item("top-1", "tops", "sweater"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-unknown", "shoes", "unknown", favorite=True),
        ]
        ctx = RecommendContext(
            weather="rainy",
            event="casual",
            mood="relaxed",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(outfits, [])

    def test_constraints_return_empty_instead_of_relaxed_fallback(self) -> None:
        wardrobe = [
            item("top-bad", "tops", "male t-shirt"),
            item("bottom-1", "bottoms", "pants"),
            item("shoe-1", "shoes", "closed shoes"),
        ]
        ctx = RecommendContext(
            weather="mild",
            event="formal",
            mood="professional",
            gender="no preference",
            outerwear_required=False,
        )

        outfits = generate_recommendations(wardrobe_items=wardrobe, ctx=ctx)

        self.assertEqual(outfits, [])


if __name__ == "__main__":
    unittest.main()
