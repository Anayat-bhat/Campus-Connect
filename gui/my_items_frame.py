"""
CampusConnect: My Reported Items Frame
Displays items reported by the currently authenticated user, with status tracking
and safe deletion options.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from models.item import Item
from database.repository import ItemRepository
from gui.item_details_dialog import ItemDetailsDialog
from services.session_manager import SessionManager, session_manager as default_session_manager


class MyItemsFrame(ttk.Frame):
    """View showing items posted by the current user."""

    def __init__(
        self,
        parent: tk.Widget,
        db_path: Optional[str] = None,
        session: Optional[SessionManager] = None
    ) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.session = session if session is not None else default_session_manager
        self.item_repo = ItemRepository(db_path)

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        """Render table and controls."""
        header_card = ttk.Frame(self, style="Card.TFrame", padding="16")
        header_card.pack(fill="x", padx=16, pady=(16, 8))

        ttk.Label(
            header_card,
            text="📋 My Reported Items",
            font=("Segoe UI", 12, "bold"),
            background="#ffffff"
        ).pack(side="left")

        self.count_lbl = ttk.Label(
            header_card,
            text="0 reports",
            font=("Segoe UI", 9),
            foreground="#64748b",
            background="#ffffff"
        )
        self.count_lbl.pack(side="left", padx=(10, 0))

        # Table
        table_card = ttk.Frame(self, style="Card.TFrame", padding="12")
        table_card.pack(fill="both", expand=True, padx=16, pady=8)

        columns = ("id", "type", "title", "category", "location", "date", "status")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="#", anchor="center")
        self.tree.heading("type", text="Type", anchor="center")
        self.tree.heading("title", text="Title", anchor="w")
        self.tree.heading("category", text="Category", anchor="w")
        self.tree.heading("location", text="Location", anchor="w")
        self.tree.heading("date", text="Date", anchor="center")
        self.tree.heading("status", text="Status", anchor="center")

        self.tree.column("id", width=45, minwidth=35, anchor="center")
        self.tree.column("type", width=70, minwidth=60, anchor="center")
        self.tree.column("title", width=220, minwidth=140, anchor="w")
        self.tree.column("category", width=140, minwidth=110, anchor="w")
        self.tree.column("location", width=140, minwidth=100, anchor="w")
        self.tree.column("date", width=95, minwidth=80, anchor="center")
        self.tree.column("status", width=105, minwidth=85, anchor="center")

        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("LOST", foreground="#b91c1c")
        self.tree.tag_configure("FOUND", foreground="#15803d")
        self.tree.tag_configure("RETURNED", foreground="#94a3b8")

        self.tree.bind("<Double-1>", lambda _: self._on_view_details())

        # Action bar
        footer = ttk.Frame(self, padding="16 6 16 12")
        footer.pack(fill="x")

        view_btn = ttk.Button(footer, text="🔍 View Details", style="Primary.TButton", command=self._on_view_details)
        view_btn.pack(side="left", padx=(0, 8))

        del_btn = ttk.Button(footer, text="🗑️ Delete Item", style="Danger.TButton", command=self._on_delete_selected)
        del_btn.pack(side="left", padx=(0, 8))

        refresh_btn = ttk.Button(footer, text="↻ Refresh", style="Secondary.TButton", command=self.refresh)
        refresh_btn.pack(side="left")

    def refresh(self) -> None:
        """Reload user's reported items."""
        for child in self.tree.get_children():
            self.tree.delete(child)

        user = self.session.current_user
        if not user:
            self.count_lbl.configure(text="Not logged in")
            return

        items = self.item_repo.list_by_user(user.id)
        self.count_lbl.configure(text=f"{len(items)} items reported by you")

        for item in items:
            tag = item.status if item.status == "RETURNED" else item.type
            self.tree.insert(
                "",
                "end",
                iid=str(item.id),
                values=(
                    f"#{item.id}",
                    item.type,
                    item.title,
                    item.category,
                    item.location,
                    item.event_date,
                    item.status
                ),
                tags=(tag,)
            )

    def _on_view_details(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Item", "Please select an item from your reports.", parent=self)
            return

        item_id = int(selected[0])
        item = self.item_repo.get_by_id(item_id)
        if not item:
            messagebox.showerror("Error", f"Item #{item_id} not found.", parent=self)
            return

        user = self.session.current_user
        current_uid = user.id if user else None

        ItemDetailsDialog(
            parent=self,
            item=item,
            current_user_id=current_uid,
            is_admin=self.session.is_admin(),
            on_delete_callback=lambda it: self._delete_item(it.id),
            db_path=self.db_path
        )

    def _on_delete_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Item", "Please select an item to delete.", parent=self)
            return

        item_id = int(selected[0])
        self._delete_item(item_id)

    def _delete_item(self, item_id: int) -> None:
        user = self.session.current_user
        user_id = user.id if user else 0
        try:
            self.item_repo.delete(item_id, requesting_user_id=user_id, is_admin=self.session.is_admin())
            messagebox.showinfo("Success", f"Item #{item_id} was successfully deleted.", parent=self)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete item: {e}", parent=self)
