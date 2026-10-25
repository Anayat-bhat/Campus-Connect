"""
CampusConnect: Modern GUI Styling & Theme Configuration
Provides a cohesive visual palette, typography, and TTK component styles.
"""

import tkinter as tk
from tkinter import ttk


# Design System Color Palette
COLORS = {
    "bg_main": "#f8fafc",        # Slate 50
    "bg_card": "#ffffff",        # White
    "bg_sidebar": "#0f172a",     # Slate 900
    "primary": "#2563eb",        # Blue 600
    "primary_hover": "#1d4ed8",  # Blue 700
    "secondary": "#64748b",      # Slate 500
    "secondary_hover": "#475569",# Slate 600
    "success": "#16a34a",        # Green 600
    "success_hover": "#15803d",  # Green 700
    "danger": "#dc2626",         # Red 600
    "danger_hover": "#b91c1c",   # Red 700
    "warning": "#d97706",        # Amber 600
    "text_primary": "#0f172a",   # Slate 900
    "text_secondary": "#475569", # Slate 600
    "text_muted": "#94a3b8",     # Slate 400
    "border": "#e2e8f0",         # Slate 200
    "border_focus": "#3b82f6",   # Blue 500
    "table_header": "#f1f5f9",   # Slate 100
    "table_alt_row": "#f8fafc",  # Slate 50
}

FONTS = {
    "h1": ("Segoe UI", 18, "bold"),
    "h2": ("Segoe UI", 14, "bold"),
    "h3": ("Segoe UI", 12, "bold"),
    "body": ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "caption": ("Segoe UI", 9),
    "button": ("Segoe UI", 10, "bold"),
}


def apply_theme(root: tk.Tk) -> ttk.Style:
    """Configure modern TTK widget styling."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # Base background
    root.configure(bg=COLORS["bg_main"])

    # TTK Frame styles
    style.configure("TFrame", background=COLORS["bg_main"])
    style.configure("Card.TFrame", background=COLORS["bg_card"], relief="flat")
    style.configure("Sidebar.TFrame", background=COLORS["bg_sidebar"])

    # Labels
    style.configure("TLabel", background=COLORS["bg_main"], foreground=COLORS["text_primary"], font=FONTS["body"])
    style.configure("Card.TLabel", background=COLORS["bg_card"], foreground=COLORS["text_primary"], font=FONTS["body"])
    style.configure("CardTitle.TLabel", background=COLORS["bg_card"], foreground=COLORS["text_primary"], font=FONTS["h3"])
    style.configure("Muted.TLabel", background=COLORS["bg_card"], foreground=COLORS["text_secondary"], font=FONTS["caption"])
    style.configure("Header.TLabel", background=COLORS["bg_main"], foreground=COLORS["text_primary"], font=FONTS["h1"])
    style.configure("Subheader.TLabel", background=COLORS["bg_main"], foreground=COLORS["text_secondary"], font=FONTS["body"])
    style.configure("Brand.TLabel", background=COLORS["bg_sidebar"], foreground="#ffffff", font=FONTS["h2"])
    style.configure("BrandSub.TLabel", background=COLORS["bg_sidebar"], foreground="#94a3b8", font=FONTS["caption"])

    # Buttons
    style.configure(
        "Primary.TButton",
        background=COLORS["primary"],
        foreground="#ffffff",
        font=FONTS["button"],
        padding=(14, 8),
        borderwidth=0,
    )
    style.map(
        "Primary.TButton",
        background=[("active", COLORS["primary_hover"]), ("disabled", "#93c5fd")],
        foreground=[("disabled", "#ffffff")]
    )

    style.configure(
        "Secondary.TButton",
        background="#e2e8f0",
        foreground=COLORS["text_primary"],
        font=FONTS["button"],
        padding=(12, 7),
        borderwidth=0,
    )
    style.map("Secondary.TButton", background=[("active", "#cbd5e1")])

    style.configure(
        "Success.TButton",
        background=COLORS["success"],
        foreground="#ffffff",
        font=FONTS["button"],
        padding=(12, 7),
        borderwidth=0,
    )
    style.map("Success.TButton", background=[("active", COLORS["success_hover"])])

    style.configure(
        "Danger.TButton",
        background=COLORS["danger"],
        foreground="#ffffff",
        font=FONTS["button"],
        padding=(12, 7),
        borderwidth=0,
    )
    style.map("Danger.TButton", background=[("active", COLORS["danger_hover"])])

    # Entry & Combobox
    style.configure("TEntry", padding=6, relief="flat")
    style.configure("TCombobox", padding=5, relief="flat")

    # Notebook (Tabs)
    style.configure("TNotebook", background=COLORS["bg_main"], tabmargins=[2, 5, 2, 0], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background="#e2e8f0",
        foreground=COLORS["text_secondary"],
        padding=[16, 8],
        font=FONTS["body_bold"],
        borderwidth=0
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["primary"])],
        foreground=[("selected", "#ffffff")]
    )

    # Treeview (Data Tables)
    style.configure(
        "Treeview",
        background="#ffffff",
        foreground=COLORS["text_primary"],
        fieldbackground="#ffffff",
        rowheight=32,
        font=FONTS["body"],
        borderwidth=1,
        relief="solid"
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["table_header"],
        foreground=COLORS["text_primary"],
        font=FONTS["body_bold"],
        padding=(6, 8),
        relief="flat"
    )
    style.map("Treeview", background=[("selected", "#dbeafe")], foreground=[("selected", COLORS["primary"])])
    style.map("Treeview.Heading", background=[("active", "#e2e8f0")])

    return style
