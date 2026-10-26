"""
CampusConnect: Modern GUI Styling & Theme Configuration
Provides a cohesive visual palette, typography, and TTK component styles.
"""

import tkinter as tk
from tkinter import ttk


# Design System Color Palette (Signature #fcf8f9 and #a21721)
COLORS = {
    "bg_main": "#fcf8f9",        # Porcelain Rose
    "bg_card": "#ffffff",        # Pure White
    "bg_sidebar": "#1c0507",     # Deep Velvet Burgundy
    "primary": "#a21721",        # Crimson Ruby
    "primary_hover": "#851119",  # Deep Crimson
    "secondary": "#703b40",      # Dusty Rose Slate
    "secondary_hover": "#542c30",# Muted Plum
    "success": "#1b7a48",        # Forest Emerald
    "success_hover": "#145c36",  # Deep Emerald
    "danger": "#a21721",         # Crimson Danger
    "danger_hover": "#851119",   # Dark Crimson
    "warning": "#b86200",        # Warm Amber
    "text_primary": "#1f0709",   # Deep Obsidian Brown
    "text_secondary": "#5e3034", # Warm Crimson Slate
    "text_muted": "#8e6266",     # Muted Rose
    "border": "#ebdada",         # Soft Rose Border
    "border_focus": "#a21721",   # Crimson Focus
    "table_header": "#f7edee",   # Soft Crimson Wash
    "table_alt_row": "#fcf8f9",  # Porcelain Wash
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
        background=[("active", COLORS["primary_hover"]), ("disabled", "#e5b7ba")],
        foreground=[("disabled", "#ffffff")]
    )

    style.configure(
        "Secondary.TButton",
        background="#ebdada",
        foreground=COLORS["text_primary"],
        font=FONTS["button"],
        padding=(12, 7),
        borderwidth=0,
    )
    style.map("Secondary.TButton", background=[("active", "#dfc5c7")])

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
        background="#ebdada",
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
