"""
CampusConnect: In-App Notification & Alert Dispatcher Service
Manages real-time campus notifications for algorithmic match detections,
claim submissions, and administrative review decisions.
"""

from typing import Optional, List, Dict, Any
from database.repository import NotificationRepository, ItemRepository, UserRepository
from models.notification import Notification
from models.item import Item
from models.claim import Claim
from services.matching_service import MatchingService


class NotificationService:
    """Service orchestrating alert generation, unread counts, and match triggers."""

    def __init__(
        self,
        notif_repo: Optional[NotificationRepository] = None,
        item_repo: Optional[ItemRepository] = None,
        user_repo: Optional[UserRepository] = None,
        matching_service: Optional[MatchingService] = None,
        db_path: Optional[str] = None
    ) -> None:
        self.db_path = db_path
        self.notif_repo = notif_repo if notif_repo is not None else NotificationRepository(db_path)
        self.item_repo = item_repo if item_repo is not None else ItemRepository(db_path)
        self.user_repo = user_repo if user_repo is not None else UserRepository(db_path)
        self.matching_service = matching_service if matching_service is not None else MatchingService(item_repo=self.item_repo, db_path=db_path)

    def notify(
        self,
        user_id: int,
        title: str,
        message: str,
        notif_type: str = "SYSTEM",
        related_item_id: Optional[int] = None
    ) -> Notification:
        """Create and persist an in-app notification for a user."""
        notif = Notification(
            id=None,
            user_id=user_id,
            title=title,
            message=message,
            type=notif_type,
            related_item_id=related_item_id,
            is_read=False
        )
        notif_id = self.notif_repo.create(notif)
        notif.id = notif_id
        return notif

    def get_unread_count(self, user_id: int) -> int:
        """Return the number of unread alerts for the specified user."""
        return self.notif_repo.count_unread(user_id)

    def list_user_notifications(self, user_id: int, unread_only: bool = False, limit: int = 50) -> List[Notification]:
        """Fetch notification history for a user."""
        return self.notif_repo.list_by_user(user_id, unread_only=unread_only, limit=limit)

    def mark_read(self, notification_id: int) -> bool:
        """Mark a notification message as read."""
        return self.notif_repo.mark_as_read(notification_id)

    def mark_all_read(self, user_id: int) -> int:
        """Mark all unread notifications for a user as read."""
        return self.notif_repo.mark_all_as_read(user_id)

    def scan_and_alert_matches(self, new_item: Item, min_threshold: float = 60.0) -> List[Notification]:
        """
        Evaluate candidate matches against the new report.
        Alert owners of counterpart reports when high-confidence matches are found.
        """
        matches = self.matching_service.find_matches_for_item(new_item, min_threshold=min_threshold, limit=5)
        created_notifs: List[Notification] = []

        for m in matches:
            target = m.target_item
            if not target.user_id:
                continue

            # Do not self-notify if same user reported both
            if target.user_id == new_item.user_id:
                continue

            pct = int(round(m.overall_score))
            title = f"🤖 Potential {new_item.type.capitalize()} Match Found ({pct}%)"
            msg = (
                f"Your reported {target.type} item '{target.title}' has a strong {pct}% algorithmic match "
                f"with recently reported {new_item.type} item '{new_item.title}' at {new_item.location}. "
                f"Rationale: {m.explanation}"
            )

            notif = self.notify(
                user_id=target.user_id,
                title=title,
                message=msg,
                notif_type="MATCH_FOUND",
                related_item_id=new_item.id
            )
            created_notifs.append(notif)

        return created_notifs

    def alert_claim_submitted(self, claim: Claim, item: Item) -> Optional[Notification]:
        """Alert the finder of a found item that an ownership claim has been submitted."""
        if not item.user_id or item.user_id == claim.claimant_id:
            return None

        title = f"✋ Claim Submitted on '{item.title}'"
        msg = (
            f"A student has submitted an ownership claim #{claim.id} for your reported found item '{item.title}'. "
            f"Campus administrators will verify their distinguishing proof description."
        )
        return self.notify(
            user_id=item.user_id,
            title=title,
            message=msg,
            notif_type="CLAIM_SUBMITTED",
            related_item_id=item.id
        )

    def alert_claim_decision(
        self,
        claim: Claim,
        item: Item,
        approved: bool,
        notes: Optional[str] = None
    ) -> Notification:
        """Alert the claimant regarding the administrative decision on their claim."""
        if approved:
            title = f"🎉 Claim Approved for '{item.title}'"
            msg = (
                f"Congratulations! Your ownership claim #{claim.id} for '{item.title}' was approved by administration. "
                f"You can now pick up your item from the campus security office. "
                f"Verification Notes: {notes or 'Identity confirmed.'}"
            )
            notif_type = "CLAIM_APPROVED"
        else:
            title = f"❌ Claim Update for '{item.title}'"
            msg = (
                f"Your ownership claim #{claim.id} for '{item.title}' was reviewed and rejected. "
                f"Reason: {notes or 'Provided proof did not match item features.'}"
            )
            notif_type = "CLAIM_REJECTED"

        return self.notify(
            user_id=claim.claimant_id,
            title=title,
            message=msg,
            notif_type=notif_type,
            related_item_id=item.id
        )
