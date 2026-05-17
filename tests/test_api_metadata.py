from __future__ import annotations

import unittest
from unittest.mock import patch


class ApiMetadataTest(unittest.TestCase):
    def test_category_metadata_includes_recommendation_options(self) -> None:
        try:
            from backend.smartwardrobe_backend.api import create_app
        except ModuleNotFoundError as e:
            if e.name == "flask":
                self.skipTest("flask is not installed in this Python environment")
            raise

        with patch("backend.smartwardrobe_backend.api.resolve_assets"), patch(
            "backend.smartwardrobe_backend.api.load_models"
        ) as load_models:
            load_models.return_value.yolo = None
            load_models.return_value.resnet18_subcat = None
            load_models.return_value.resnet50_compat = None
            load_models.return_value.subcat_mapping = {}
            load_models.return_value.main_to_subcat_ids = {}
            load_models.return_value.errors = []
            load_models.return_value.warnings = []

            app = create_app()
            response = app.test_client().get("/metadata/categories")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["weather_types"], ["hot", "mild", "cold", "rainy"])
        self.assertEqual(
            payload["event_types"],
            ["casual", "smart-casual", "formal", "sport"],
        )
        self.assertEqual(
            payload["mood_types"],
            ["energetic", "professional", "relaxed", "calm"],
        )
        self.assertNotIn("business", payload["event_types"])
        self.assertNotIn("romantic", payload["mood_types"])


if __name__ == "__main__":
    unittest.main()
