"""
CampusConnect: Presentation GUI Package
"""

from gui.styles import apply_theme, COLORS, FONTS
from gui.auth_window import AuthWindow
from gui.main_window import MainWindow
from gui.search_frame import SearchFrame
from gui.report_item_frame import ReportItemFrame
from gui.my_items_frame import MyItemsFrame
from gui.item_details_dialog import ItemDetailsDialog
from gui.match_dialog import MatchesDialog

__all__ = [
    "apply_theme",
    "COLORS",
    "FONTS",
    "AuthWindow",
    "MainWindow",
    "SearchFrame",
    "ReportItemFrame",
    "MyItemsFrame",
    "ItemDetailsDialog",
    "MatchesDialog",
]
