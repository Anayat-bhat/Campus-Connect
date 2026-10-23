"""
CampusConnect: Database Connection & Initialization Manager

Handles SQLite database connections, foreign key enforcement, schema initialization,
and transaction context management.
"""

import os
import sqlite3
import hashlib
import secrets
from contextlib import contextmanager
from typing import Generator, Optional


# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "campus_connect.db")
DEFAULT_SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Establish and return a configured SQLite connection.

    Enforces foreign key constraints and configures dictionary-like row access.
    """
    target_path = db_path if db_path is not None else DEFAULT_DB_PATH

    # Ensure parent directory exists for file-based databases
    if target_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)

    conn = sqlite3.connect(target_path)
    # Enable foreign key constraint checking (disabled by default in SQLite)
    conn.execute("PRAGMA foreign_keys = ON;")
    # Return rows as dictionary-accessible Row objects
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_cursor(db_path: Optional[str] = None) -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager providing a database cursor with automatic transaction management.

    Commits on success; automatically rolls back on exception.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def init_database(db_path: Optional[str] = None, schema_path: Optional[str] = None) -> None:
    """
    Initialize all database tables, constraints, and indexes from schema.sql.
    """
    target_schema = schema_path if schema_path is not None else DEFAULT_SCHEMA_PATH
    if not os.path.exists(target_schema):
        raise FileNotFoundError(f"Schema DDL file not found at {target_schema}")

    with open(target_schema, "r", encoding="utf-8") as schema_file:
        ddl_script = schema_file.read()

    conn = get_connection(db_path)
    try:
        with conn:
            conn.executescript(ddl_script)
    finally:
        conn.close()


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password securely using PBKDF2-HMAC-SHA256 from the standard library.

    Returns:
        tuple[str, str]: (hex_password_hash, hex_salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000
    )
    return key.hex(), salt


def seed_default_admin(
    db_path: Optional[str] = None,
    username: str = "admin",
    password: str = "Admin@Campus2026",
    full_name: str = "Campus Administrator",
    email: str = "admin@campusconnect.edu"
) -> bool:
    """
    Safely seed a local administrator account if none currently exists.

    Returns:
        bool: True if created, False if an admin account already exists.
    """
    pw_hash, salt = hash_password(password)

    with get_db_cursor(db_path) as cursor:
        cursor.execute("SELECT id FROM users WHERE username = ? OR role = 'admin'", (username,))
        existing = cursor.fetchone()
        if existing:
            return False

        cursor.execute(
            """
            INSERT INTO users (username, password_hash, salt, full_name, email, role)
            VALUES (?, ?, ?, ?, ?, 'admin')
            """,
            (username, pw_hash, salt, full_name, email)
        )
        return True


if __name__ == "__main__":
    print(f"Initializing CampusConnect database at: {DEFAULT_DB_PATH}")
    init_database()
    created = seed_default_admin()
    if created:
        print("Default administrator account initialized (username: 'admin').")
    else:
        print("Admin user already exists. Skipped seeding.")
    print("Database initialization complete.")
