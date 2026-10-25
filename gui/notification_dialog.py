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
        self.geometry("640x540")
        self.minsize(560, 460)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_notifications()

    def _build_ui(self) -> None:
        """Construct the notification viewer interface."""
        container = ttk.Frame(self, padding="20")
        container.pack(fill="both", expand=True)

        # Header
        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(
            header,
            text="🔔 Notifications & Smart Alerts",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        self.count_lbl = ttk.Label(
            header,
            text="",
            font=("Segoe UI", 9),
            foreground="#64748b"
        )
        self.count_lbl.pack(side="left", padx=(10, 0))

        mark_all_btn = ttk.Button(
            header,
            text="Mark All as Read",
            style="Secondary.TButton",
            command=self._on_mark_all_read
        )
        mark_all_btn.pack(side="right")

        # Split pane: Top list, Bottom detail box
        table_card = ttk.Frame(container, style="Card.TFrame", padding="8")
        table_card.pack(fill="both", expand=True, pady=(0, 12))

        columns = ("type", "status", "title", "date")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse", height=7)

        self.tree.heading("type", text="Type", anchor="center")
        self.tree.heading("status", text="Status", anchor="center")
        self.tree.heading("title", text="Alert Title", anchor="w")
        self.tree.heading("date", text="Date & Time", anchor="center")

        self.tree.column("type", width=70, minwidth=60, anchor="center")
        self.tree.column("status", width=75, minwidth=65, anchor="center")
        self.tree.column("title", width=280, minwidth=200, anchor="w")
        self.tree.column("date", width=120, minwidth=100, anchor="center")

        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("UNREAD", font=("Segoe UI", 9, "bold"), foreground="#2563eb")
        self.tree.tag_configure("READ", font=("Segoe UI", 9), foreground="#64748b")

        self.tree.bind("<<TreeviewSelect>>", self._on_select_notification)

        # Message Detail Box
        detail_card = ttk.Frame(container, style="Card.TFrame", padding="12")
        detail_card.pack(fill="both", expand=True, pady=(0, 12))

        ttk.Label(detail_card, text="Alert Message", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 4))
        self.message_box = tk.Text(
            detail_card,
            wrap="word",
            font=("Segoe UI", 10),
            height=4,
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=8
        )
        self.message_box.pack(fill="both", expand=True)
        self.message_box.configure(state="disabled")

        # Action Footer
        footer = ttk.Frame(container)
        footer.pack(fill="x")

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

            icon = TYPE_ICONS.get(n.type, "📢")
            status_text = "🔵 New" if not n.is_read else "Read"
            tag = "UNREAD" if not n.is_read else "READ"

            self.tree.insert(
                "",
                "end",
                iid=str(n.id),
                values=(
                    f"{icon} {n.type[:5]}",
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
                f"{TYPE_ICONS.get(notif.type, '📢')} {notif.type[:5]}",
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
