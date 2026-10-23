"""
CampusConnect: Claim Domain Model
Represents a student's verification claim on a found item.
"""

from dataclasses import dataclass
from typing import Optional


VALID_CLAIM_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


@dataclass
class Claim:
    """Domain model representing an ownership claim."""
    id: Optional[int]
    item_id: int
    claimant_id: int
    proof_description: str
    status: str = "PENDING"
    submitted_at: Optional[str] = None
    reviewed_at: Optional[str] = None
    reviewed_by: Optional[int] = None
    review_notes: Optional[str] = None

    def validate(self) -> None:
        """
        Validate claim domain constraints.
        Raises ValueError if attributes are invalid.
        """
        if not self.item_id or self.item_id <= 0:
            raise ValueError("Claim must reference a valid item_id.")

        if not self.claimant_id or self.claimant_id <= 0:
            raise ValueError("Claim must reference a valid claimant_id.")

        if not self.proof_description or len(self.proof_description.strip()) < 5:
            raise ValueError(
                "Proof description must be at least 5 characters long describing distinguishing features."
            )

        if self.status not in VALID_CLAIM_STATUSES:
            raise ValueError(
                f"Invalid claim status '{self.status}'. Must be one of {VALID_CLAIM_STATUSES}"
            )
