"""
CampusConnect: Claims & Return Handover Service
Manages student ownership claims, verification workflows, and atomic
handover transitions with ACID database transactions.
"""

import sqlite3
from typing import Optional, List, Dict, Any
from database.connection import get_connection, get_db_cursor
from database.repository import ItemRepository, ClaimRepository, UserRepository
from models.claim import Claim
from models.item import Item
from models.user import User


class ClaimWorkflowError(Exception):
    """Raised when a business rule or invariant of the claim workflow is violated."""
    pass


class ClaimService:
    """Service orchestrating claim submissions, reviews, and item return transactions."""

    def __init__(
        self,
        item_repo: Optional[ItemRepository] = None,
        claim_repo: Optional[ClaimRepository] = None,
        user_repo: Optional[UserRepository] = None,
        db_path: Optional[str] = None
    ) -> None:
        self.db_path = db_path
        self.item_repo = item_repo if item_repo is not None else ItemRepository(db_path)
        self.claim_repo = claim_repo if claim_repo is not None else ClaimRepository(db_path)
        self.user_repo = user_repo if user_repo is not None else UserRepository(db_path)

    def submit_claim(self, item_id: int, claimant_id: int, proof_description: str) -> Claim:
        """
        Validate and submit an ownership claim against a FOUND item.
        Transitions item status to CLAIM_PENDING atomically.
        """
        clean_proof = proof_description.strip() if proof_description else ""
        if len(clean_proof) < 5:
            raise ClaimWorkflowError("Proof description must be at least 5 characters long.")

        item = self.item_repo.get_by_id(item_id)
        if not item:
            raise ClaimWorkflowError(f"Item #{item_id} does not exist.")

        if item.type != "FOUND":
            raise ClaimWorkflowError("Claims can only be filed against FOUND items.")

        if item.status == "RETURNED":
            raise ClaimWorkflowError("This item has already been returned to its owner.")

        if item.user_id == claimant_id:
            raise ClaimWorkflowError("You cannot submit an ownership claim on an item you reported as found.")

        # Check if user already has an active pending claim for this item
        existing_claims = self.claim_repo.list_by_item(item_id)
        for existing in existing_claims:
            if existing.claimant_id == claimant_id and existing.status == "PENDING":
                raise ClaimWorkflowError("You already have a pending claim under review for this item.")

        claim = Claim(
            id=None,
            item_id=item_id,
            claimant_id=claimant_id,
            proof_description=clean_proof,
            status="PENDING"
        )

        claim_id = self.claim_repo.create(claim)
        claim.id = claim_id
        return claim

    def approve_claim(
        self,
        claim_id: int,
        reviewer_id: int,
        verification_notes: Optional[str] = None
    ) -> bool:
        """
        Approve an ownership claim and record handover in an atomic ACID transaction:
        1. Mark claim as APPROVED.
        2. Reject all other competing pending claims for the item.
        3. Mark item status as RETURNED.
        4. Insert immutable handover record into item_returns.
        """
        with get_db_cursor(self.db_path) as cursor:
            # 1. Inspect claim
            cursor.execute(
                "SELECT id, item_id, claimant_id, status FROM claims WHERE id = ?",
                (claim_id,)
            )
            claim_row = cursor.fetchone()
            if not claim_row:
                raise ClaimWorkflowError(f"Claim #{claim_id} not found.")

            if claim_row["status"] != "PENDING":
                raise ClaimWorkflowError(f"Cannot approve claim in '{claim_row['status']}' state.")

            item_id = claim_row["item_id"]
            claimant_id = claim_row["claimant_id"]

            # 2. Inspect item
            cursor.execute("SELECT id, status FROM items WHERE id = ?", (item_id,))
            item_row = cursor.fetchone()
            if not item_row:
                raise ClaimWorkflowError(f"Target item #{item_id} does not exist.")
            if item_row["status"] == "RETURNED":
                raise ClaimWorkflowError(f"Item #{item_id} has already been returned.")

            # 3. Update current claim to APPROVED
            cursor.execute(
                """
                UPDATE claims
                SET status = 'APPROVED',
                    reviewed_at = datetime('now', 'localtime'),
                    reviewed_by = ?,
                    review_notes = ?
                WHERE id = ?
                """,
                (reviewer_id, verification_notes, claim_id)
            )

            # 4. Reject competing pending claims for the same item
            cursor.execute(
                """
                UPDATE claims
                SET status = 'REJECTED',
                    reviewed_at = datetime('now', 'localtime'),
                    reviewed_by = ?,
                    review_notes = 'Another claim was verified and approved.'
                WHERE item_id = ? AND id != ? AND status = 'PENDING'
                """,
                (reviewer_id, item_id, claim_id)
            )

            # 5. Transition item status to RETURNED
            cursor.execute(
                "UPDATE items SET status = 'RETURNED' WHERE id = ?",
                (item_id,)
            )

            # 6. Insert audit return handover record
            cursor.execute(
                """
                INSERT INTO item_returns (item_id, claim_id, handed_over_by, received_by, verification_notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_id, claim_id, reviewer_id, claimant_id, verification_notes)
            )

            return True

    def reject_claim(
        self,
        claim_id: int,
        reviewer_id: int,
        reason: Optional[str] = None
    ) -> bool:
        """
        Reject an ownership claim:
        1. Set claim status to REJECTED.
        2. If no remaining PENDING claims exist for the item, revert item status to OPEN.
        """
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("SELECT id, item_id, status FROM claims WHERE id = ?", (claim_id,))
            claim_row = cursor.fetchone()
            if not claim_row:
                raise ClaimWorkflowError(f"Claim #{claim_id} not found.")

            if claim_row["status"] != "PENDING":
                raise ClaimWorkflowError(f"Cannot reject claim in '{claim_row['status']}' state.")

            item_id = claim_row["item_id"]

            # Update claim to REJECTED
            cursor.execute(
                """
                UPDATE claims
                SET status = 'REJECTED',
                    reviewed_at = datetime('now', 'localtime'),
                    reviewed_by = ?,
                    review_notes = ?
                WHERE id = ?
                """,
                (reviewer_id, reason, claim_id)
            )

            # Check for remaining pending claims on this item
            cursor.execute(
                "SELECT COUNT(*) as count FROM claims WHERE item_id = ? AND status = 'PENDING'",
                (item_id,)
            )
            count_row = cursor.fetchone()
            pending_count = count_row["count"] if count_row else 0

            # If no more pending claims, reset item to OPEN so other students can claim it
            if pending_count == 0:
                cursor.execute(
                    "UPDATE items SET status = 'OPEN' WHERE id = ? AND status = 'CLAIM_PENDING'",
                    (item_id,)
                )

            return True

    def get_return_record(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Fetch audit return receipt for a returned item."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT r.id, r.item_id, r.claim_id, r.return_date, r.verification_notes,
                       h.full_name as handed_over_name, h.email as handed_over_email,
                       rec.full_name as received_name, rec.email as received_email
                FROM item_returns r
                JOIN users h ON r.handed_over_by = h.id
                JOIN users rec ON r.received_by = rec.id
                WHERE r.item_id = ?
                """,
                (item_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)
        finally:
            conn.close()

    def list_pending_claims_for_review(self) -> List[Dict[str, Any]]:
        """List all pending claims across the campus with full item and claimant context."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT c.id as claim_id, c.item_id, c.claimant_id, c.proof_description,
                       c.status, c.submitted_at,
                       i.title as item_title, i.category as item_category, i.location as item_location,
                       u.full_name as claimant_name, u.email as claimant_email
                FROM claims c
                JOIN items i ON c.item_id = i.id
                JOIN users u ON c.claimant_id = u.id
                WHERE c.status = 'PENDING'
                ORDER BY c.id DESC
                """
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
