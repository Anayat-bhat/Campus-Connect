"""
Unit Tests for Phase 5: GUI Presentation Layer
Verifies styling, window instantiation, frames, data binding, and filters.
"""

import os
import sqlite3
import unittest
import tkinter as tk

from database.connection import DEFAULT_SCHEMA_PATH, seed_default_admin
from database.repository import UserRepository, ItemRepository
from models.user import User
from models.item import Item
from services.session_manager import SessionManager
from gui.styles import apply_theme, COLORS, FONTS
from gui.auth_window import AuthWindow
from gui.search_frame import SearchFrame
from gui.report_item_frame import ReportItemFrame
from gui.my_items_frame import MyItemsFrame
from main import CampusConnectApp


class TestGUIComponents(unittest.TestCase):
    """Test suite validating Phase 5 GUI windows and widget frames."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
            cls.tk_available = True
        except tk.TclError:
            cls.tk_available = False

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.tk_available and cls.root:
            cls.root.destroy()

    def setUp(self) -> None:
        if not self.tk_available:
            self.skipTest("Tkinter display is not available in current environment.")

        self.test_db = os.path.join(os.path.dirname(__file__), "test_gui.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        conn = sqlite3.connect(self.test_db)
        conn.execute("PRAGMA foreign_keys = ON;")
        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

        seed_default_admin(self.test_db)

        self.session = SessionManager()
        self.user_repo = UserRepository(self.test_db)
        self.item_repo = ItemRepository(self.test_db)

        # Login a student session
        self.student = self.user_repo.get_by_username("admin")
        self.session.login(self.student)

        # Populate a sample item
        self.sample_item = Item(
            id=None,
            type="LOST",
            user_id=self.student.id,
            title="Black Lenovo Laptop Charger",
            category="Electronics",
            description="Type-C 65W charging adapter left on 3rd floor desk.",
            event_date="2026-10-24",
            location="Library 3rd Floor",
            image_path=None,
            status="OPEN"
        )
        self.sample_item.id = self.item_repo.create(self.sample_item)

    def tearDown(self) -> None:
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_theme_and_colors(self) -> None:
        """Verify theme configuration and color palette definitions."""
        self.assertIn("primary", COLORS)
        self.assertIn("bg_main", COLORS)
        self.assertIn("h1", FONTS)
        style = apply_theme(self.root)
        self.assertIsNotNone(style)

    def test_auth_window_instantiation(self) -> None:
        """Verify AuthWindow creates notebook tabs and input variables."""
        auth_win = AuthWindow(parent=self.root, db_path=self.test_db, session=self.session)
        self.assertIsNotNone(auth_win.login_ident_entry)
        self.assertIsNotNone(auth_win.login_pwd_entry)
        self.assertEqual(auth_win.notebook.index("end"), 2)
        auth_win.destroy()

    def test_report_item_frame_inputs_and_reset(self) -> None:
        """Verify ReportItemFrame inputs, validation, and reset behavior."""
        frame = ReportItemFrame(parent=self.root, db_path=self.test_db, session=self.session)
        frame.title_var.set("Blue Water Bottle")
        frame.location_var.set("Cafeteria")
        frame.desc_text.insert("1.0", "Stainless steel water bottle with stickers.")

        self.assertEqual(frame.title_var.get(), "Blue Water Bottle")

        frame.reset_form()
        self.assertEqual(frame.title_var.get(), "")
        self.assertEqual(frame.location_var.get(), "")
        self.assertEqual(frame.desc_text.get("1.0", tk.END).strip(), "")
        frame.destroy()

    def test_search_frame_data_loading_and_filtering(self) -> None:
        """Verify SearchFrame loads repository data and filters appropriately."""
        search_frame = SearchFrame(parent=self.root, db_path=self.test_db, session=self.session)

        # Initial load should have at least 1 item
        self.assertGreaterEqual(len(search_frame.cached_items), 1)
        self.assertEqual(search_frame.cached_items[0].title, "Black Lenovo Laptop Charger")

        # Test filtering by keyword
        search_frame.keyword_var.set("Lenovo")
        search_frame.search_items()
        self.assertEqual(len(search_frame.cached_items), 1)

        # Non-matching keyword
        search_frame.keyword_var.set("NonexistentItemXYZ")
        search_frame.search_items()
        self.assertEqual(len(search_frame.cached_items), 0)

        # Reset filter
        search_frame.reset_filters()
        self.assertGreaterEqual(len(search_frame.cached_items), 1)

        search_frame.destroy()

    def test_my_items_frame_data(self) -> None:
        """Verify MyItemsFrame shows items belonging to active user."""
        my_frame = MyItemsFrame(parent=self.root, db_path=self.test_db, session=self.session)
        self.assertIn("1 items reported by you", my_frame.count_lbl.cget("text"))
        children = my_frame.tree.get_children()
        self.assertEqual(len(children), 1)
        my_frame.destroy()

    def test_campus_connect_app_initialization(self) -> None:
        """Verify main CampusConnectApp controller initializes and boots views."""
        app = CampusConnectApp(root=self.root, db_path=self.test_db)
        self.assertIsNotNone(app.current_view)
        self.assertIsInstance(app.current_view, AuthWindow)

        # Simulate login transition
        app.show_main_dashboard(self.student)
        from gui.main_window import MainWindow
        self.assertIsInstance(app.current_view, MainWindow)

        # Simulate logout transition
        app.show_auth_view()
        self.assertIsInstance(app.current_view, AuthWindow)


if __name__ == "__main__":
    unittest.main()
