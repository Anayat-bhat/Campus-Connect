"""
CampusConnect: Search & Item Directory Frame
Provides real-time multi-filter parameterized searching, pagination, and inspection
of lost and found campus items.
"""

import math
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Callable
from models.item import Item, VALID_CATEGORIES, VALID_STATUSES
from database.repository import ItemRepository
from gui.item_details_dialog import ItemDetailsDialog
from services.session_manager import SessionManager, session_manager as default_session_manager


PAGE_SIZE = 12


class SearchFrame(ttk.Frame):
    """View component for searching and browsing lost/found items."""

    def __init__(
        self,
        parent: tk.Widget,
        db_path: Optional[str] = None,
        session: Optional[SessionManager] = None,
        on_claim_callback: Optional[Callable[[Item], None]] = None
    ) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.session = session if session is not None else default_session_manager
        self.on_claim_callback = on_claim_callback
        self.item_repo = ItemRepository(db_path)

        self.current_page = 1
        self.total_items = 0
        self.total_pages = 1
        self.cached_items: List[Item] = []

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        """Construct the search filters and data table."""
        # Top Filter Card
        filter_card = ttk.Frame(self, style="Card.TFrame", padding="16")
        filter_card.pack(fill="x", padx=16, pady=(16, 8))

        # Title / Summary
        header_row = ttk.Frame(filter_card, style="Card.TFrame")
        header_row.pack(fill="x", pady=(0, 10))

        ttk.Label(
            header_row,
            text="🔍 Search & Filter Items",
            font=("Segoe UI", 12, "bold"),
            background="#ffffff"
        ).pack(side="left")

        # Filter Inputs Row 1: Keyword, Type, Category
        row1 = ttk.Frame(filter_card, style="Card.TFrame")
        row1.pack(fill="x", pady=4)

        ttk.Label(row1, text="Keyword:", background="#ffffff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.keyword_var = tk.StringVar()
        self.keyword_entry = ttk.Entry(row1, textvariable=self.keyword_var, width=22)
        self.keyword_entry.pack(side="left", padx=(0, 14))
        self.keyword_entry.bind("<Return>", lambda _: self.search_items())

        ttk.Label(row1, text="Type:", background="#ffffff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.type_var = tk.StringVar(value="All")
        self.type_cb = ttk.Combobox(
            row1,
            textvariable=self.type_var,
            values=["All", "LOST", "FOUND"],
            state="readonly",
            width=8
        )
        self.type_cb.pack(side="left", padx=(0, 14))
        self.type_cb.bind("<<ComboboxSelected>>", lambda _: self.search_items())

        ttk.Label(row1, text="Category:", background="#ffffff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.cat_var = tk.StringVar(value="All")
        self.cat_cb = ttk.Combobox(
            row1,
            textvariable=self.cat_var,
            values=["All"] + sorted(list(VALID_CATEGORIES)),
            state="readonly",
            width=18
        )
        self.cat_cb.pack(side="left", padx=(0, 14))
        self.cat_cb.bind("<<ComboboxSelected>>", lambda _: self.search_items())

        # Filter Inputs Row 2: Status, Location, and Action Buttons
        row2 = ttk.Frame(filter_card, style="Card.TFrame")
        row2.pack(fill="x", pady=4)

        ttk.Label(row2, text="Status:", background="#ffffff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.status_var = tk.StringVar(value="All")
        self.status_cb = ttk.Combobox(
            row2,
            textvariable=self.status_var,
            values=["All", "OPEN", "CLAIM_PENDING", "RETURNED"],
            state="readonly",
            width=14
        )
        self.status_cb.pack(side="left", padx=(0, 14))
        self.status_cb.bind("<<ComboboxSelected>>", lambda _: self.search_items())

        ttk.Label(row2, text="Location:", background="#ffffff", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
        self.loc_var = tk.StringVar()
        self.loc_entry = ttk.Entry(row2, textvariable=self.loc_var, width=18)
        self.loc_entry.pack(side="left", padx=(0, 14))
        self.loc_entry.bind("<Return>", lambda _: self.search_items())

        search_btn = ttk.Button(row2, text="Search", style="Primary.TButton", command=self.search_items)
        search_btn.pack(side="left", padx=(0, 6))

        reset_btn = ttk.Button(row2, text="Reset", style="Secondary.TButton", command=self.reset_filters)
        reset_btn.pack(side="left")

        # Table Container
        table_card = ttk.Frame(self, style="Card.TFrame", padding="12")
        table_card.pack(fill="both", expand=True, padx=16, pady=8)

        columns = ("id", "type", "title", "category", "location", "date", "status")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="#", anchor="center")
        self.tree.heading("type", text="Type", anchor="center")
        self.tree.heading("title", text="Item Title", anchor="w")
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

        # Table scrollbar
        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Row tag highlights
        self.tree.tag_configure("LOST", foreground="#b91c1c")
        self.tree.tag_configure("FOUND", foreground="#15803d")
        self.tree.tag_configure("RETURNED", foreground="#94a3b8")

        self.tree.bind("<Double-1>", lambda _: self._on_view_details())

        # Pagination & Action Footer
        footer = ttk.Frame(self, padding="16 6 16 12")
        footer.pack(fill="x")

        # Actions on selected item
        view_btn = ttk.Button(footer, text="🔍 View Details", style="Primary.TButton", command=self._on_view_details)
        view_btn.pack(side="left", padx=(0, 8))

        refresh_btn = ttk.Button(footer, text="↻ Refresh", style="Secondary.TButton", command=self.refresh)
        refresh_btn.pack(side="left")

        # Pagination controls
        self.next_btn = ttk.Button(footer, text="Next ▶", command=self._next_page)
        self.next_btn.pack(side="right", padx=(4, 0))

        self.prev_btn = ttk.Button(footer, text="◀ Prev", command=self._prev_page)
        self.prev_btn.pack(side="right")

        self.page_lbl = ttk.Label(footer, text="Page 1 of 1 (0 items)", font=("Segoe UI", 9))
        self.page_lbl.pack(side="right", padx=12)

    def reset_filters(self) -> None:
        """Clear all search filter values."""
        self.keyword_var.set("")
        self.type_var.set("All")
        self.cat_var.set("All")
        self.status_var.set("All")
        self.loc_var.set("")
        self.current_page = 1
        self.search_items()

    def search_items(self) -> None:
        """Query repository with active filters and update table view."""
        self.current_page = 1
        self._load_data()

    def refresh(self) -> None:
        """Reload current page results."""
        self._load_data()

    def _get_filter_params(self) -> tuple:
        item_type = self.type_var.get() if self.type_var.get() != "All" else None
        category = self.cat_var.get() if self.cat_var.get() != "All" else None
        status = self.status_var.get() if self.status_var.get() != "All" else None
        keyword = self.keyword_var.get().strip() or None
        location = self.loc_var.get().strip() or None
        return item_type, category, status, keyword, location

    def _load_data(self) -> None:
        """Fetch matching items from database and render tree rows."""
        item_type, category, status, keyword, location = self._get_filter_params()

        self.total_items = self.item_repo.count_items(
            item_type=item_type,
            category=category,
            status=status,
            keyword=keyword,
            location=location
        )

        self.total_pages = max(1, math.ceil(self.total_items / PAGE_SIZE))
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages

        offset = (self.current_page - 1) * PAGE_SIZE
        self.cached_items = self.item_repo.list_items(
            item_type=item_type,
            category=category,
            status=status,
            keyword=keyword,
            location=location,
            limit=PAGE_SIZE,
            offset=offset
        )

        # Clear existing items
        for child in self.tree.get_children():
            self.tree.delete(child)

        # Insert items
        for item in self.cached_items:
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

        # Update pagination display
        self.page_lbl.configure(
            text=f"Page {self.current_page} of {self.total_pages} ({self.total_items} items found)"
        )
        self.prev_btn.configure(state="normal" if self.current_page > 1 else "disabled")
        self.next_btn.configure(state="normal" if self.current_page < self.total_pages else "disabled")

    def _prev_page(self) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self._load_data()

    def _next_page(self) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._load_data()

    def _on_view_details(self) -> None:
        """Open item detail dialog for selected item."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Item", "Please select an item from the table to view details.", parent=self)
            return

        item_id = int(selected[0])
        item = self.item_repo.get_by_id(item_id)
        if not item:
            messagebox.showerror("Error", f"Item #{item_id} could not be retrieved.", parent=self)
            return

        user = self.session.current_user
        current_uid = user.id if user else None
        is_admin = self.session.is_admin()

        ItemDetailsDialog(
            parent=self,
            item=item,
            current_user_id=current_uid,
            is_admin=is_admin,
            on_claim_callback=self.on_claim_callback,
            on_delete_callback=self._on_item_deleted,
            db_path=self.db_path
        )

    def _on_item_deleted(self, item: Item) -> None:
        user = self.session.current_user
        user_id = user.id if user else 0
        try:
            self.item_repo.delete(item.id, requesting_user_id=user_id, is_admin=self.session.is_admin())
            messagebox.showinfo("Deleted", f"Item #{item.id} has been deleted.", parent=self)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete item: {e}", parent=self)
