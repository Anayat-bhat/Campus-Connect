"""
Unit Tests for Phase 8: Data Analytics & Matplotlib Visualizations
Verifies Pandas DataFrame ingestion, KPI calculations, and Matplotlib chart builders.
"""

import os
import sqlite3
import unittest
import tkinter as tk
import matplotlib.pyplot as plt

from database.connection import DEFAULT_SCHEMA_PATH, seed_default_admin
from database.repository import ItemRepository, UserRepository
from models.item import Item
from analytics.metrics import AnalyticsMetrics
from analytics.chart_builder import ChartBuilder
from gui.analytics_frame import AnalyticsFrame
from services.session_manager import SessionManager


class TestAnalytics(unittest.TestCase):
    """Test suite for Phase 8 Analytics & Chart generation."""

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
        self.test_db = os.path.join(os.path.dirname(__file__), "test_analytics.db")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        conn = sqlite3.connect(self.test_db)
        conn.execute("PRAGMA foreign_keys = ON;")
        with open(DEFAULT_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.close()

        seed_default_admin(self.test_db)

        self.user_repo = UserRepository(self.test_db)
        self.item_repo = ItemRepository(self.test_db)
        self.admin = self.user_repo.get_by_username("admin")

        # Insert representative test items
        items = [
            Item(None, "LOST", self.admin.id, "Scientific Calculator", "Electronics", "Casio fx-991", "2026-10-20", "Library 2nd Floor", None, "OPEN"),
            Item(None, "LOST", self.admin.id, "Student ID Card", "Identity cards", "Blue lanyard", "2026-10-21", "Block A", None, "OPEN"),
            Item(None, "FOUND", self.admin.id, "Dell Charger", "Electronics", "Type-C black", "2026-10-22", "Library 2nd Floor", None, "RETURNED"),
            Item(None, "FOUND", self.admin.id, "Water Bottle", "Personal belongings", "Metal bottle", "2026-10-23", "Cafeteria", None, "CLAIM_PENDING"),
            Item(None, "FOUND", self.admin.id, "Notebook", "Books and stationery", "Math notes", "2026-10-24", "Block A", None, "RETURNED"),
        ]
        for it in items:
            self.item_repo.create(it)

        self.metrics = AnalyticsMetrics(self.test_db)
        self.builder = ChartBuilder(self.metrics)

    def tearDown(self) -> None:
        plt.close("all")
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_dataframe_generation(self) -> None:
        """Verify items are correctly read into a Pandas DataFrame."""
        df = self.metrics.get_items_dataframe()
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 5)
        self.assertIn("category", df.columns)
        self.assertIn("location", df.columns)

    def test_summary_kpis(self) -> None:
        """Verify KPI computations including recovery rate calculation."""
        kpis = self.metrics.get_summary_kpis()
        self.assertEqual(kpis["total_items"], 5)
        self.assertEqual(kpis["lost_items"], 2)
        self.assertEqual(kpis["found_items"], 3)
        self.assertEqual(kpis["returned_items"], 2)
        self.assertEqual(kpis["pending_claims"], 1)
        # 2 returned out of 3 found = 66.7%
        self.assertAlmostEqual(kpis["recovery_rate"], 66.7, places=1)

    def test_category_distribution(self) -> None:
        """Verify item category aggregation Series."""
        cats = self.metrics.get_category_distribution()
        self.assertGreaterEqual(len(cats), 4)
        self.assertEqual(cats["Electronics"], 2)

    def test_location_hotspots(self) -> None:
        """Verify location hotspot frequency rankings."""
        locs = self.metrics.get_location_hotspots(top_n=3)
        self.assertIn("Library 2Nd Floor", locs.index)
        self.assertIn("Block A", locs.index)

    def test_chart_builder_figures(self) -> None:
        """Verify Matplotlib chart figure creation."""
        fig_donut = self.builder.create_category_donut()
        self.assertIsNotNone(fig_donut)
        self.assertGreater(len(fig_donut.axes), 0)

        fig_bar = self.builder.create_location_bar()
        self.assertIsNotNone(fig_bar)
        self.assertGreater(len(fig_bar.axes), 0)

        fig_overview = self.builder.create_overview_dashboard()
        self.assertIsNotNone(fig_overview)
        self.assertEqual(len(fig_overview.axes), 2)

    def test_analytics_frame_integration(self) -> None:
        """Verify AnalyticsFrame creates KPI widgets and embeds Matplotlib canvas."""
        if not self.tk_available:
            self.skipTest("Tkinter display not available.")

        session = SessionManager()
        session.login(self.admin)

        frame = AnalyticsFrame(parent=self.root, db_path=self.test_db, session=session)
        self.assertEqual(frame.kpi_labels["total"].cget("text"), "5")
        self.assertEqual(frame.kpi_labels["returned"].cget("text"), "2")
        self.assertIsNotNone(frame.canvas)
        frame.destroy()


if __name__ == "__main__":
    unittest.main()
