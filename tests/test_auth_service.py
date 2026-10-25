"""
Unit Tests for Phase 4: Authentication Service, Session Manager & Role Protection
Verifies registration, password hashing/validation, session state, and RBAC guards.
"""

import os
import sqlite3
import unittest

from database.connection import DEFAULT_SCHEMA_PATH, seed_default_admin
from database.repository import UserRepository
from models.user import User
from services.auth_service import AuthService, RegistrationError
from services.session_manager import (
    SessionManager,
    AuthenticationError,
    AuthorizationError,
    require_auth,
    require_role,
    require_admin,
)


class TestAuthAndSession(unittest.TestCase):
    """Test suite for AuthService, SessionManager, and RBAC decorators."""

    def setUp(self) -> None:
        self.test_db = os.path.join(os.path.dirname(__file__), "test_auth.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        conn = sqlite3.connect(self.test_db)
        conn.execute("PRAGMA foreign_keys = ON;")
        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

        # Seed default admin
        seed_default_admin(self.test_db)

        self.user_repo = UserRepository(self.test_db)
        self.session = SessionManager()
        self.auth_service = AuthService(user_repo=self.user_repo, session=self.session)

    def tearDown(self) -> None:
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_register_user_success(self) -> None:
        """Verify successful student registration."""
        user = self.auth_service.register_user(
            username="priya_sharma",
            password="Password123",
            full_name="Priya Sharma",
            email="priya@campus.edu",
            role="student"
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(user.username, "priya_sharma")
        self.assertEqual(user.role, "student")
        self.assertNotEqual(user.password_hash, "Password123")
        self.assertTrue(len(user.salt) >= 16)

    def test_register_duplicate_username_fails(self) -> None:
        """Verify duplicate username raises RegistrationError."""
        self.auth_service.register_user(
            username="priya_sharma",
            password="Password123",
            full_name="Priya Sharma",
            email="priya@campus.edu"
        )
        with self.assertRaises(RegistrationError) as ctx:
            self.auth_service.register_user(
                username="priya_sharma",
                password="DifferentPass1",
                full_name="Priya Clone",
                email="different@campus.edu"
            )
        self.assertIn("already taken", str(ctx.exception))

    def test_register_duplicate_email_fails(self) -> None:
        """Verify duplicate email raises RegistrationError."""
        self.auth_service.register_user(
            username="user_one",
            password="Password123",
            full_name="User One",
            email="shared@campus.edu"
        )
        with self.assertRaises(RegistrationError) as ctx:
            self.auth_service.register_user(
                username="user_two",
                password="Password123",
                full_name="User Two",
                email="shared@campus.edu"
            )
        self.assertIn("already registered", str(ctx.exception))

    def test_password_strength_validation(self) -> None:
        """Verify short or invalid passwords raise RegistrationError."""
        with self.assertRaises(RegistrationError):
            self.auth_service.register_user(
                username="valid_user",
                password="123",  # Under 6 chars
                full_name="Valid Name",
                email="valid@campus.edu"
            )

        with self.assertRaises(RegistrationError):
            self.auth_service.register_user(
                username="valid_user2",
                password="  pass123  ",  # Leading/trailing whitespace
                full_name="Valid Name",
                email="valid2@campus.edu"
            )

    def test_authenticate_and_login_by_username(self) -> None:
        """Verify login using username."""
        self.auth_service.register_user(
            username="arjun_k",
            password="SecurePass2026",
            full_name="Arjun Kapoor",
            email="arjun@campus.edu"
        )

        user = self.auth_service.login("arjun_k", "SecurePass2026")
        self.assertEqual(user.username, "arjun_k")
        self.assertTrue(self.session.is_authenticated())
        self.assertFalse(self.session.is_admin())
        self.assertEqual(self.session.current_user.id, user.id)

    def test_authenticate_and_login_by_email(self) -> None:
        """Verify login using email address."""
        self.auth_service.register_user(
            username="sneha_p",
            password="SecurePass2026",
            full_name="Sneha Patel",
            email="sneha@campus.edu"
        )

        user = self.auth_service.login("sneha@campus.edu", "SecurePass2026")
        self.assertEqual(user.username, "sneha_p")
        self.assertTrue(self.session.is_authenticated())

    def test_login_invalid_password_fails(self) -> None:
        """Verify incorrect password raises AuthenticationError."""
        self.auth_service.register_user(
            username="amit_v",
            password="CorrectPass1",
            full_name="Amit Verma",
            email="amit@campus.edu"
        )
        with self.assertRaises(AuthenticationError):
            self.auth_service.login("amit_v", "WrongPassword")

    def test_login_nonexistent_user_fails(self) -> None:
        """Verify login with non-existent user raises AuthenticationError."""
        with self.assertRaises(AuthenticationError):
            self.auth_service.login("ghost_user", "AnyPassword123")

    def test_admin_login_and_privileges(self) -> None:
        """Verify seeded admin login and admin flag."""
        admin = self.auth_service.login("admin", "Admin@Campus2026")
        self.assertTrue(self.session.is_authenticated())
        self.assertTrue(self.session.is_admin())
        self.assertTrue(self.session.has_role("admin"))
        self.assertFalse(self.session.has_role("student"))
        self.assertEqual(admin.role, "admin")

    def test_session_logout(self) -> None:
        """Verify logout clears session state."""
        self.auth_service.login("admin", "Admin@Campus2026")
        self.assertTrue(self.session.is_authenticated())
        self.auth_service.logout()
        self.assertFalse(self.session.is_authenticated())
        self.assertIsNone(self.session.current_user)

    def test_role_protection_decorators(self) -> None:
        """Verify @require_auth and @require_role decorators."""
        session = SessionManager()

        @require_auth(session=session)
        def protected_view() -> str:
            return "accessed"

        @require_admin(session=session)
        def admin_view() -> str:
            return "admin_ok"

        # Not authenticated: both fail
        with self.assertRaises(AuthenticationError):
            protected_view()

        with self.assertRaises(AuthenticationError):
            admin_view()

        # Login as student
        student = User(
            id=10,
            username="student1",
            password_hash="h",
            salt="s",
            full_name="Student One",
            email="s1@campus.edu",
            role="student"
        )
        session.login(student)

        # Student can access general protected_view
        self.assertEqual(protected_view(), "accessed")
        # Student cannot access admin_view
        with self.assertRaises(AuthorizationError):
            admin_view()

        # Switch to admin
        admin = User(
            id=1,
            username="admin",
            password_hash="h",
            salt="s",
            full_name="Administrator",
            email="admin@campus.edu",
            role="admin"
        )
        session.login(admin)
        self.assertEqual(admin_view(), "admin_ok")

    def test_change_password(self) -> None:
        """Verify user password change flow."""
        user = self.auth_service.register_user(
            username="rohit_m",
            password="OldPassword123",
            full_name="Rohit Mehra",
            email="rohit@campus.edu"
        )

        # Attempt with incorrect old password
        with self.assertRaises(AuthenticationError):
            self.auth_service.change_password(user.id, "WrongOldPass", "NewPassword456")

        # Attempt with weak new password
        with self.assertRaises(RegistrationError):
            self.auth_service.change_password(user.id, "OldPassword123", "short")

        # Success case
        success = self.auth_service.change_password(user.id, "OldPassword123", "NewPassword456")
        self.assertTrue(success)

        # Verify old password no longer works
        with self.assertRaises(AuthenticationError):
            self.auth_service.login("rohit_m", "OldPassword123")

        # Verify new password works
        new_login = self.auth_service.login("rohit_m", "NewPassword456")
        self.assertEqual(new_login.username, "rohit_m")

    def test_admin_reset_password(self) -> None:
        """Verify admin can reset another user's password."""
        admin = self.user_repo.get_by_username("admin")
        student = self.auth_service.register_user(
            username="kavita_s",
            password="OriginalPassword",
            full_name="Kavita Singh",
            email="kavita@campus.edu"
        )

        # Student cannot reset passwords
        with self.assertRaises(AuthorizationError):
            self.auth_service.admin_reset_password(student.id, student.id, "NewPassAdmin")

        # Admin can reset password
        self.auth_service.admin_reset_password(admin.id, student.id, "ResetByAdmin123")
        login_student = self.auth_service.login("kavita_s", "ResetByAdmin123")
        self.assertEqual(login_student.id, student.id)


if __name__ == "__main__":
    unittest.main()
