"""
CampusConnect: Notification Domain Model
Represents in-app notification alerts for match discoveries, claim submissions,
and administrative verification decisions.
"""

from dataclasses import dataclass
from typing import Optional


VALID_NOTIFICATION_TYPES = {
    "MATCH_FOUND",
    "CLAIM_SUBMITTED",
    "CLAIM_APPROVED",
    "CLAIM_REJECTED",
    "SYSTEM",
}


@dataclass
class Notification:
    """Domain model representing a user notification message."""
    id: Optional[int]
    user_id: int
    title: str
    message: str
    type: str = "SYSTEM"
    related_item_id: Optional[int] = None
    is_read: bool = False
    created_at: Optional[str] = None

    def validate(self) -> None:
        """Validate notification domain invariants."""
        if not self.user_id or self.user_id <= 0:
            raise ValueError("Notification must reference a valid user_id.")
        if not self.title or len(self.title.strip()) < 3:
            raise ValueError("Notification title must be at least 3 characters long.")
        if not self.message or len(self.message.strip()) < 5:
            raise ValueError("Notification message must be at least 5 characters long.")
        if self.type not in VALID_NOTIFICATION_TYPES:
            raise ValueError(f"Invalid notification type '{self.type}'. Must be one of {VALID_NOTIFICATION_TYPES}")
