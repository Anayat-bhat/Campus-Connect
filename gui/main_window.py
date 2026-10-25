"""
CampusConnect: Main Dashboard Window & Application Shell
Integrates navigation, user session status, search directory, reporting forms,
and personal report tracking into a tabbed interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from models.user import User
from models.item import Item
from database.repository import ItemRepository
from services.session_manager import SessionManager, session_manager as default_session_manager
from gui.search_frame import SearchFrame
from gui.report_item_frame import ReportItemFrame
from gui.my_items_frame import MyItemsFrame


class MainWindow(ttk.Frame):
    """Main application container frame shown after successful authentication."""

    def __init__(
        self,
        parent: tk.Widget,
        db_path: Optional[str] = None,
        session: Optional[SessionManager] = None,
        on_logout: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.session = session if session is not None else default_session_manager
        self.on_logout = on_logout
        self.item_repo = ItemRepository(db_path)

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct dashboard header and primary navigation tabs."""
        # Top Global Navigation Bar
        navbar = ttk.Frame(self, style="Sidebar.TFrame", padding="16 12")
        navbar.pack(fill="x")

        # Brand on left
        brand_frame = ttk.Frame(navbar, style="Sidebar.TFrame")
        brand_frame.pack(side="left")

        brand_lbl = ttk.Label(
            brand_frame,
            text="🎓 CampusConnect",
            style="Brand.TLabel"
        )
        brand_lbl.pack(anchor="w")

        sub_lbl = ttk.Label(
            brand_frame,
            text="Smart Lost & Found Management System",
            style="BrandSub.TLabel"
        )
        sub_lbl.pack(anchor="w")

        # User Profile & Logout on right
        user_frame = ttk.Frame(navbar, style="Sidebar.TFrame")
        user_frame.pack(side="right")

        user = self.session.current_user
        full_name = user.full_name if user else "Guest"
        role_tag = f"[{user.role.upper()}]" if user else ""

        user_chip = ttk.Label(
            user_frame,
            text=f"👤 {full_name} {role_tag}",
            style="Brand.TLabel",
            font=("Segoe UI", 10, "bold")
        )
        user_chip.pack(side="left", padx=(0, 16))

        logout_btn = ttk.Button(
            user_frame,
            text="Log Out",
            command=self._handle_logout
        )
        logout_btn.pack(side="right")

        # Main Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=12)

        # Tab 1: Search & Browse
        self.search_tab = SearchFrame(
            parent=self.notebook,
            db_path=self.db_path,
            session=self.session,
            on_claim_callback=self._on_claim_item
        )
        self.notebook.add(self.search_tab, text="  🔍 Browse & Search  ")

        # Tab 2: Report Item
        self.report_tab = ReportItemFrame(
            parent=self.notebook,
            db_path=self.db_path,
            session=self.session,
            on_success_callback=self._on_item_created
        )
        self.notebook.add(self.report_tab, text="  📝 Report Item  ")

        # Tab 3: My Reports
        self.my_items_tab = MyItemsFrame(
            parent=self.notebook,
            db_path=self.db_path,
            session=self.session
        )
        self.notebook.add(self.my_items_tab, text="  📋 My Reports  ")

        # Listen for tab changes to auto-refresh data
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event: tk.Event) -> None:
        """Refresh contents of the activated tab."""
        selected_index = self.notebook.index(self.notebook.select())
        if selected_index == 0:
            self.search_tab.refresh()
        elif selected_index == 2:
            self.my_items_tab.refresh()

    def _on_item_created(self, item_id: int) -> None:
        """Handle new item submission by refreshing views and switching to search tab."""
        self.search_tab.refresh()
        self.my_items_tab.refresh()
        self.notebook.select(self.search_tab)

    def _on_claim_item(self, item: Item) -> None:
        """Placeholder hook for claiming items (fully wired in Phase 7)."""
        messagebox.showinfo(
            "Claim Request",
            f"Claiming #{item.id} ('{item.title}'). The claim workflow will be launched.",
            parent=self
        )

    def _handle_logout(self) -> None:
        """Confirm and execute session logout."""
        if messagebox.askyesno("Confirm Log Out", "Are you sure you want to log out of your session?", parent=self):
            self.session.logout()
            if self.on_logout:
                self.on_logout()
