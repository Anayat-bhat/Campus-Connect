"""
Phase 9: End-to-End System Integration & Edge-Case Hardening Test Suite
Simulates the entire multi-user campus lost-and-found lifecycle:
Registration -> Login -> Reporting -> Algorithmic Matching -> Claim Submission ->
Admin Handover Approval -> Audit Receipt Verification -> Safe Deletion Invariants ->
Analytics Verification -> Edge Case Stress Testing.
"""

import os
import sqlite3
import unittest

from database.connection import DEFAULT_SCHEMA_PATH, seed_default_admin
from database.repository import UserRepository, ItemRepository, ClaimRepository
from services.auth_service import AuthService, RegistrationError
from services.session_manager import SessionManager, AuthenticationError, AuthorizationError
from services.matching_service import MatchingService
from services.claim_service import ClaimService, ClaimWorkflowError
from analytics.metrics import AnalyticsMetrics


class TestEndToEndSystemIntegration(unittest.TestCase):
    """Full lifecycle integration and edge-case hardening test suite."""

    def setUp(self) -> None:
        self.test_db = os.path.join(os.path.dirname(__file__), "test_e2e.db")
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
        self.session = SessionManager()
        self.auth = AuthService(user_repo=self.user_repo, session=self.session)
        self.matcher = MatchingService(item_repo=self.item_repo)
        self.claim_service = ClaimService(
            item_repo=self.item_repo,
            claim_repo=self.claim_repo,
            user_repo=self.user_repo,
            db_path=self.test_db
        )
        self.analytics = AnalyticsMetrics(self.test_db)

    def tearDown(self) -> None:
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_complete_campus_lifecycle(self) -> None:
        """Execute complete multi-actor user story across all subsystems."""
        # 1. Student A registers and reports a LOST item
        student_a = self.auth.register_user(
            username="aravind_nair",
            password="Aravind@2026",
            full_name="Aravind Nair",
            email="aravind@campus.edu",
            role="student"
        )
        self.auth.login("aravind_nair", "Aravind@2026")
        self.assertTrue(self.session.is_authenticated())

        from models.item import Item
        lost_item = Item(
            id=None,
            type="LOST",
            user_id=student_a.id,
            title="Brown Tommy Hilfiger Leather Wallet",
            category="Personal belongings",
            description="Lost brown leather bi-fold wallet containing college ID and metro pass.",
            event_date="2026-10-25",
            location="Student Center Cafeteria",
            image_path=None,
            status="OPEN"
        )
        lost_id = self.item_repo.create(lost_item)
        lost_item.id = lost_id
        self.auth.logout()

        # 2. Student B registers and reports a FOUND item
        student_b = self.auth.register_user(
            username="kavya_menon",
            password="KavyaPass2026",
            full_name="Kavya Menon",
            email="kavya@campus.edu",
            role="student"
        )
        self.auth.login("kavya_menon", "KavyaPass2026")

        found_item = Item(
            id=None,
            type="FOUND",
            user_id=student_b.id,
            title="Found Tommy Hilfiger Brown Wallet",
            category="Personal belongings",
            description="Found a brown bi-fold wallet on cafeteria table after lunch.",
            event_date="2026-10-25",
            location="Cafeteria",
            image_path=None,
            status="OPEN"
        )
        found_id = self.item_repo.create(found_item)
        found_item.id = found_id
        self.auth.logout()

        # 3. Algorithmic matching correlates the reports
        matches = self.matcher.find_matches_for_item(lost_item, min_threshold=40.0)
        self.assertGreaterEqual(len(matches), 1)
        top_match = matches[0]
        self.assertEqual(top_match.target_item.id, found_id)
        self.assertGreater(top_match.overall_score, 70.0)
        self.assertIn("Identical category", top_match.explanation)

        # 4. Student A signs in and files an ownership claim on the found wallet
        self.auth.login("aravind_nair", "Aravind@2026")
        claim = self.claim_service.submit_claim(
            item_id=found_id,
            claimant_id=student_a.id,
            proof_description="Inside zipper has a silver lucky coin and metro card ending in 4102."
        )
        self.assertEqual(claim.status, "PENDING")

        # Verify item status transitioned to CLAIM_PENDING
        self.assertEqual(self.item_repo.get_by_id(found_id).status, "CLAIM_PENDING")
        self.auth.logout()

        # 5. Admin reviews pending claim and executes handover
        admin = self.auth.login("admin", "Admin@Campus2026")
        self.assertTrue(self.session.is_admin())

        pending_queue = self.claim_service.list_pending_claims_for_review()
        self.assertEqual(len(pending_queue), 1)
        self.assertEqual(pending_queue[0]["claimant_name"], "Aravind Nair")

        # Admin approves claim
        handover_success = self.claim_service.approve_claim(
            claim_id=claim.id,
            reviewer_id=admin.id,
            verification_notes="Claimant showed matching metro card and ID at campus security desk."
        )
        self.assertTrue(handover_success)

        # 6. Verify item is RETURNED and audit trail is sealed
        updated_found = self.item_repo.get_by_id(found_id)
        self.assertEqual(updated_found.status, "RETURNED")

        receipt = self.claim_service.get_return_record(found_id)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["received_name"], "Aravind Nair")
        self.assertEqual(receipt["handed_over_name"], "Campus Administrator")

        # 7. Safe Deletion Invariant: Prevent deleting RETURNED item records
        with self.assertRaises(ValueError) as ctx:
            self.item_repo.delete(found_id, requesting_user_id=admin.id, is_admin=True)
        self.assertIn("cannot delete", str(ctx.exception).lower())

        # 8. Verify Analytics reflects updated state
        kpis = self.analytics.get_summary_kpis()
        self.assertEqual(kpis["total_items"], 2)
        self.assertEqual(kpis["lost_items"], 1)
        self.assertEqual(kpis["found_items"], 1)
        self.assertEqual(kpis["returned_items"], 1)
        self.assertEqual(kpis["recovery_rate"], 100.0)

    def test_sql_injection_resilience(self) -> None:
        """Verify parameterized queries prevent SQL injection payloads."""
        sql_payload = "' OR '1'='1' --"
        results = self.item_repo.list_items(keyword=sql_payload)
        self.assertEqual(len(results), 0)

        count = self.item_repo.count_items(keyword=sql_payload)
        self.assertEqual(count, 0)

        # Malicious username in authentication
        with self.assertRaises(AuthenticationError):
            self.auth.login("admin' OR '1'='1", "any_password")

    def test_unicode_and_special_character_resilience(self) -> None:
        """Verify system handles Unicode, Hindi characters, and symbols without crashing."""
        user = self.auth.register_user(
            username="student_unicode",
            password="ValidPass123",
            full_name="राहुल शर्मा (Rahul)",
            email="rahul.intl@campus.edu"
        )
        self.assertEqual(user.full_name, "राहुल शर्मा (Rahul)")

        from models.item import Item
        item = Item(
            id=None,
            type="LOST",
            user_id=user.id,
            title="HP Pavilion 15\" Laptop (Silver) — ⚡ Charger & Pen",
            category="Electronics",
            description="Left in Room #104. 'Special quotes', <tags>, and &symbols inside.",
            event_date="2026-10-25",
            location="Room #104 & Lab-B",
            image_path=None,
            status="OPEN"
        )
        item_id = self.item_repo.create(item)
        fetched = self.item_repo.get_by_id(item_id)
        self.assertIn("⚡", fetched.title)
        self.assertIn("<tags>", fetched.description)


if __name__ == "__main__":
    unittest.main()
