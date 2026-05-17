from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.smartwardrobe_backend.storage import (
    get_item,
    init_db,
    insert_item,
    list_liked_outfits,
    record_outfit_feedback,
    to_api_dict,
    update_item,
)


class StorageMetadataTest(unittest.TestCase):
    def test_item_metadata_defaults_and_updates_are_exposed(self) -> None:
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
                model_confidence=0.9,
            )

            payload = to_api_dict(item, base_url="http://localhost:5000")
            self.assertFalse(payload["favorite"])
            self.assertEqual(payload["times_worn"], 0)

            updated = update_item(db_path, "item-1", favorite=True, times_worn=3)
            updated_payload = to_api_dict(updated, base_url="http://localhost:5000")
            self.assertTrue(updated_payload["favorite"])
            self.assertEqual(updated_payload["times_worn"], 3)

    def test_liked_outfit_feedback_persists_and_increments_worn_counts(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db_path = Path(tmp) / "wardrobe.db"
            init_db(db_path)
            for item_id in ("top-1", "bottom-1", "shoe-1"):
                insert_item(
                    db_path,
                    item_id=item_id,
                    image_path=str(Path(tmp) / f"{item_id}.jpg"),
                    main_category="tops",
                    sub_category="shirt",
                    bbox_json=None,
                    embedding_json=None,
                    model_confidence=None,
                )

            record_outfit_feedback(
                db_path,
                action="like",
                item_ids=["top-1", "bottom-1", "shoe-1"],
                score=0.87,
            )

            liked = list_liked_outfits(db_path)
            self.assertEqual(len(liked), 1)
            self.assertEqual(liked[0]["item_ids"], ["top-1", "bottom-1", "shoe-1"])
            self.assertEqual(get_item(db_path, "top-1").times_worn, 1)


if __name__ == "__main__":
    unittest.main()
