"""
CampusConnect: Item Domain Model
Represents lost and found reports with category definitions and validation rules.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


VALID_ITEM_TYPES = {"LOST", "FOUND"}

VALID_CATEGORIES = (
    "Electronics",
    "Books and stationery",
    "Identity cards",
    "Accessories",
    "Personal belongings",
    "Other",
)

VALID_STATUSES = {"OPEN", "CLAIM_PENDING", "RETURNED", "CLOSED"}


@dataclass
class Item:
    """Domain model representing an item reported as lost or found."""
    id: Optional[int]
    type: str
    user_id: int
    title: str
    category: str
    description: str
    event_date: str            # YYYY-MM-DD
    location: str
    image_path: Optional[str] = None
    status: str = "OPEN"
    created_at: Optional[str] = None

    def validate(self) -> None:
        """
        Validate item domain constraints.
        Raises ValueError if attributes are invalid.
        """
        if self.type not in VALID_ITEM_TYPES:
            raise ValueError(f"Invalid item type '{self.type}'. Must be one of {VALID_ITEM_TYPES}")

        if not self.user_id or self.user_id <= 0:
            raise ValueError("Item must be associated with a valid user_id.")

        if not self.title or len(self.title.strip()) < 2:
            raise ValueError("Item title must be at least 2 characters long.")

        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category '{self.category}'. Allowed categories: {list(VALID_CATEGORIES)}"
            )

        if not self.description or len(self.description.strip()) < 5:
            raise ValueError("Description must be at least 5 characters long to assist matching.")

        if not self.location or len(self.location.strip()) < 2:
            raise ValueError("Location must be specified (at least 2 characters).")

        # Validate event date is YYYY-MM-DD and not an impossible date
        try:
            datetime.strptime(self.event_date.strip(), "%Y-%m-%d")
        except (ValueError, TypeError):
            raise ValueError(
                f"Invalid event_date '{self.event_date}'. Date must follow YYYY-MM-DD format."
            )

        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{self.status}'. Must be one of {VALID_STATUSES}")

    @property
    def is_claimable(self) -> bool:
        """Check if item is in a state eligible for student claims."""
        return self.type == "FOUND" and self.status == "OPEN"

    @property
    def can_be_deleted(self) -> bool:
        """Reports can only be deleted if they are not already returned or under active claim."""
        return self.status in {"OPEN", "CLOSED"}
