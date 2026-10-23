"""
Unit Tests for Phase 2: Database Schema, Constraints, and Operations
"""

import os
import sqlite3
import unittest

from database.connection import (
    get_connection,
    get_db_cursor,
    init_database,
    seed_default_admin,
    hash_password,
    DEFAULT_SCHEMA_PATH,
)


class TestDatabaseSchema(unittest.TestCase):
    """Test suite verifying relational tables, constraints, foreign keys, and transactions."""

    def setUp(self) -> None:
        """Create a fresh in-memory database initialized with schema.sql for each test."""
        # SQLite in-memory database shared across connections via URI or direct connection
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.row_factory = sqlite3.Row

        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())

    def tearDown(self) -> None:
        self.conn.close()

    def test_tables_created(self) -> None:
        """Verify that all 4 required relational tables are created."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row["name"] for row in cursor.fetchall()]
        expected_tables = ["claims", "item_returns", "items", "users"]
        for expected in expected_tables:
            self.assertIn(expected, tables, f"Table {expected} was not created.")

    def test_indexes_created(self) -> None:
        """Verify performance indexes exist."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = [row["name"] for row in cursor.fetchall()]
        expected_indexes = [
            "idx_items_type_status",
            "idx_items_category",
            "idx_items_location",
            "idx_claims_item_id",
            "idx_claims_status",
            "idx_users_username",
        ]
        for idx in expected_indexes:
            self.assertIn(idx, indexes, f"Index {idx} was not found.")

    def test_user_insertion_and_uniqueness(self) -> None:
        """Verify user insertion and unique username/email constraints."""
        pw_hash, salt = hash_password("Secret123")
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, salt, full_name, email, role)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("student1", pw_hash, salt, "Alice Smith", "alice@campus.edu", "student")
        )
        self.conn.commit()

        # Duplicate username must fail
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, salt, full_name, email, role)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("student1", pw_hash, salt, "Another Alice", "another@campus.edu", "student")
            )

        # Duplicate email must fail
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, salt, full_name, email, role)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("student2", pw_hash, salt, "Bob Jones", "alice@campus.edu", "student")
            )

    def test_user_role_check_constraint(self) -> None:
        """Verify CHECK constraint prevents invalid user roles."""
        pw_hash, salt = hash_password("Pass123")
        cursor = self.conn.cursor()
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, salt, full_name, email, role)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("bad_role", pw_hash, salt, "Bad User", "bad@campus.edu", "superhero")
            )

    def test_foreign_key_enforcement_items(self) -> None:
        """Verify that inserting an item with a non-existent user_id violates foreign key."""
        cursor = self.conn.cursor()
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO items (type, user_id, title, category, description, event_date, location)
                VALUES ('LOST', 9999, 'Blue Backpack', 'Personal belongings', 'Contains notebook', '2026-10-20', 'Library')
                """
            )

    def test_item_category_check_constraint(self) -> None:
        """Verify item category must be one of the permitted campus categories."""
        # Insert valid user first
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, salt, full_name, email, role)
            VALUES ('john', 'hash', 'salt', 'John Doe', 'john@campus.edu', 'student')
            """
        )
        user_id = cursor.lastrowid

        # Insert with valid category succeeds
        cursor.execute(
            """
            INSERT INTO items (type, user_id, title, category, description, event_date, location)
            VALUES ('LOST', ?, 'Scientific Calculator', 'Electronics', 'Casio fx-991EX', '2026-10-21', 'Lab 3')
            """,
            (user_id,)
        )
        self.conn.commit()

        # Insert with invalid category fails
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO items (type, user_id, title, category, description, event_date, location)
                VALUES ('LOST', ?, 'Space Shuttle', 'Spaceships', 'Invalid category item', '2026-10-21', 'Campus')
                """,
                (user_id,)
            )

    def test_item_type_check_constraint(self) -> None:
        """Verify item type must only be LOST or FOUND."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, salt, full_name, email, role)
            VALUES ('jane', 'hash', 'salt', 'Jane Doe', 'jane@campus.edu', 'student')
            """
        )
        user_id = cursor.lastrowid

        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO items (type, user_id, title, category, description, event_date, location)
                VALUES ('STOLEN', ?, 'Earphones', 'Electronics', 'Black earbuds', '2026-10-21', 'Canteen')
                """,
                (user_id,)
            )

    def test_cascade_delete_user_removes_items(self) -> None:
        """Verify ON DELETE CASCADE removes associated items when user is deleted."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, salt, full_name, email, role)
            VALUES ('temporary', 'hash', 'salt', 'Temp User', 'temp@campus.edu', 'student')
            """
        )
        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO items (type, user_id, title, category, description, event_date, location)
            VALUES ('LOST', ?, 'Water Bottle', 'Personal belongings', 'Steel bottle', '2026-10-21', 'Gym')
            """,
            (user_id,)
        )
        self.conn.commit()

        # Verify item exists
        cursor.execute("SELECT COUNT(*) as cnt FROM items WHERE user_id = ?", (user_id,))
        self.assertEqual(cursor.fetchone()["cnt"], 1)

        # Delete user
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.conn.commit()

        # Verify item is automatically cascaded and removed
        cursor.execute("SELECT COUNT(*) as cnt FROM items WHERE user_id = ?", (user_id,))
        self.assertEqual(cursor.fetchone()["cnt"], 0)

    def test_item_returns_duplicate_prevention(self) -> None:
        """Verify an item cannot have multiple returns (item_id UNIQUE constraint)."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, salt, full_name, email, role)
            VALUES ('u1', 'h1', 's1', 'User 1', 'u1@campus.edu', 'student'),
                   ('u2', 'h2', 's2', 'User 2', 'u2@campus.edu', 'student'),
                   ('adm', 'h3', 's3', 'Admin', 'adm@campus.edu', 'admin')
            """
        )
        u1_id, u2_id, admin_id = 1, 2, 3

        cursor.execute(
            """
            INSERT INTO items (type, user_id, title, category, description, event_date, location)
            VALUES ('FOUND', ?, 'Silver Watch', 'Accessories', 'Analog watch', '2026-10-21', 'Library')
            """,
            (u1_id,)
        )
        item_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO claims (item_id, claimant_id, proof_description, status)
            VALUES (?, ?, 'Has scratch on clasp', 'APPROVED')
            """,
            (item_id, u2_id)
        )
        claim1_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO claims (item_id, claimant_id, proof_description, status)
            VALUES (?, ?, 'Another claim', 'APPROVED')
            """,
            (item_id, u1_id)
        )
        claim2_id = cursor.lastrowid

        # First return succeeds
        cursor.execute(
            """
            INSERT INTO item_returns (item_id, claim_id, handed_over_by, received_by, verification_notes)
            VALUES (?, ?, ?, ?, 'Identity card verified')
            """,
            (item_id, claim1_id, admin_id, u2_id)
        )
        self.conn.commit()

        # Second return for same item MUST raise IntegrityError
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute(
                """
                INSERT INTO item_returns (item_id, claim_id, handed_over_by, received_by, verification_notes)
                VALUES (?, ?, ?, ?, 'Duplicate return attempt')
                """,
                (item_id, claim2_id, admin_id, u1_id)
            )

    def test_file_database_init_and_admin_seeding(self) -> None:
        """Verify init_database() and seed_default_admin() on a temporary file db."""
        test_db = os.path.join(os.path.dirname(__file__), "test_temp.db")
        try:
            if os.path.exists(test_db):
                os.remove(test_db)

            # Initialize database
            init_database(test_db)

            # Seed admin first time: returns True
            created = seed_default_admin(test_db)
            self.assertTrue(created)

            # Seed admin second time: returns False (already exists)
            created_again = seed_default_admin(test_db)
            self.assertFalse(created_again)

            # Verify admin credentials can be retrieved
            with get_db_cursor(test_db) as cur:
                cur.execute("SELECT username, role FROM users WHERE role = 'admin'")
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["username"], "admin")
                self.assertEqual(row["role"], "admin")

        finally:
            if os.path.exists(test_db):
                os.remove(test_db)


if __name__ == "__main__":
    unittest.main()
