"""
CampusConnect: Item Details Dialog
Provides an in-depth modal inspection view of a Lost or Found item.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from models.item import Item
from database.repository import ItemRepository, UserRepository


class ItemDetailsDialog(tk.Toplevel):
    """Modal dialog displaying comprehensive item details and actions."""

    def __init__(
        self,
        parent: tk.Widget,
        item: Item,
        current_user_id: Optional[int] = None,
        is_admin: bool = False,
        on_claim_callback: Optional[Callable[[Item], None]] = None,
        on_delete_callback: Optional[Callable[[Item], None]] = None,
        db_path: Optional[str] = None
    ) -> None:
        super().__init__(parent)
        self.item = item
        self.current_user_id = current_user_id
        self.is_admin = is_admin
        self.on_claim_callback = on_claim_callback
        self.on_delete_callback = on_delete_callback
        self.db_path = db_path
        self.user_repo = UserRepository(db_path)

        self.title(f"Item Details — #{item.id} {item.title}")
        self.geometry("620x580")
        self.minsize(540, 500)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct item detail presentation."""
        # Main container with padding
        container = ttk.Frame(self, padding="24")
        container.pack(fill="both", expand=True)

        # Header Badge & Title
        header_frame = ttk.Frame(container)
        header_frame.pack(fill="x", pady=(0, 16))

        badge_color = "#dc2626" if self.item.type == "LOST" else "#16a34a"
        type_badge = tk.Label(
            header_frame,
            text=f"  {self.item.type}  ",
            bg=badge_color,
            fg="#ffffff",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padx=6,
            pady=3
        )
        type_badge.pack(side="left", padx=(0, 10))

        title_lbl = ttk.Label(
            header_frame,
            text=self.item.title,
            font=("Segoe UI", 14, "bold"),
            wraplength=420
        )
        title_lbl.pack(side="left", fill="x", expand=True)

        # Metadata Card
        meta_card = ttk.Frame(container, style="Card.TFrame", padding="16")
        meta_card.pack(fill="x", pady=(0, 16))

        # Fetch reporter details
        reporter_name = "Unknown"
        reporter_email = "N/A"
        if self.item.user_id:
            user = self.user_repo.get_by_id(self.item.user_id)
            if user:
                reporter_name = user.full_name
                reporter_email = user.email

        details = [
            ("Category:", self.item.category),
            ("Date Reported:", self.item.event_date),
            ("Location:", self.item.location),
            ("Current Status:", self.item.status),
            ("Reported By:", f"{reporter_name} ({reporter_email})"),
        ]

        if self.item.image_path:
            details.append(("Attached Image:", self.item.image_path))

        for row_idx, (label, val) in enumerate(details):
            lbl = ttk.Label(meta_card, text=label, font=("Segoe UI", 10, "bold"), width=16)
            lbl.grid(row=row_idx, column=0, sticky="w", pady=4)

            val_lbl = ttk.Label(meta_card, text=val, font=("Segoe UI", 10))
            val_lbl.grid(row=row_idx, column=1, sticky="w", pady=4)

        # Full Description Card
        desc_card = ttk.Frame(container, style="Card.TFrame", padding="16")
        desc_card.pack(fill="both", expand=True, pady=(0, 16))

        desc_title = ttk.Label(desc_card, text="Detailed Description", font=("Segoe UI", 11, "bold"))
        desc_title.pack(anchor="w", pady=(0, 8))

        desc_box = tk.Text(
            desc_card,
            wrap="word",
            font=("Segoe UI", 10),
            bg="#ffffff",
            relief="solid",
            borderwidth=1,
            height=6,
            padx=8,
            pady=8
        )
        desc_box.insert("1.0", self.item.description)
        desc_box.configure(state="disabled")
        desc_box.pack(fill="both", expand=True)

        # Action Buttons footer
        action_bar = ttk.Frame(container)
        action_bar.pack(fill="x")

        # Claim button (only for items reported as FOUND, status OPEN, and not reported by the current user)
        is_owner = (self.current_user_id == self.item.user_id)
        if self.item.type == "FOUND" and self.item.status == "OPEN" and not is_owner:
            claim_btn = ttk.Button(
                action_bar,
                text="✋ Claim This Item",
                style="Primary.TButton",
                command=self._on_claim
            )
            claim_btn.pack(side="left", padx=(0, 8))

        # Delete button (only if owner or admin, and not already returned)
        can_delete = (is_owner or self.is_admin) and self.item.status != "RETURNED"
        if can_delete:
            del_btn = ttk.Button(
                action_bar,
                text="🗑️ Delete Item",
                style="Danger.TButton",
                command=self._on_delete
            )
            del_btn.pack(side="left")

        close_btn = ttk.Button(
            action_bar,
            text="Close",
            style="Secondary.TButton",
            command=self.destroy
        )
        close_btn.pack(side="right")

    def _on_claim(self) -> None:
        if self.on_claim_callback:
            self.destroy()
            self.on_claim_callback(self.item)

    def _on_delete(self) -> None:
        if messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to permanently delete item #{self.item.id} ('{self.item.title}')?",
            parent=self
        ):
            if self.on_delete_callback:
                self.destroy()
                self.on_delete_callback(self.item)
