"""
CampusConnect: Smart Matches Dialog
Displays ranked counterpart item matches with explainable confidence scores
and factor-by-factor breakdown.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from models.item import Item
from services.matching_service import MatchingService, MatchResult
from database.repository import ItemRepository


class MatchesDialog(tk.Toplevel):
    """Modal dialog displaying AI/algorithmic matches with explainability breakdown."""

    def __init__(
        self,
        parent: tk.Widget,
        source_item: Item,
        db_path: Optional[str] = None,
        on_view_item_callback: Optional[Callable[[Item], None]] = None
    ) -> None:
        super().__init__(parent)
        self.source_item = source_item
        self.db_path = db_path
        self.on_view_item_callback = on_view_item_callback
        self.matching_service = MatchingService(db_path=db_path)
        self.item_repo = ItemRepository(db_path)

        self.title(f"Smart Match Candidates — #{source_item.id} {source_item.title}")
        self.geometry("700x520")
        self.minsize(620, 440)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_matches()

    def _build_ui(self) -> None:
        """Construct the matching results interface."""
        container = ttk.Frame(self, padding="20")
        container.pack(fill="both", expand=True)

        # Header
        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 12))

        counterpart_label = "Found" if self.source_item.type == "LOST" else "Lost"
        ttk.Label(
            header,
            text=f"🤖 Potential {counterpart_label} Matches",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=f"Scored against reported items using Category, Keywords, Location, and Date proximity.",
            font=("Segoe UI", 9),
            foreground="#64748b"
        ).pack(anchor="w", pady=(2, 0))

        # Matches List Frame
        list_card = ttk.Frame(container, style="Card.TFrame", padding="8")
        list_card.pack(fill="both", expand=True, pady=(0, 12))

        columns = ("score", "id", "title", "category", "location", "date", "explanation")
        self.tree = ttk.Treeview(list_card, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("score", text="Score", anchor="center")
        self.tree.heading("id", text="#", anchor="center")
        self.tree.heading("title", text="Title", anchor="w")
        self.tree.heading("category", text="Category", anchor="w")
        self.tree.heading("location", text="Location", anchor="w")
        self.tree.heading("date", text="Date", anchor="center")
        self.tree.heading("explanation", text="Match Rationale", anchor="w")

        self.tree.column("score", width=65, minwidth=55, anchor="center")
        self.tree.column("id", width=40, minwidth=35, anchor="center")
        self.tree.column("title", width=140, minwidth=100, anchor="w")
        self.tree.column("category", width=110, minwidth=90, anchor="w")
        self.tree.column("location", width=110, minwidth=90, anchor="w")
        self.tree.column("date", width=85, minwidth=75, anchor="center")
        self.tree.column("explanation", width=260, minwidth=180, anchor="w")

        scrollbar = ttk.Scrollbar(list_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Action footer
        footer = ttk.Frame(container)
        footer.pack(fill="x")

        view_btn = ttk.Button(
            footer,
            text="Inspect Matched Item",
            style="Primary.TButton",
            command=self._on_inspect_selected
        )
        view_btn.pack(side="left", padx=(0, 8))

        close_btn = ttk.Button(
            footer,
            text="Close",
            style="Secondary.TButton",
            command=self.destroy
        )
        close_btn.pack(side="right")

    def _load_matches(self) -> None:
        """Execute matching algorithm and render rows."""
        matches = self.matching_service.find_matches_for_item(self.source_item, min_threshold=30.0, limit=15)
        self.match_map = {}

        if not matches:
            self.tree.insert("", "end", values=("0%", "-", "No potential matches found at this time.", "-", "-", "-", "Threshold not met."))
            return

        for m in matches:
            target = m.target_item
            self.match_map[str(target.id)] = target
            score_text = f"{int(round(m.overall_score))}%"
            self.tree.insert(
                "",
                "end",
                iid=str(target.id),
                values=(
                    score_text,
                    f"#{target.id}",
                    target.title,
                    target.category,
                    target.location,
                    target.event_date,
                    m.explanation
                )
            )

    def _on_inspect_selected(self) -> None:
        selected = self.tree.selection()
        if not selected or selected[0] not in self.match_map:
            messagebox.showinfo("Select Item", "Please select a matched item to inspect.", parent=self)
            return

        target_item = self.match_map[selected[0]]
        if self.on_view_item_callback:
            self.destroy()
            self.on_view_item_callback(target_item)
