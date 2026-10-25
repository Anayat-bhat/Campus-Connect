"""
CampusConnect: Smart Campus Lost & Found Management System
Main Application Entry Point

Bootstraps SQLite database initialization, configures modern TTK theme,
and manages dynamic transitions between Authentication (Sign In/Register)
and the Main Dashboard (Browse, Search, Report, Manage).
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from database.connection import DEFAULT_DB_PATH, init_database, seed_default_admin
from gui.styles import apply_theme
from gui.auth_window import AuthWindow
from gui.main_window import MainWindow
from models.user import User
from services.session_manager import session_manager


class CampusConnectApp:
    """Master application controller coordinating views and active sessions."""

    def __init__(self, root: tk.Tk, db_path: Optional[str] = None) -> None:
        self.root = root
        self.db_path = db_path if db_path is not None else DEFAULT_DB_PATH

        self.root.title("CampusConnect — Smart Lost & Found")
        self.root.geometry("1024x720")
        self.root.minsize(840, 580)

        # Apply cohesive design system theme
        apply_theme(self.root)

        # Ensure database is initialized and seeded
        self._bootstrap_database()

        # View container
        self.current_view: Optional[ttk.Frame] = None

        # Start with authentication view
        self.show_auth_view()

    def _bootstrap_database(self) -> None:
        """Initialize database tables and default administrator if missing."""
        try:
            if not os.path.exists(self.db_path):
                init_database(self.db_path)
            seed_default_admin(self.db_path)
        except Exception as e:
            messagebox.showerror(
                "Database Initialization Error",
                f"Failed to initialize SQLite database:\n{e}"
            )

    def show_auth_view(self) -> None:
        """Display the Sign-In / Register authentication screen."""
        if self.current_view is not None:
            self.current_view.destroy()

        self.current_view = AuthWindow(
            parent=self.root,
            db_path=self.db_path,
            session=session_manager,
            on_login_success=self.show_main_dashboard
        )
        self.current_view.pack(fill="both", expand=True)

    def show_main_dashboard(self, user: User) -> None:
        """Display the authenticated main application dashboard."""
        if self.current_view is not None:
            self.current_view.destroy()

        self.current_view = MainWindow(
            parent=self.root,
            db_path=self.db_path,
            session=session_manager,
            on_logout=self.show_auth_view
        )
        self.current_view.pack(fill="both", expand=True)


def main() -> None:
    """Application main entry point."""
    root = tk.Tk()
    app = CampusConnectApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
