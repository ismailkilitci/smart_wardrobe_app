from __future__ import annotations

import unittest

from backend.smartwardrobe_backend.vector_index import VectorIndex


class VectorIndexTest(unittest.TestCase):
    def test_search_returns_nearest_embedding_ids(self) -> None:
        index = VectorIndex(dimension=3)
        index.add("shirt", [1.0, 0.0, 0.0])
        index.add("shoe", [0.0, 1.0, 0.0])

        results = index.search([0.9, 0.1, 0.0], top_k=2)

        self.assertEqual(results[0].item_id, "shirt")
        self.assertGreater(results[0].score, results[1].score)


if __name__ == "__main__":
    unittest.main()
