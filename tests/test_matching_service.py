"""
Unit Tests for Phase 6: Explainable Multi-Factor Text-Matching Algorithm
Verifies tokenization, text/location/date similarity, explainable score breakdown,
and automated counterpart discovery.
"""

import os
import sqlite3
import unittest

from database.connection import DEFAULT_SCHEMA_PATH, seed_default_admin
from database.repository import ItemRepository, UserRepository
from models.item import Item
from services.matching_service import MatchingService, MatchResult


class TestMatchingService(unittest.TestCase):
    """Test suite for Phase 6 MatchingService."""

    def setUp(self) -> None:
        self.test_db = os.path.join(os.path.dirname(__file__), "test_match.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        conn = sqlite3.connect(self.test_db)
        conn.execute("PRAGMA foreign_keys = ON;")
        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

        seed_default_admin(self.test_db)
        self.item_repo = ItemRepository(self.test_db)
        self.user_repo = UserRepository(self.test_db)
        self.service = MatchingService(item_repo=self.item_repo)
        self.admin = self.user_repo.get_by_username("admin")

    def tearDown(self) -> None:
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_tokenize_and_stopwords(self) -> None:
        """Verify tokenization removes punctuation and stopwords."""
        text = "I lost my Black Lenovo laptop charger near the library!"
        tokens = self.service.tokenize(text)
        self.assertIn("lenovo", tokens)
        self.assertIn("laptop", tokens)
        self.assertIn("charger", tokens)
        self.assertIn("black", tokens)
        self.assertNotIn("the", tokens)
        self.assertNotIn("my", tokens)

    def test_text_similarity(self) -> None:
        """Verify salient text token similarity calculation."""
        text_a = "Black Dell 65W Laptop Charger"
        text_b = "Found Dell charging adapter with black cable"
        score, shared = self.service.calculate_text_similarity(text_a, text_b)
        self.assertGreater(score, 0.4)
        self.assertIn("black", shared)
        self.assertIn("dell", shared)

    def test_location_similarity(self) -> None:
        """Verify location similarity with exact match and substring match."""
        # Exact match
        exact_score, _ = self.service.calculate_location_similarity("Main Library", "Main Library")
        self.assertEqual(exact_score, 1.0)

        # Substring containment
        sub_score, _ = self.service.calculate_location_similarity("Library", "Main Library 2nd Floor")
        self.assertGreaterEqual(sub_score, 0.8)

        # Completely disjoint locations
        disjoint_score, _ = self.service.calculate_location_similarity("Sports Complex", "Physics Laboratory")
        self.assertLess(disjoint_score, 0.2)

    def test_date_proximity(self) -> None:
        """Verify date proximity scoring based on days elapsed."""
        same_day = self.service.calculate_date_proximity("2026-10-25", "2026-10-25")
        self.assertEqual(same_day, 1.0)

        next_day = self.service.calculate_date_proximity("2026-10-25", "2026-10-26")
        self.assertGreaterEqual(next_day, 0.85)

        distant = self.service.calculate_date_proximity("2026-10-25", "2026-08-01")
        self.assertLessEqual(distant, 0.1)

    def test_score_match_and_explainability(self) -> None:
        """Verify full multi-factor score breakdown and explainable reasons."""
        lost_item = Item(
            id=1,
            type="LOST",
            user_id=self.admin.id,
            title="Black Lenovo ThinkPad Laptop Charger",
            category="Electronics",
            description="65W Type-C adapter left on table near window.",
            event_date="2026-10-24",
            location="Central Library 2nd Floor",
            image_path=None,
            status="OPEN"
        )

        found_item = Item(
            id=2,
            type="FOUND",
            user_id=self.admin.id,
            title="Lenovo Type-C Charger",
            category="Electronics",
            description="Found a black 65W Lenovo charger on table in library.",
            event_date="2026-10-24",
            location="Central Library",
            image_path=None,
            status="OPEN"
        )

        match = self.service.score_match(lost_item, found_item)
        self.assertGreater(match.overall_score, 75.0)
        self.assertEqual(match.category_score, 1.0)
        self.assertGreater(match.text_score, 0.5)
        self.assertGreater(match.location_score, 0.8)
        self.assertGreater(match.date_score, 0.9)
        self.assertIn("Identical category", match.explanation)
        self.assertTrue(len(match.reasons) >= 3)

    def test_category_mismatch_penalty(self) -> None:
        """Verify items with different categories receive heavy score penalty."""
        lost_wallet = Item(
            id=1,
            type="LOST",
            user_id=self.admin.id,
            title="Brown Leather Wallet",
            category="Personal belongings",
            description="Lost brown leather wallet with cards.",
            event_date="2026-10-24",
            location="Cafeteria",
            image_path=None,
            status="OPEN"
        )

        found_book = Item(
            id=2,
            type="FOUND",
            user_id=self.admin.id,
            title="Leather Diary Notebook",
            category="Books and stationery",
            description="Found a brown leather diary in cafeteria.",
            event_date="2026-10-24",
            location="Cafeteria",
            image_path=None,
            status="OPEN"
        )

        match = self.service.score_match(lost_wallet, found_book)
        # Should be capped due to category mismatch
        self.assertLessEqual(match.overall_score, 35.0)
        self.assertEqual(match.category_score, 0.0)

    def test_find_matches_for_item_counterparts(self) -> None:
        """Verify automated candidate search queries and ranks counterpart items."""
        # Insert 3 FOUND items into database
        found_match = Item(
            id=None,
            type="FOUND",
            user_id=self.admin.id,
            title="Blue Campus ID Card for Rahul Sharma",
            category="Identity cards",
            description="Found student identity card on ground near Block B stairs.",
            event_date="2026-10-24",
            location="Block B",
            image_path=None,
            status="OPEN"
        )
        found_unrelated = Item(
            id=None,
            type="FOUND",
            user_id=self.admin.id,
            title="Green Umbrella",
            category="Accessories",
            description="Foldable green umbrella left in classroom 102.",
            event_date="2026-10-20",
            location="Block A",
            image_path=None,
            status="OPEN"
        )

        self.item_repo.create(found_match)
        self.item_repo.create(found_unrelated)

        # Student reports a LOST ID card
        lost_card = Item(
            id=99,
            type="LOST",
            user_id=self.admin.id,
            title="Lost Student ID Card Rahul",
            category="Identity cards",
            description="Lost my campus ID card somewhere around Block B today.",
            event_date="2026-10-24",
            location="Block B",
            image_path=None,
            status="OPEN"
        )

        matches = self.service.find_matches_for_item(lost_card, min_threshold=30.0)
        self.assertTrue(len(matches) >= 1)
        top_match = matches[0]
        self.assertEqual(top_match.target_item.category, "Identity cards")
        self.assertIn("ID Card", top_match.target_item.title)
        self.assertGreater(top_match.overall_score, 60.0)


if __name__ == "__main__":
    unittest.main()
