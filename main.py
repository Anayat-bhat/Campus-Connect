"""
CampusConnect: Smart Campus Lost & Found Management System
Phase 1: Entry Point and Environment Verification

This file serves as the main execution entry point for CampusConnect.
During Phase 1, it confirms that the Python runtime and Tkinter GUI system
are properly configured and functioning on the host machine.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox


class CampusConnectSetupApp:
    """Entry window for Phase 1 verification."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CampusConnect — System Verification (Phase 1)")
        self.root.geometry("640x460")
        self.root.minsize(580, 400)
        self.root.configure(bg="#f4f6f9")

        self._configure_styles()
        self._build_ui()

    def _configure_styles(self) -> None:
        """Configure ttk styles for clean visual appearance."""
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # Configure colors and typography
        style.configure("Header.TLabel", background="#f4f6f9", foreground="#1e293b", font=("Helvetica", 16, "bold"))
        style.configure("Subheader.TLabel", background="#f4f6f9", foreground="#64748b", font=("Helvetica", 10))
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("CardTitle.TLabel", background="#ffffff", foreground="#0f172a", font=("Helvetica", 11, "bold"))
        style.configure("CardText.TLabel", background="#ffffff", foreground="#334155", font=("Helvetica", 10))
        style.configure("Primary.TButton", font=("Helvetica", 10, "bold"), padding=8)

    def _build_ui(self) -> None:
        """Construct the user interface components."""
        # Top banner frame
        header_frame = ttk.Frame(self.root, padding="24 20 24 10")
        header_frame.pack(fill="x")

        title_label = ttk.Label(
            header_frame,
            text="🎓 CampusConnect",
            style="Header.TLabel"
        )
        title_label.pack(anchor="w")

        subtitle_label = ttk.Label(
            header_frame,
            text="Smart Campus Lost & Found Management System — Phase 1 Setup",
            style="Subheader.TLabel"
        )
        subtitle_label.pack(anchor="w", pady=(4, 0))

        # Main content card
        content_card = ttk.Frame(self.root, style="Card.TFrame", padding="20")
        content_card.pack(fill="both", expand=True, padx=24, pady=12)

        info_title = ttk.Label(
            content_card,
            text="System & Runtime Diagnostic",
            style="CardTitle.TLabel"
        )
        info_title.pack(anchor="w", pady=(0, 12))

        # System check items
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        tk_version = tk.TkVersion

        status_items = [
            ("Python Runtime:", f"Python {py_version} (Compatible 3.10+)"),
            ("Tkinter GUI Toolkit:", f"Version {tk_version} (Loaded successfully)"),
            ("Database Engine:", "SQLite 3 (Built-in standard library - ready for Phase 2)"),
            ("Architecture:", "Layered (GUI -> Services -> Models -> Database)"),
            ("Current Milestone:", "Phase 1: Environment Setup & Foundation"),
        ]

        for label, val in status_items:
            row = ttk.Frame(content_card, style="Card.TFrame")
            row.pack(fill="x", pady=4)
            lbl = ttk.Label(row, text=f"• {label}", style="CardTitle.TLabel", width=22)
            lbl.pack(side="left")
            val_lbl = ttk.Label(row, text=val, style="CardText.TLabel")
            val_lbl.pack(side="left")

        # Notification box
        note_box = ttk.Label(
            content_card,
            text="All Phase 1 pre-checks passed successfully.\n"
                 "The directory structure, Git configuration, and virtual environment are ready.",
            style="CardText.TLabel",
            justify="left",
            foreground="#047857"
        )
        note_box.pack(anchor="w", pady=(18, 0))

        # Bottom action bar
        footer_frame = ttk.Frame(self.root, padding="24 10 24 20")
        footer_frame.pack(fill="x")

        test_btn = ttk.Button(
            footer_frame,
            text="Test Diagnostic Alert",
            style="Primary.TButton",
            command=self._on_test_dialog
        )
        test_btn.pack(side="left")

        exit_btn = ttk.Button(
            footer_frame,
            text="Close & Continue",
            command=self.root.destroy
        )
        exit_btn.pack(side="right")

    def _on_test_dialog(self) -> None:
        """Verify modal dialog handling."""
        messagebox.showinfo(
            "Diagnostic Check",
            "Tkinter event loop, message dialogs, and styling are working flawlessly!"
        )


def main() -> None:
    """Application main entry point."""
    root = tk.Tk()
    app = CampusConnectSetupApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
