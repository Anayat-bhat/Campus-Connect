"""
CampusConnect: In-App Notification Center Dialog
Displays real-time user notifications, match alerts, and claim decision updates
with inspection and unread management.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict
from models.notification import Notification
from services.notification_service import NotificationService
from database.repository import ItemRepository
from gui.item_details_dialog import ItemDetailsDialog


TYPE_ICONS = {
    "MATCH_FOUND": "🤖",
    "CLAIM_SUBMITTED": "✋",
    "CLAIM_APPROVED": "✅",
    "CLAIM_REJECTED": "❌",
    "SYSTEM": "📢",
}

TYPE_LABELS = {
    "MATCH_FOUND": "Match",
    "CLAIM_SUBMITTED": "Claim Filed",
    "CLAIM_APPROVED": "Approved",
    "CLAIM_REJECTED": "Rejected",
    "SYSTEM": "System",
}


def format_notification_type(notif_type: str) -> str:
    """Format notification type with appropriate emoji and clean label."""
    icon = TYPE_ICONS.get(notif_type, "📢")
    label = TYPE_LABELS.get(notif_type, notif_type.replace("_", " ").title())
    return f"{icon} {label}"


class NotificationCenterDialog(tk.Toplevel):
    """Modal dialog presenting the user's notifications and match alerts."""

    def __init__(
        self,
        parent: tk.Widget,
        user_id: int,
        db_path: Optional[str] = None,
        on_notifications_changed: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__(parent)
        self.user_id = user_id
        self.db_path = db_path
        self.on_notifications_changed = on_notifications_changed
        self.notif_service = NotificationService(db_path=db_path)
        self.item_repo = ItemRepository(db_path)
        self.notif_map: Dict[str, Notification] = {}

        self.title("🔔 CampusConnect Notifications & Match Alerts")
        self.geometry("740x620")
        self.minsize(660, 520)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_notifications()

    def _build_ui(self) -> None:
        """Construct the notification viewer interface."""
        container = ttk.Frame(self, padding="18")
        container.pack(fill="both", expand=True)

        # 1. Header (Top)
        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(
            header,
            text="🔔 Notifications & Smart Alerts",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        self.count_lbl = ttk.Label(
            header,
            text="",
            font=("Segoe UI", 9),
            foreground="#8e6266"
        )
        self.count_lbl.pack(side="left", padx=(10, 0))

        mark_all_btn = ttk.Button(
            header,
            text="Mark All as Read",
            style="Secondary.TButton",
            command=self._on_mark_all_read
        )
        mark_all_btn.pack(side="right")

        # 2. Action Footer (Pinned to bottom first to ensure it is never clipped)
        footer = ttk.Frame(container)
        footer.pack(side="bottom", fill="x", pady=(12, 0))

        self.inspect_btn = ttk.Button(
            footer,
            text="🔍 Inspect Related Item",
            style="Primary.TButton",
            state="disabled",
            command=self._on_inspect_item
        )
        self.inspect_btn.pack(side="left", padx=(0, 8))

        self.mark_read_btn = ttk.Button(
            footer,
            text="✓ Mark as Read",
            style="Secondary.TButton",
            state="disabled",
            command=self._on_mark_single_read
        )
        self.mark_read_btn.pack(side="left")

        close_btn = ttk.Button(
            footer,
            text="Close",
            style="Secondary.TButton",
            command=self.destroy
        )
        close_btn.pack(side="right")

        # 3. Message Detail Box (Pinned above footer)
        detail_card = ttk.Frame(container, style="Card.TFrame", padding="12")
        detail_card.pack(side="bottom", fill="x", pady=(8, 0))

        ttk.Label(detail_card, text="Alert Message", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        
        msg_frame = ttk.Frame(detail_card)
        msg_frame.pack(fill="x", expand=False)

        self.message_box = tk.Text(
            msg_frame,
            wrap="word",
            font=("Segoe UI", 10),
            height=4,
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=8
        )
        msg_scroll = ttk.Scrollbar(msg_frame, orient="vertical", command=self.message_box.yview)
        self.message_box.configure(yscrollcommand=msg_scroll.set)

        self.message_box.pack(side="left", fill="both", expand=True)
        msg_scroll.pack(side="right", fill="y")
        self.message_box.configure(state="disabled")

        # 4. Table Card (Top/Middle, expands to fill remaining space)
        table_card = ttk.Frame(container, style="Card.TFrame", padding="8")
        table_card.pack(fill="both", expand=True)

        columns = ("type", "status", "title", "date")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse", height=7)

        self.tree.heading("type", text="Type", anchor="w")
        self.tree.heading("status", text="Status", anchor="center")
        self.tree.heading("title", text="Alert Title", anchor="w")
        self.tree.heading("date", text="Date & Time", anchor="center")

        self.tree.column("type", width=125, minwidth=110, anchor="w")
        self.tree.column("status", width=75, minwidth=65, anchor="center")
        self.tree.column("title", width=340, minwidth=220, anchor="w")
        self.tree.column("date", width=130, minwidth=110, anchor="center")

        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("UNREAD", font=("Segoe UI", 9, "bold"), foreground="#a21721")
        self.tree.tag_configure("READ", font=("Segoe UI", 9), foreground="#8e6266")

        self.tree.bind("<<TreeviewSelect>>", self._on_select_notification)

    def _load_notifications(self) -> None:
        """Fetch and populate notifications."""
        for child in self.tree.get_children():
            self.tree.delete(child)

        notifs = self.notif_service.list_user_notifications(self.user_id, limit=50)
        self.notif_map = {}
        unread_count = 0

        for n in notifs:
            self.notif_map[str(n.id)] = n
            if not n.is_read:
                unread_count += 1

            status_text = "🔵 New" if not n.is_read else "Read"
            tag = "UNREAD" if not n.is_read else "READ"

            self.tree.insert(
                "",
                "end",
                iid=str(n.id),
                values=(
                    format_notification_type(n.type),
                    status_text,
                    n.title,
                    n.created_at[:16] if n.created_at else ""
                ),
                tags=(tag,)
            )

        self.count_lbl.configure(text=f"({unread_count} unread of {len(notifs)} total)")

    def _on_select_notification(self, event: tk.Event) -> None:
        """Display notification content and enable actions."""
        selected = self.tree.selection()
        if not selected or selected[0] not in self.notif_map:
            return

        notif = self.notif_map[selected[0]]

        # Display message
        self.message_box.configure(state="normal")
        self.message_box.delete("1.0", tk.END)
        self.message_box.insert("1.0", notif.message)
        self.message_box.configure(state="disabled")

        # Automatically mark as read if not already read
        if not notif.is_read:
            self.notif_service.mark_read(notif.id)
            notif.is_read = True
            # Update row appearance
            self.tree.item(str(notif.id), tags=("READ",), values=(
                format_notification_type(notif.type),
                "Read",
                notif.title,
                notif.created_at[:16] if notif.created_at else ""
            ))
            if self.on_notifications_changed:
                self.on_notifications_changed()

        # Update action buttons
        self.mark_read_btn.configure(state="disabled")
        if notif.related_item_id:
            self.inspect_btn.configure(state="normal")
        else:
            self.inspect_btn.configure(state="disabled")

    def _on_mark_single_read(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        notif_id = int(selected[0])
        self.notif_service.mark_read(notif_id)
        self._load_notifications()
        if self.on_notifications_changed:
            self.on_notifications_changed()

    def _on_mark_all_read(self) -> None:
        self.notif_service.mark_all_read(self.user_id)
        self._load_notifications()
        if self.on_notifications_changed:
            self.on_notifications_changed()

    def _on_inspect_item(self) -> None:
        """Open item details for the item referenced in this alert."""
        selected = self.tree.selection()
        if not selected or selected[0] not in self.notif_map:
            return

        notif = self.notif_map[selected[0]]
        if not notif.related_item_id:
            return

        item = self.item_repo.get_by_id(notif.related_item_id)
        if not item:
            messagebox.showinfo("Item Expired", "The referenced item is no longer available in the database.", parent=self)
            return

        ItemDetailsDialog(
            parent=self,
            item=item,
            current_user_id=self.user_id,
            db_path=self.db_path
        )
