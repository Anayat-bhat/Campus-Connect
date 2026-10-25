"""
CampusConnect: Data Repository Layer
Provides complete CRUD operations, parameterized SQL queries, and pagination
for Users, Items, and Claims.
"""

import sqlite3
from typing import Optional, Tuple, List

from database.connection import get_connection, get_db_cursor
from models.user import User
from models.item import Item
from models.claim import Claim
from models.notification import Notification


class UserRepository:
    """Data access object for User entities."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path

    def create(self, user: User) -> int:
        """
        Validate and insert a new user into the database.
        Returns the inserted user's ID.
        """
        user.validate()
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, salt, full_name, email, role)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user.username, user.password_hash, user.salt, user.full_name, user.email, user.role)
            )
            return cursor.lastrowid

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch a single user by primary key ID."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash, salt, full_name, email, role, created_at FROM users WHERE id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
        finally:
            conn.close()

    def get_by_username(self, username: str) -> Optional[User]:
        """Fetch a user by unique username (case-insensitive search)."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash, salt, full_name, email, role, created_at FROM users WHERE LOWER(username) = LOWER(?)",
                (username.strip(),)
            )
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
        finally:
            conn.close()

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by unique email address."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash, salt, full_name, email, role, created_at FROM users WHERE LOWER(email) = LOWER(?)",
                (email.strip(),)
            )
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
        finally:
            conn.close()

    def list_all(self) -> List[User]:
        """List all registered users ordered by registration date."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, password_hash, salt, full_name, email, role, created_at FROM users ORDER BY id ASC"
            )
            return [self._row_to_user(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_profile(self, user_id: int, full_name: str, email: str) -> bool:
        """Update a user's full name and email."""
        if len(full_name.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters long.")
        if "@" not in email:
            raise ValueError("Invalid email format.")

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                "UPDATE users SET full_name = ?, email = ? WHERE id = ?",
                (full_name.strip(), email.strip(), user_id)
            )
            return cursor.rowcount > 0

    def update_password(self, user_id: int, password_hash: str, salt: str) -> bool:
        """Update a user's password hash and salt."""
        if not password_hash or not salt:
            raise ValueError("Password hash and salt cannot be empty.")
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                (password_hash, salt, user_id)
            )
            return cursor.rowcount > 0

    def delete(self, user_id: int) -> bool:
        """Delete a user account by primary key ID."""
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            salt=row["salt"],
            full_name=row["full_name"],
            email=row["email"],
            role=row["role"],
            created_at=row["created_at"]
        )


class ItemRepository:
    """Data access object for Item entities (Lost & Found reports)."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path

    def create(self, item: Item) -> int:
        """
        Validate and insert an item report.
        Returns the inserted item's ID.
        """
        item.validate()
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT INTO items (type, user_id, title, category, description, event_date, location, image_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.type,
                    item.user_id,
                    item.title.strip(),
                    item.category,
                    item.description.strip(),
                    item.event_date.strip(),
                    item.location.strip(),
                    item.image_path,
                    item.status
                )
            )
            return cursor.lastrowid

    def get_by_id(self, item_id: int) -> Optional[Item]:
        """Fetch an item by primary key ID."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, type, user_id, title, category, description, event_date, location, image_path, status, created_at
                FROM items WHERE id = ?
                """,
                (item_id,)
            )
            row = cursor.fetchone()
            return self._row_to_item(row) if row else None
        finally:
            conn.close()

    def list_items(
        self,
        item_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Item]:
        """
        Search and filter items with dynamic parameterized SQL and pagination.
        """
        conditions, params = self._build_filter_clause(
            item_type, category, status, location, keyword, start_date, end_date, user_id
        )

        query = """
            SELECT id, type, user_id, title, category, description, event_date, location, image_path, status, created_at
            FROM items
        """
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_item(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def list_by_user(self, user_id: int) -> List[Item]:
        """Fetch all items reported by a specific user."""
        return self.list_items(user_id=user_id, limit=500)

    def count_items(
        self,
        item_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        location: Optional[str] = None,
        keyword: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> int:
        """Count items matching search criteria (useful for pagination calculations)."""
        conditions, params = self._build_filter_clause(
            item_type, category, status, location, keyword, start_date, end_date, user_id
        )

        query = "SELECT COUNT(*) as count FROM items"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return row["count"] if row else 0
        finally:
            conn.close()

    def update(self, item: Item) -> bool:
        """Update mutable fields of an existing item."""
        if not item.id:
            raise ValueError("Item must have an ID to be updated.")
        item.validate()

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                UPDATE items
                SET title = ?, category = ?, description = ?, event_date = ?, location = ?, image_path = ?, status = ?
                WHERE id = ?
                """,
                (
                    item.title.strip(),
                    item.category,
                    item.description.strip(),
                    item.event_date.strip(),
                    item.location.strip(),
                    item.image_path,
                    item.status,
                    item.id
                )
            )
            return cursor.rowcount > 0

    def update_status(self, item_id: int, new_status: str) -> bool:
        """Update status of an item."""
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("UPDATE items SET status = ? WHERE id = ?", (new_status, item_id))
            return cursor.rowcount > 0

    def delete(
        self,
        item_id: int,
        requesting_user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> bool:
        """
        Delete an item report safely.
        Students can only delete their own reports; Admins can delete any report.
        Items that are RETURNED cannot be deleted to preserve the audit trail.
        """
        item = self.get_by_id(item_id)
        if not item:
            return False

        if not is_admin and requesting_user_id is not None and item.user_id != requesting_user_id:
            raise PermissionError("You do not have permission to delete this report.")

        if not item.can_be_deleted:
            raise ValueError(f"Cannot delete item with status '{item.status}'. Audit record must be preserved.")

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _build_filter_clause(
        item_type: Optional[str],
        category: Optional[str],
        status: Optional[str],
        location: Optional[str],
        keyword: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        user_id: Optional[int]
    ) -> Tuple[List[str], List]:
        conditions = []
        params = []

        if item_type:
            conditions.append("type = ?")
            params.append(item_type)

        if category:
            conditions.append("category = ?")
            params.append(category)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if location:
            conditions.append("location LIKE ?")
            params.append(f"%{location.strip()}%")

        if keyword:
            conditions.append("(title LIKE ? OR description LIKE ?)")
            kw = f"%{keyword.strip()}%"
            params.extend([kw, kw])

        if start_date:
            conditions.append("event_date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("event_date <= ?")
            params.append(end_date)

        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)

        return conditions, params

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> Item:
        return Item(
            id=row["id"],
            type=row["type"],
            user_id=row["user_id"],
            title=row["title"],
            category=row["category"],
            description=row["description"],
            event_date=row["event_date"],
            location=row["location"],
            image_path=row["image_path"],
            status=row["status"],
            created_at=row["created_at"]
        )


class ClaimRepository:
    """Data access object for Claim entities."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path

    def create(self, claim: Claim) -> int:
        """
        Validate and submit a claim on a found item.
        Automatically updates item status to 'CLAIM_PENDING' within the same transaction.
        """
        claim.validate()

        with get_db_cursor(self.db_path) as cursor:
            # Verify the item exists and is eligible
            cursor.execute("SELECT type, status FROM items WHERE id = ?", (claim.item_id,))
            item_row = cursor.fetchone()
            if not item_row:
                raise ValueError(f"Item ID {claim.item_id} does not exist.")
            if item_row["type"] != "FOUND":
                raise ValueError("Claims can only be filed against FOUND items.")
            if item_row["status"] == "RETURNED":
                raise ValueError("This item has already been claimed and returned.")

            # Insert claim
            cursor.execute(
                """
                INSERT INTO claims (item_id, claimant_id, proof_description, status)
                VALUES (?, ?, ?, ?)
                """,
                (claim.item_id, claim.claimant_id, claim.proof_description.strip(), claim.status)
            )
            claim_id = cursor.lastrowid

            # Update item status to CLAIM_PENDING
            cursor.execute("UPDATE items SET status = 'CLAIM_PENDING' WHERE id = ?", (claim.item_id,))
            return claim_id

    def get_by_id(self, claim_id: int) -> Optional[Claim]:
        """Fetch claim by primary key ID."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, item_id, claimant_id, proof_description, status, submitted_at, reviewed_at, reviewed_by, review_notes
                FROM claims WHERE id = ?
                """,
                (claim_id,)
            )
            row = cursor.fetchone()
            return self._row_to_claim(row) if row else None
        finally:
            conn.close()

    def list_by_item(self, item_id: int) -> List[Claim]:
        """List all claims filed for a specific item."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, item_id, claimant_id, proof_description, status, submitted_at, reviewed_at, reviewed_by, review_notes
                FROM claims WHERE item_id = ? ORDER BY id DESC
                """,
                (item_id,)
            )
            return [self._row_to_claim(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def list_by_claimant(self, claimant_id: int) -> List[Claim]:
        """List all claims submitted by a specific student."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, item_id, claimant_id, proof_description, status, submitted_at, reviewed_at, reviewed_by, review_notes
                FROM claims WHERE claimant_id = ? ORDER BY id DESC
                """,
                (claimant_id,)
            )
            return [self._row_to_claim(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def list_all(self, status: Optional[str] = None) -> List[Claim]:
        """List claims across the system, optionally filtered by status."""
        query = """
            SELECT id, item_id, claimant_id, proof_description, status, submitted_at, reviewed_at, reviewed_by, review_notes
            FROM claims
        """
        params = []
        if status:
            query += " WHERE status = ?"
            params.append(status)

        query += " ORDER BY id DESC"

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_claim(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_status(
        self,
        claim_id: int,
        status: str,
        reviewed_by: int,
        review_notes: Optional[str] = None
    ) -> bool:
        """Update claim status (APPROVED or REJECTED) along with reviewer audit information."""
        if status not in {"APPROVED", "REJECTED"}:
            raise ValueError("Status update must be either APPROVED or REJECTED.")

        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                UPDATE claims
                SET status = ?, reviewed_at = datetime('now', 'localtime'), reviewed_by = ?, review_notes = ?
                WHERE id = ?
                """,
                (status, reviewed_by, review_notes, claim_id)
            )
            return cursor.rowcount > 0

    def delete(self, claim_id: int) -> bool:
        """Delete a claim by primary key ID."""
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("DELETE FROM claims WHERE id = ?", (claim_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_claim(row: sqlite3.Row) -> Claim:
        return Claim(
            id=row["id"],
            item_id=row["item_id"],
            claimant_id=row["claimant_id"],
            proof_description=row["proof_description"],
            status=row["status"],
            submitted_at=row["submitted_at"],
            reviewed_at=row["reviewed_at"],
            reviewed_by=row["reviewed_by"],
            review_notes=row["review_notes"]
        )


class NotificationRepository:
    """Data access object for in-app user notifications."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path

    def create(self, notification: Notification) -> int:
        """Validate and insert a new notification."""
        notification.validate()
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                """
                INSERT INTO notifications (user_id, title, message, type, related_item_id, is_read)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    notification.user_id,
                    notification.title.strip(),
                    notification.message.strip(),
                    notification.type,
                    notification.related_item_id,
                    1 if notification.is_read else 0
                )
            )
            return cursor.lastrowid

    def get_by_id(self, notification_id: int) -> Optional[Notification]:
        """Fetch notification by primary key ID."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, title, message, type, related_item_id, is_read, created_at
                FROM notifications WHERE id = ?
                """,
                (notification_id,)
            )
            row = cursor.fetchone()
            return self._row_to_notification(row) if row else None
        finally:
            conn.close()

    def list_by_user(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """List recent notifications for a user, optionally filtering by unread status."""
        query = """
            SELECT id, user_id, title, message, type, related_item_id, is_read, created_at
            FROM notifications WHERE user_id = ?
        """
        params = [user_id]
        if unread_only:
            query += " AND is_read = 0"

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_notification(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def count_unread(self, user_id: int) -> int:
        """Count unread notification messages for a user."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0",
                (user_id,)
            )
            row = cursor.fetchone()
            return row["count"] if row else 0
        finally:
            conn.close()

    def mark_as_read(self, notification_id: int) -> bool:
        """Mark a single notification as read."""
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ?",
                (notification_id,)
            )
            return cursor.rowcount > 0

    def mark_all_as_read(self, user_id: int) -> int:
        """Mark all unread notifications for a user as read."""
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute(
                "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0",
                (user_id,)
            )
            return cursor.rowcount

    def delete(self, notification_id: int) -> bool:
        """Delete a notification by ID."""
        with get_db_cursor(self.db_path) as cursor:
            cursor.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_notification(row: sqlite3.Row) -> Notification:
        return Notification(
            id=row["id"],
            user_id=row["user_id"],
            title=row["title"],
            message=row["message"],
            type=row["type"],
            related_item_id=row["related_item_id"],
            is_read=bool(row["is_read"]),
            created_at=row["created_at"]
        )
