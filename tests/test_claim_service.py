"""
Unit Tests for Phase 7: Claims & Return Handover Service with ACID Transactions
Verifies claim submission validation, state transitions, atomic approval/rejection,
competing claim handling, and return audit logging.
"""

import os
import sqlite3
import unittest

from database.connection import DEFAULT_SCHEMA_PATH, seed_default_admin
from database.repository import UserRepository, ItemRepository, ClaimRepository
from models.user import User
from models.item import Item
from models.claim import Claim
from services.claim_service import ClaimService, ClaimWorkflowError
from services.auth_service import AuthService


class TestClaimService(unittest.TestCase):
    """Test suite for Phase 7 ClaimService and handover transactions."""

    def setUp(self) -> None:
        self.test_db = os.path.join(os.path.dirname(__file__), "test_claims.db")
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
        self.auth_service = AuthService(user_repo=self.user_repo)
        self.claim_service = ClaimService(
            item_repo=self.item_repo,
            claim_repo=self.claim_repo,
            user_repo=self.user_repo,
            db_path=self.test_db
        )

        self.admin = self.user_repo.get_by_username("admin")

        # Create two test students: finder and claimant
        self.finder = self.auth_service.register_user(
            username="student_finder",
            password="FinderPass123",
            full_name="Aman Finder",
            email="finder@campus.edu"
        )
        self.claimant1 = self.auth_service.register_user(
            username="student_claimant1",
            password="ClaimantPass123",
            full_name="Neha Claimant",
            email="neha@campus.edu"
        )
        self.claimant2 = self.auth_service.register_user(
            username="student_claimant2",
            password="ClaimantPass456",
            full_name="Vikas Claimant",
            email="vikas@campus.edu"
        )

        # Create a sample FOUND item
        self.found_item = Item(
            id=None,
            type="FOUND",
            user_id=self.finder.id,
            title="Scientific Calculator fx-991EX",
            category="Electronics",
            description="Found in Engineering Block Room 204 under desk.",
            event_date="2026-10-25",
            location="Engg Block Room 204",
            image_path=None,
            status="OPEN"
        )
        self.found_item.id = self.item_repo.create(self.found_item)

    def tearDown(self) -> None:
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_submit_claim_success(self) -> None:
        """Verify successful claim submission transitions item to CLAIM_PENDING."""
        claim = self.claim_service.submit_claim(
            item_id=self.found_item.id,
            claimant_id=self.claimant1.id,
            proof_description="It has a silver spider-man sticker on the back cover."
        )
        self.assertIsNotNone(claim.id)
        self.assertEqual(claim.status, "PENDING")

        # Verify item status updated to CLAIM_PENDING
        updated_item = self.item_repo.get_by_id(self.found_item.id)
        self.assertEqual(updated_item.status, "CLAIM_PENDING")

    def test_submit_claim_validation_failures(self) -> None:
        """Verify proof length, finder claiming own item, and duplicate claim rejections."""
        # Short proof
        with self.assertRaises(ClaimWorkflowError):
            self.claim_service.submit_claim(self.found_item.id, self.claimant1.id, "abc")

        # Finder cannot claim their own found report
        with self.assertRaises(ClaimWorkflowError):
            self.claim_service.submit_claim(self.found_item.id, self.finder.id, "Valid proof description here.")

        # Successfully submit first claim
        self.claim_service.submit_claim(
            self.found_item.id,
            self.claimant1.id,
            "Valid distinguishing proof description."
        )

        # Duplicate pending claim by same claimant
        with self.assertRaises(ClaimWorkflowError):
            self.claim_service.submit_claim(
                self.found_item.id,
                self.claimant1.id,
                "Another proof description from same user."
            )

    def test_approve_claim_atomic_handover(self) -> None:
        """Verify atomic handover: approves claim, rejects competitors, marks item RETURNED, records return."""
        # Claimant 1 and Claimant 2 both claim the item
        claim1 = self.claim_service.submit_claim(
            self.found_item.id,
            self.claimant1.id,
            "Silver spider sticker and battery cover has tape."
        )
        claim2 = self.claim_service.submit_claim(
            self.found_item.id,
            self.claimant2.id,
            "Has white tape on back."
        )

        # Admin approves claim1
        success = self.claim_service.approve_claim(
            claim_id=claim1.id,
            reviewer_id=self.admin.id,
            verification_notes="Claimant showed matching college sticker proof."
        )
        self.assertTrue(success)

        # Verify claim 1 is APPROVED
        c1 = self.claim_repo.get_by_id(claim1.id)
        self.assertEqual(c1.status, "APPROVED")
        self.assertEqual(c1.reviewed_by, self.admin.id)

        # Verify competing claim 2 is REJECTED
        c2 = self.claim_repo.get_by_id(claim2.id)
        self.assertEqual(c2.status, "REJECTED")

        # Verify item status transitioned to RETURNED
        item = self.item_repo.get_by_id(self.found_item.id)
        self.assertEqual(item.status, "RETURNED")

        # Verify audit handover record exists in item_returns
        record = self.claim_service.get_return_record(self.found_item.id)
        self.assertIsNotNone(record)
        self.assertEqual(record["claim_id"], claim1.id)
        self.assertEqual(record["received_name"], self.claimant1.full_name)

    def test_reject_claim_reverts_item_to_open(self) -> None:
        """Verify rejecting the only pending claim resets item status to OPEN."""
        claim = self.claim_service.submit_claim(
            self.found_item.id,
            self.claimant1.id,
            "My calculator has a red mark on it."
        )
        self.assertEqual(self.item_repo.get_by_id(self.found_item.id).status, "CLAIM_PENDING")

        # Admin rejects claim
        self.claim_service.reject_claim(
            claim_id=claim.id,
            reviewer_id=self.admin.id,
            reason="Item does not have any red mark."
        )

        c = self.claim_repo.get_by_id(claim.id)
        self.assertEqual(c.status, "REJECTED")

        # Item should be reverted to OPEN
        updated_item = self.item_repo.get_by_id(self.found_item.id)
        self.assertEqual(updated_item.status, "OPEN")

    def test_list_pending_claims_for_review(self) -> None:
        """Verify pending review queue query joins claimant and item fields."""
        self.claim_service.submit_claim(
            self.found_item.id,
            self.claimant1.id,
            "Detailed proof description of calculator."
        )
        queue = self.claim_service.list_pending_claims_for_review()
        self.assertEqual(len(queue), 1)
        item_data = queue[0]
        self.assertEqual(item_data["item_title"], "Scientific Calculator fx-991EX")
        self.assertEqual(item_data["claimant_name"], self.claimant1.full_name)


if __name__ == "__main__":
    unittest.main()
