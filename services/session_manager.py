"""
CampusConnect: Session Manager & Role Protection
Maintains in-memory session state for logged-in users and provides decorators
for role-based access control (RBAC).
"""

from functools import wraps
from typing import Optional, Callable, Any, Tuple
from datetime import datetime
from models.user import User


class AuthenticationError(Exception):
    """Raised when authentication fails or user is not logged in."""
    pass


class AuthorizationError(Exception):
    """Raised when user lacks required permissions or roles."""
    pass


class SessionManager:
    """
    Session manager maintaining active user session state.
    Designed for single-user desktop application session management.
    """

    def __init__(self) -> None:
        self._current_user: Optional[User] = None
        self._login_time: Optional[datetime] = None

    @property
    def current_user(self) -> Optional[User]:
        """Return the currently authenticated user or None."""
        return self._current_user

    @property
    def login_time(self) -> Optional[datetime]:
        """Return timestamp of login or None."""
        return self._login_time

    def login(self, user: User) -> None:
        """Set the authenticated user for the session."""
        if not isinstance(user, User):
            raise TypeError("Expected an instance of User.")
        self._current_user = user
        self._login_time = datetime.now()

    def logout(self) -> None:
        """Clear the current session state."""
        self._current_user = None
        self._login_time = None

    def is_authenticated(self) -> bool:
        """Check whether a user is currently logged in."""
        return self._current_user is not None

    def is_admin(self) -> bool:
        """Check if current user is logged in and has admin privileges."""
        return self._current_user is not None and self._current_user.is_admin

    def has_role(self, *roles: str) -> bool:
        """Check if the logged-in user possesses any of the specified roles."""
        if not self.is_authenticated() or not self._current_user:
            return False
        return self._current_user.role in roles


# Default global session singleton instance
session_manager = SessionManager()


def require_auth(session: Optional[SessionManager] = None) -> Callable:
    """
    Decorator that enforces user authentication before calling a function.
    Raises AuthenticationError if user is not logged in.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            active_session = session if session is not None else session_manager
            if not active_session.is_authenticated():
                raise AuthenticationError("Authentication required to access this resource.")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*required_roles: str, session: Optional[SessionManager] = None) -> Callable:
    """
    Decorator that enforces role membership.
    Raises AuthorizationError if user lacks any of the accepted roles.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            active_session = session if session is not None else session_manager
            if not active_session.is_authenticated():
                raise AuthenticationError("Authentication required before authorization check.")
            if not active_session.has_role(*required_roles):
                user_role = active_session.current_user.role if active_session.current_user else "unknown"
                raise AuthorizationError(
                    f"Access denied. User role '{user_role}' lacks required permissions: {required_roles}"
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin(session: Optional[SessionManager] = None) -> Callable:
    """Decorator convenience shorthand for requiring administrator role."""
    return require_role("admin", session=session)
