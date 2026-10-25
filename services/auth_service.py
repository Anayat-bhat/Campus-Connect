"""
CampusConnect: Authentication & User Account Service
Handles secure registration, credential verification, session-aware login/logout,
password management, and password strength policies.
"""

from typing import Optional
from database.connection import hash_password
from database.repository import UserRepository
from models.user import User
from services.session_manager import (
    SessionManager,
    session_manager as default_session_manager,
    AuthenticationError,
    AuthorizationError,
)


class RegistrationError(Exception):
    """Raised when user registration validation or constraint fails."""
    pass


class AuthService:
    """Service providing authentication, registration, and credential operations."""

    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        session: Optional[SessionManager] = None
    ) -> None:
        self.user_repo = user_repo if user_repo is not None else UserRepository()
        self.session = session if session is not None else default_session_manager

    @staticmethod
    def validate_password_strength(password: str) -> None:
        """
        Validate password complexity.
        Requirements:
        - At least 6 characters long
        - Cannot be purely whitespace
        """
        if not password or len(password.strip()) < 6:
            raise RegistrationError("Password must be at least 6 characters long.")
        if password.strip() != password:
            raise RegistrationError("Password cannot begin or end with whitespace.")

    def register_user(
        self,
        username: str,
        password: str,
        full_name: str,
        email: str,
        role: str = "student"
    ) -> User:
        """
        Register a new user account with hashed credentials.
        Raises RegistrationError or ValueError if validations fail.
        """
        clean_username = username.strip() if username else ""
        clean_email = email.strip() if email else ""
        clean_full_name = full_name.strip() if full_name else ""

        # Validate password strength before database checks
        self.validate_password_strength(password)

        # Ensure uniqueness of username
        if self.user_repo.get_by_username(clean_username):
            raise RegistrationError(f"Username '{clean_username}' is already taken.")

        # Ensure uniqueness of email
        if self.user_repo.get_by_email(clean_email):
            raise RegistrationError(f"Email '{clean_email}' is already registered.")

        # Generate cryptographic PBKDF2 hash & salt
        pwd_hash, salt = hash_password(password)

        user = User(
            id=None,
            username=clean_username,
            password_hash=pwd_hash,
            salt=salt,
            full_name=clean_full_name,
            email=clean_email,
            role=role
        )

        try:
            user_id = self.user_repo.create(user)
            user.id = user_id
            return user
        except ValueError as err:
            raise RegistrationError(str(err)) from err

    def authenticate(self, username_or_email: str, password: str) -> User:
        """
        Verify credentials against database records.
        Supports lookup by either username or email address.
        Returns the authenticated User or raises AuthenticationError.
        """
        clean_identifier = username_or_email.strip() if username_or_email else ""
        if not clean_identifier or not password:
            raise AuthenticationError("Username/email and password are required.")

        user: Optional[User] = None
        if "@" in clean_identifier:
            user = self.user_repo.get_by_email(clean_identifier)
        else:
            user = self.user_repo.get_by_username(clean_identifier)

        # Fallback to checking username if email lookup was attempted or vice versa
        if not user:
            user = self.user_repo.get_by_username(clean_identifier) or self.user_repo.get_by_email(clean_identifier)

        if not user:
            raise AuthenticationError("Invalid username or password.")

        computed_hash, _ = hash_password(password, salt=user.salt)
        if computed_hash != user.password_hash:
            raise AuthenticationError("Invalid username or password.")

        return user

    def login(self, username_or_email: str, password: str) -> User:
        """
        Authenticate credentials and bind the user to the active session.
        """
        user = self.authenticate(username_or_email, password)
        self.session.login(user)
        return user

    def logout(self) -> None:
        """Clear active user session."""
        self.session.logout()

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Update user password after validating existing password.
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found.")

        old_hash, _ = hash_password(old_password, salt=user.salt)
        if old_hash != user.password_hash:
            raise AuthenticationError("Current password does not match.")

        self.validate_password_strength(new_password)
        new_hash, new_salt = hash_password(new_password)

        return self.user_repo.update_password(user_id, new_hash, new_salt)

    def admin_reset_password(self, admin_id: int, target_user_id: int, new_password: str) -> bool:
        """
        Administrative override allowing admins to reset any user password.
        """
        admin_user = self.user_repo.get_by_id(admin_id)
        if not admin_user or not admin_user.is_admin:
            raise AuthorizationError("Only administrators can perform administrative password resets.")

        target_user = self.user_repo.get_by_id(target_user_id)
        if not target_user:
            raise ValueError(f"Target user ID {target_user_id} not found.")

        self.validate_password_strength(new_password)
        new_hash, new_salt = hash_password(new_password)

        return self.user_repo.update_password(target_user_id, new_hash, new_salt)
