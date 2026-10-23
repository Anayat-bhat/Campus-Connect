"""
CampusConnect Database Package
"""

from database.connection import (
    DEFAULT_DB_PATH,
    DEFAULT_SCHEMA_PATH,
    get_connection,
    get_db_cursor,
    init_database,
    seed_default_admin,
    hash_password,
)

__all__ = [
    "DEFAULT_DB_PATH",
    "DEFAULT_SCHEMA_PATH",
    "get_connection",
    "get_db_cursor",
    "init_database",
    "seed_default_admin",
    "hash_password",
]
