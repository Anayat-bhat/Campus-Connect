"""
CampusConnect: User Domain Model
Represents student and administrator entities with domain validation.
"""

from dataclasses import dataclass
import re
from typing import Optional


VALID_ROLES = {"student", "admin"}
EMAIL_REGEX = re.compile(r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$")


@dataclass
class User:
    """Domain model representing a campus user."""
    id: Optional[int]
    username: str
    password_hash: str
    salt: str
    full_name: str
    email: str
    role: str = "student"
    created_at: Optional[str] = None

    def validate(self) -> None:
        """
        Validate user domain invariants.
        Raises ValueError if attributes are invalid.
        """
        if not self.username or len(self.username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long.")

        if not re.match(r"^[a-zA-Z0-9_]+$", self.username):
            raise ValueError("Username can only contain alphanumeric characters and underscores.")

        if not self.full_name or len(self.full_name.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters long.")

        if not self.email or not EMAIL_REGEX.match(self.email.strip()):
            raise ValueError(f"Invalid email address: '{self.email}'.")

        if self.role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{self.role}'. Permitted roles are: {VALID_ROLES}")

        if not self.password_hash or not self.salt:
            raise ValueError("Password hash and salt must be present.")

    @property
    def is_admin(self) -> bool:
        """Check if user has administrative privileges."""
        return self.role == "admin"
