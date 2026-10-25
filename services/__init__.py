"""
CampusConnect: Business Logic & Application Services Package
"""

from services.session_manager import (
    SessionManager,
    session_manager,
    AuthenticationError,
    AuthorizationError,
    require_auth,
    require_role,
    require_admin,
)
from services.auth_service import (
    AuthService,
    RegistrationError,
)
from services.matching_service import (
    MatchingService,
    MatchResult,
)

__all__ = [
    "SessionManager",
    "session_manager",
    "AuthenticationError",
    "AuthorizationError",
    "require_auth",
    "require_role",
    "require_admin",
    "AuthService",
    "RegistrationError",
    "MatchingService",
    "MatchResult",
]
