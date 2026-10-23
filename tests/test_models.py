"""
Unit Tests for Phase 3: Domain Data Models and Invariant Validation
"""

import unittest
from models.user import User
from models.item import Item
from models.claim import Claim


class TestDomainModels(unittest.TestCase):
    """Test validation and business invariants for User, Item, and Claim models."""

    def test_valid_user(self) -> None:
        """Verify that a properly constructed User model passes validation."""
        user = User(
            id=None,
            username="john_doe",
            password_hash="hash123",
            salt="salt123",
            full_name="John Doe",
            email="john@campus.edu",
            role="student"
        )
        # Should not raise
        user.validate()
        self.assertFalse(user.is_admin)

    def test_invalid_username_characters(self) -> None:
        """Verify invalid username formats raise ValueError."""
        user = User(
            id=None,
            username="john doe spaces!",
            password_hash="hash",
            salt="salt",
            full_name="John Doe",
            email="john@campus.edu"
        )
        with self.assertRaises(ValueError):
            user.validate()

    def test_invalid_email(self) -> None:
        """Verify invalid email formats raise ValueError."""
        user = User(
            id=None,
            username="john_doe",
            password_hash="hash",
            salt="salt",
            full_name="John Doe",
            email="not-an-email"
        )
        with self.assertRaises(ValueError):
            user.validate()

    def test_valid_item(self) -> None:
        """Verify that a valid Item model passes validation."""
        item = Item(
            id=None,
            type="LOST",
            user_id=1,
            title="Scientific Calculator",
            category="Electronics",
            description="Casio fx-991EX with stickers on back",
            event_date="2026-10-22",
            location="Computer Lab 2"
        )
        item.validate()
        self.assertFalse(item.is_claimable)  # Lost items cannot be claimed
        self.assertTrue(item.can_be_deleted)

    def test_item_invalid_date(self) -> None:
        """Verify that malformed dates raise ValueError."""
        item = Item(
            id=None,
            type="LOST",
            user_id=1,
            title="Notebook",
            category="Books and stationery",
            description="Math notebook",
            event_date="22-10-2026",  # Not YYYY-MM-DD
            location="Room 101"
        )
        with self.assertRaises(ValueError):
            item.validate()

    def test_item_invalid_category(self) -> None:
        """Verify that non-permitted category raises ValueError."""
        item = Item(
            id=None,
            type="LOST",
            user_id=1,
            title="Notebook",
            category="Automobiles",
            description="Math notebook",
            event_date="2026-10-22",
            location="Room 101"
        )
        with self.assertRaises(ValueError):
            item.validate()

    def test_valid_claim(self) -> None:
        """Verify that a valid Claim passes validation."""
        claim = Claim(
            id=None,
            item_id=10,
            claimant_id=2,
            proof_description="Inside cover has my student registration number written in pencil."
        )
        claim.validate()
        self.assertEqual(claim.status, "PENDING")

    def test_claim_empty_proof(self) -> None:
        """Verify that empty or short proof raises ValueError."""
        claim = Claim(
            id=None,
            item_id=10,
            claimant_id=2,
            proof_description="mine"  # too short
        )
        with self.assertRaises(ValueError):
            claim.validate()


if __name__ == "__main__":
    unittest.main()
