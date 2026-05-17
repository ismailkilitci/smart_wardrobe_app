from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.smartwardrobe_backend import recommendation
from backend.smartwardrobe_backend.storage import init_db, insert_item, to_api_dict


class RecommendationOptionsTest(unittest.TestCase):
    def test_recommendation_option_constants_match_current_product_scope(self) -> None:
        self.assertEqual(recommendation.VALID_WEATHERS, ("hot", "mild", "cold", "rainy"))
        self.assertEqual(
            recommendation.VALID_EVENTS,
            ("casual", "smart-casual", "formal", "sport"),
        )
        self.assertEqual(
            recommendation.VALID_MOODS,
            ("energetic", "professional", "relaxed", "calm"),
        )
        self.assertNotIn("business", recommendation.VALID_EVENTS)
        self.assertNotIn("romantic", recommendation.VALID_MOODS)

    def test_storage_exposes_embedding_dimension_without_leaking_vector(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "wardrobe.db"
            init_db(db_path)

            item = insert_item(
                db_path,
                item_id="item-1",
                image_path=str(Path(tmp) / "shirt.jpg"),
                main_category="tops",
                sub_category="shirt",
                bbox_json=None,
                embedding_json=json.dumps([0.1, 0.2, 0.3]),
                model_confidence=0.91,
            )

            payload = to_api_dict(item, base_url="http://localhost:5000")

            self.assertEqual(payload["embedding_dim"], 3)
            self.assertNotIn("embedding_json", payload)
            self.assertNotIn("embedding", payload)


if __name__ == "__main__":
    unittest.main()
