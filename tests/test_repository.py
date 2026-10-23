"""
Unit Tests for Phase 3: Data Repository CRUD Operations
Verifies Create, Read, Update, and Safe Delete with in-memory SQLite database.
"""

import os
import sqlite3
import unittest

from database.connection import hash_password, DEFAULT_SCHEMA_PATH
from database.repository import UserRepository, ItemRepository, ClaimRepository
from models.user import User
from models.item import Item
from models.claim import Claim


class TestRepositories(unittest.TestCase):
    """Test suite for UserRepository, ItemRepository, and ClaimRepository."""

    def setUp(self) -> None:
        """Create fresh in-memory database per test with initialized schema."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.row_factory = sqlite3.Row

        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())

        # Bind repositories to connection by patching get_connection in repository tests
        # We can pass an in-memory db file or test database
        self.test_db = os.path.join(os.path.dirname(__file__), "test_repo.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        # Initialize schema in test file database
        test_conn = sqlite3.connect(self.test_db)
        test_conn.execute("PRAGMA foreign_keys = ON;")
        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            test_conn.executescript(f.read())
        test_conn.close()

        self.user_repo = UserRepository(self.test_db)
        self.item_repo = ItemRepository(self.test_db)
        self.claim_repo = ClaimRepository(self.test_db)

    def tearDown(self) -> None:
        self.conn.close()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_user_repository_crud(self) -> None:
        """Verify full user CRUD lifecycle."""
        pw_hash, salt = hash_password("Secret2026")
        user = User(
            id=None,
            username="student_rahul",
            password_hash=pw_hash,
            salt=salt,
            full_name="Rahul Sharma",
            email="rahul@campus.edu",
            role="student"
        )
        user_id = self.user_repo.create(user)
        self.assertIsNotNone(user_id)

        # Read by ID
        fetched = self.user_repo.get_by_id(user_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.username, "student_rahul")

        # Read by username
        fetched_user = self.user_repo.get_by_username("student_rahul")
        self.assertIsNotNone(fetched_user)

        # Read by email
        fetched_email = self.user_repo.get_by_email("rahul@campus.edu")
        self.assertIsNotNone(fetched_email)

        # Update profile
        updated = self.user_repo.update_profile(user_id, "Rahul S.", "rahul.s@campus.edu")
        self.assertTrue(updated)
        refetched = self.user_repo.get_by_id(user_id)
        self.assertEqual(refetched.full_name, "Rahul S.")
        self.assertEqual(refetched.email, "rahul.s@campus.edu")

        # Delete user
        deleted = self.user_repo.delete(user_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.user_repo.get_by_id(user_id))

    def test_item_repository_crud_and_safe_delete(self) -> None:
        """Verify item creation, updating, permission enforcement, and safe deletion."""
        pw_hash, salt = hash_password("Pass123")
        owner_id = self.user_repo.create(User(None, "owner", pw_hash, salt, "Owner User", "o@campus.edu"))
        other_user_id = self.user_repo.create(User(None, "other", pw_hash, salt, "Other User", "oth@campus.edu"))

        item = Item(
            id=None,
            type="LOST",
            user_id=owner_id,
            title="Scientific Calculator",
            category="Electronics",
            description="Black Casio calculator fx-991EX",
            event_date="2026-10-21",
            location="Room 302"
        )
        item_id = self.item_repo.create(item)
        self.assertIsNotNone(item_id)

        # Update item
        item.id = item_id
        item.description = "Black Casio calculator fx-991EX with name sticker"
        self.assertTrue(self.item_repo.update(item))

        # Permission check: unauthorized user cannot delete
        with self.assertRaises(PermissionError):
            self.item_repo.delete(item_id, requesting_user_id=other_user_id, is_admin=False)

        # Safe deletion: owner can delete an OPEN report
        self.assertTrue(self.item_repo.delete(item_id, requesting_user_id=owner_id, is_admin=False))
        self.assertIsNone(self.item_repo.get_by_id(item_id))

    def test_item_search_filtering_and_pagination(self) -> None:
        """Verify dynamic search, category filtering, keyword matching, and pagination."""
        pw_hash, salt = hash_password("Pass123")
        uid = self.user_repo.create(User(None, "reporter", pw_hash, salt, "Reporter", "rep@campus.edu"))

        # Create 3 items
        items_data = [
            ("LOST", "Blue Dell Laptop", "Electronics", "Dell Inspiron 15 with stickers", "2026-10-18", "Library 2nd Floor"),
            ("FOUND", "Black Wallet", "Personal belongings", "Leather wallet with coins", "2026-10-19", "Canteen"),
            ("FOUND", "Scientific Calculator", "Electronics", "Casio calculator in grey cover", "2026-10-20", "Library 1st Floor"),
        ]
        for itype, title, cat, desc, dt, loc in items_data:
            self.item_repo.create(Item(None, itype, uid, title, cat, desc, dt, loc))

        # Test filter by type
        found_items = self.item_repo.list_items(item_type="FOUND")
        self.assertEqual(len(found_items), 2)

        # Test filter by category
        electronics = self.item_repo.list_items(category="Electronics")
        self.assertEqual(len(electronics), 2)

        # Test keyword search across title and description
        wallet_search = self.item_repo.list_items(keyword="Leather")
        self.assertEqual(len(wallet_search), 1)
        self.assertEqual(wallet_search[0].title, "Black Wallet")

        # Test location search
        lib_items = self.item_repo.list_items(location="Library")
        self.assertEqual(len(lib_items), 2)

        # Test pagination
        page1 = self.item_repo.list_items(limit=2, offset=0)
        self.assertEqual(len(page1), 2)
        page2 = self.item_repo.list_items(limit=2, offset=2)
        self.assertEqual(len(page2), 1)

    def test_claim_repository_lifecycle(self) -> None:
        """Verify claim creation, automatic status transitions, and reviews."""
        pw_hash, salt = hash_password("Pass123")
        finder_id = self.user_repo.create(User(None, "finder", pw_hash, salt, "Finder", "find@campus.edu"))
        claimant_id = self.user_repo.create(User(None, "claimant", pw_hash, salt, "Claimant", "claim@campus.edu"))
        admin_id = self.user_repo.create(User(None, "admin_user", pw_hash, salt, "Admin", "admin@campus.edu", "admin"))

        found_item_id = self.item_repo.create(
            Item(None, "FOUND", finder_id, "Wireless Earbuds", "Electronics", "White case", "2026-10-21", "Auditorium")
        )

        # File claim
        claim = Claim(
            id=None,
            item_id=found_item_id,
            claimant_id=claimant_id,
            proof_description="Left bud has a red dot marker on the stem"
        )
        claim_id = self.claim_repo.create(claim)
        self.assertIsNotNone(claim_id)

        # Item status should automatically transition to CLAIM_PENDING
        item_refetched = self.item_repo.get_by_id(found_item_id)
        self.assertEqual(item_refetched.status, "CLAIM_PENDING")

        # Admin approves claim
        self.assertTrue(self.claim_repo.update_status(claim_id, "APPROVED", admin_id, "Marker dot verified"))
        reviewed_claim = self.claim_repo.get_by_id(claim_id)
        self.assertEqual(reviewed_claim.status, "APPROVED")
        self.assertEqual(reviewed_claim.reviewed_by, admin_id)


if __name__ == "__main__":
    unittest.main()
