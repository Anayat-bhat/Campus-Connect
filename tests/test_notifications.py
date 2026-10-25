"""
Unit Tests for Phase 11: Notification & Smart Match Alert System
Verifies notification domain validation, repository persistence, unread counter queries,
automated match detection alerts, and claim workflow alert dispatches.
"""

import os
import sqlite3
import unittest
import tkinter as tk
from typing import Optional

from database.connection import DEFAULT_SCHEMA_PATH, seed_default_admin
from database.repository import (
    UserRepository,
    ItemRepository,
    ClaimRepository,
    NotificationRepository,
)
from models.user import User
from models.item import Item
from models.claim import Claim
from models.notification import Notification, VALID_NOTIFICATION_TYPES
from services.notification_service import NotificationService
from services.claim_service import ClaimService
from services.matching_service import MatchingService
from services.auth_service import AuthService
from gui.notification_dialog import NotificationCenterDialog


class TestNotificationModel(unittest.TestCase):
    """Unit tests for the Notification domain entity."""

    def test_valid_notification(self) -> None:
        notif = Notification(
            id=1,
            user_id=10,
            title="Item Matched",
            message="Your lost keys might have been found at Central Library.",
            type="MATCH_FOUND",
            related_item_id=5,
            is_read=False,
        )
        # Should not raise
        notif.validate()
        self.assertEqual(notif.type, "MATCH_FOUND")
        self.assertFalse(notif.is_read)

    def test_invalid_user_id(self) -> None:
        notif = Notification(
            id=1,
            user_id=0,
            title="Valid Title",
            message="Valid message content for test.",
        )
        with self.assertRaises(ValueError):
            notif.validate()

    def test_short_title_and_message(self) -> None:
        short_title = Notification(
            id=1,
            user_id=1,
            title="Hi",
            message="Valid message content here.",
        )
        with self.assertRaises(ValueError):
            short_title.validate()

        short_msg = Notification(
            id=1,
            user_id=1,
            title="Valid Title",
            message="Hey",
        )
        with self.assertRaises(ValueError):
            short_msg.validate()

    def test_invalid_notification_type(self) -> None:
        invalid_type = Notification(
            id=1,
            user_id=1,
            title="Valid Title",
            message="Valid message content here.",
            type="UNKNOWN_TYPE",
        )
        with self.assertRaises(ValueError):
            invalid_type.validate()


class TestNotificationRepository(unittest.TestCase):
    """Integration tests for NotificationRepository database operations."""

    def setUp(self) -> None:
        self.test_db = os.path.join(os.path.dirname(__file__), "test_notifications.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        conn = sqlite3.connect(self.test_db)
        conn.execute("PRAGMA foreign_keys = ON;")
        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

        seed_default_admin(self.test_db)
        self.user_repo = UserRepository(self.test_db)
        self.item_repo = ItemRepository(self.test_db)
        self.notif_repo = NotificationRepository(self.test_db)

        # Create student user
        self.student = User(
            id=None,
            username="notif_student",
            password_hash="fakehash",
            salt="fakesalt",
            full_name="Student One",
            email="student1@campus.edu",
            role="student",
        )
        self.student.id = self.user_repo.create(self.student)

    def tearDown(self) -> None:
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                pass

    def test_create_and_fetch_notification(self) -> None:
        notif = Notification(
            id=None,
            user_id=self.student.id,
            title="Welcome Alert",
            message="Welcome to CampusConnect Notification Center!",
            type="SYSTEM",
        )
        notif_id = self.notif_repo.create(notif)
        self.assertGreater(notif_id, 0)

        fetched = self.notif_repo.get_by_id(notif_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "Welcome Alert")
        self.assertFalse(fetched.is_read)
        self.assertEqual(fetched.user_id, self.student.id)

    def test_count_unread_and_mark_read(self) -> None:
        self.assertEqual(self.notif_repo.count_unread(self.student.id), 0)

        # Create two notifications
        n1 = Notification(
            id=None,
            user_id=self.student.id,
            title="Alert 1",
            message="Content for alert one.",
            type="SYSTEM",
        )
        n2 = Notification(
            id=None,
            user_id=self.student.id,
            title="Alert 2",
            message="Content for alert two.",
            type="MATCH_FOUND",
        )
        id1 = self.notif_repo.create(n1)
        id2 = self.notif_repo.create(n2)

        self.assertEqual(self.notif_repo.count_unread(self.student.id), 2)

        # Mark single as read
        self.assertTrue(self.notif_repo.mark_as_read(id1))
        self.assertEqual(self.notif_repo.count_unread(self.student.id), 1)

        # Unread list should now have length 1
        unread_list = self.notif_repo.list_by_user(self.student.id, unread_only=True)
        self.assertEqual(len(unread_list), 1)
        self.assertEqual(unread_list[0].id, id2)

        # Mark all as read
        marked_count = self.notif_repo.mark_all_as_read(self.student.id)
        self.assertEqual(marked_count, 1)
        self.assertEqual(self.notif_repo.count_unread(self.student.id), 0)

    def test_delete_notification(self) -> None:
        n = Notification(
            id=None,
            user_id=self.student.id,
            title="Temporary Notification",
            message="Will be deleted shortly.",
        )
        nid = self.notif_repo.create(n)
        self.assertTrue(self.notif_repo.delete(nid))
        self.assertIsNone(self.notif_repo.get_by_id(nid))


class TestNotificationService(unittest.TestCase):
    """Test suite for high-level NotificationService and smart alerts."""

    def setUp(self) -> None:
        self.test_db = os.path.join(os.path.dirname(__file__), "test_notif_service.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        conn = sqlite3.connect(self.test_db)
        conn.execute("PRAGMA foreign_keys = ON;")
        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

        seed_default_admin(self.test_db)
        self.user_repo = UserRepository(self.test_db)
        self.item_repo = ItemRepository(self.test_db)
        self.claim_repo = ClaimRepository(self.test_db)
        self.notif_repo = NotificationRepository(self.test_db)
        self.auth_service = AuthService(user_repo=self.user_repo)

        self.notif_service = NotificationService(
            notif_repo=self.notif_repo,
            item_repo=self.item_repo,
            user_repo=self.user_repo,
            db_path=self.test_db,
        )

        self.claim_service = ClaimService(
            item_repo=self.item_repo,
            claim_repo=self.claim_repo,
            user_repo=self.user_repo,
            notification_service=self.notif_service,
            db_path=self.test_db,
        )

        self.student_a = self.auth_service.register_user(
            username="user_a",
            password="Password123",
            full_name="Alice Student",
            email="alice@campus.edu",
        )
        self.student_b = self.auth_service.register_user(
            username="user_b",
            password="Password123",
            full_name="Bob Student",
            email="bob@campus.edu",
        )

    def tearDown(self) -> None:
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                pass

    def test_custom_notification(self) -> None:
        notif = self.notif_service.notify(
            user_id=self.student_a.id,
            title="System Maintenance",
            message="Server upgrade scheduled at midnight tonight.",
            notif_type="SYSTEM",
        )
        self.assertIsNotNone(notif.id)
        self.assertEqual(self.notif_service.get_unread_count(self.student_a.id), 1)

        items = self.notif_service.list_user_notifications(self.student_a.id)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "System Maintenance")

    def test_match_alert_scanning(self) -> None:
        # User A reported a lost blue Dell laptop at Central Library
        lost_item = Item(
            id=None,
            type="LOST",
            user_id=self.student_a.id,
            title="Blue Dell XPS 15 Laptop",
            category="Electronics",
            description="Silver keyboard, blue skin, Intel i7 badge",
            event_date="2026-10-25",
            location="Central Library 2nd Floor",
            status="OPEN",
        )
        lost_item.id = self.item_repo.create(lost_item)

        # User B now reports finding a Dell laptop at Central Library
        found_item = Item(
            id=None,
            type="FOUND",
            user_id=self.student_b.id,
            title="Blue Dell Laptop",
            category="Electronics",
            description="Found Dell laptop with blue skin near study tables",
            event_date="2026-10-25",
            location="Central Library",
            status="OPEN",
        )
        found_item.id = self.item_repo.create(found_item)

        # Trigger match scanning for found_item
        alerts = self.notif_service.scan_and_alert_matches(found_item, min_threshold=50.0)
        self.assertGreaterEqual(len(alerts), 1)

        # User A (owner of the lost counterpart) should receive an alert
        user_a_notifs = self.notif_service.list_user_notifications(self.student_a.id)
        self.assertEqual(len(user_a_notifs), 1)
        self.assertEqual(user_a_notifs[0].type, "MATCH_FOUND")
        self.assertIn("Match Found", user_a_notifs[0].title)
        self.assertIn("Dell", user_a_notifs[0].message)
        self.assertIn("algorithmic match", user_a_notifs[0].message)

    def test_claim_submission_and_decision_alerts(self) -> None:
        # User A found a calculator
        found_item = Item(
            id=None,
            type="FOUND",
            user_id=self.student_a.id,
            title="Casio fx-991EX Calculator",
            category="Electronics",
            description="Scientific calculator with solar panel",
            event_date="2026-10-25",
            location="Room 304",
            status="OPEN",
        )
        found_item.id = self.item_repo.create(found_item)

        # User B submits an ownership claim
        claim = self.claim_service.submit_claim(
            item_id=found_item.id,
            claimant_id=self.student_b.id,
            proof_description="Has my initials 'BS' engraved on back battery cover.",
        )

        # Finder (User A) should have received a CLAIM_SUBMITTED notification
        finder_notifs = self.notif_service.list_user_notifications(self.student_a.id)
        self.assertEqual(len(finder_notifs), 1)
        self.assertEqual(finder_notifs[0].type, "CLAIM_SUBMITTED")
        self.assertIn("Claim Submitted", finder_notifs[0].title)

        # Admin approves the claim
        admin = self.user_repo.get_by_username("admin")
        self.claim_service.approve_claim(
            claim_id=claim.id,
            reviewer_id=admin.id,
            verification_notes="Initials match student ID.",
        )

        # Claimant (User B) should have received a CLAIM_APPROVED notification
        claimant_notifs = self.notif_service.list_user_notifications(self.student_b.id)
        self.assertEqual(len(claimant_notifs), 1)
        self.assertEqual(claimant_notifs[0].type, "CLAIM_APPROVED")
        self.assertIn("Approved", claimant_notifs[0].title)


class TestNotificationDialogGUI(unittest.TestCase):
    """Test suite verifying GUI dialog creation and rendering."""

    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError:
            self.skipTest("Tkinter display not available in current test environment.")

        self.test_db = os.path.join(os.path.dirname(__file__), "test_gui_notif.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        conn = sqlite3.connect(self.test_db)
        conn.execute("PRAGMA foreign_keys = ON;")
        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

        self.user_repo = UserRepository(self.test_db)
        self.notif_repo = NotificationRepository(self.test_db)
        self.notif_service = NotificationService(notif_repo=self.notif_repo, db_path=self.test_db)

        self.test_user = User(
            id=None,
            username="gui_notif_user",
            password_hash="pwd",
            salt="salt",
            full_name="GUI User",
            email="gui@campus.edu",
            role="student",
        )
        self.test_user.id = self.user_repo.create(self.test_user)

        # Seed 1 notification
        self.notif_service.notify(
            user_id=self.test_user.id,
            title="GUI Test Notification",
            message="This is a test notification for the dialog test.",
            notif_type="SYSTEM",
        )

    def tearDown(self) -> None:
        if hasattr(self, "root") and self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                pass

    def test_notification_dialog_initialization(self) -> None:
        dialog = NotificationCenterDialog(
            parent=self.root,
            user_id=self.test_user.id,
            db_path=self.test_db,
        )
        self.assertIsNotNone(dialog)
        self.assertEqual(dialog.user_id, self.test_user.id)
        # Verify notifications loaded in tree
        children = dialog.tree.get_children()
        self.assertEqual(len(children), 1)
        dialog.destroy()


if __name__ == "__main__":
    unittest.main()
