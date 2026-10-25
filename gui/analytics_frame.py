"""
CampusConnect: Analytics & Reporting Frame
Interactive dashboard displaying key performance indicators (KPIs) and
embedded Matplotlib charts for campus lost-and-found trends.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from analytics.metrics import AnalyticsMetrics
from analytics.chart_builder import ChartBuilder
from services.session_manager import SessionManager, session_manager as default_session_manager


class AnalyticsFrame(ttk.Frame):
    """View component displaying analytics KPIs and embedded visualizations."""

    def __init__(
        self,
        parent: tk.Widget,
        db_path: Optional[str] = None,
        session: Optional[SessionManager] = None
    ) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.session = session if session is not None else default_session_manager
        self.metrics = AnalyticsMetrics(db_path)
        self.builder = ChartBuilder(self.metrics)

        self.current_chart_mode = "overview"
        self.fig: Optional[plt.Figure] = None
        self.canvas: Optional[FigureCanvasTkAgg] = None

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        """Construct the KPI cards and visualization canvas layout."""
        # Main scrollable or padded container
        self.container = ttk.Frame(self, padding="16")
        self.container.pack(fill="both", expand=True)

        # 1. Header Bar
        header = ttk.Frame(self.container, style="Card.TFrame", padding="16")
        header.pack(fill="x", pady=(0, 12))

        ttk.Label(
            header,
            text="📊 Campus Lost & Found Insights & Analytics",
            font=("Segoe UI", 13, "bold"),
            background="#ffffff"
        ).pack(side="left")

        actions = ttk.Frame(header, style="Card.TFrame")
        actions.pack(side="right")

        export_btn = ttk.Button(
            actions,
            text="📥 Export Chart",
            style="Secondary.TButton",
            command=self._on_export_chart
        )
        export_btn.pack(side="left", padx=(0, 8))

        refresh_btn = ttk.Button(
            actions,
            text="↻ Refresh",
            style="Primary.TButton",
            command=self.refresh
        )
        refresh_btn.pack(side="left")

        # 2. KPI Summary Cards Grid
        self.kpi_frame = ttk.Frame(self.container)
        self.kpi_frame.pack(fill="x", pady=(0, 12))

        # 5 KPI cards
        self.kpi_labels = {}
        cards_meta = [
            ("total", "📦 Total Reports", "#2563eb"),
            ("lost", "🔍 Lost Items", "#dc2626"),
            ("found", "🎁 Found Items", "#059669"),
            ("returned", "✅ Returned to Owner", "#16a34a"),
            ("recovery", "📈 Recovery Rate", "#7c3aed"),
        ]

        for idx, (key, title, color) in enumerate(cards_meta):
            self.kpi_frame.columnconfigure(idx, weight=1)
            card = ttk.Frame(self.kpi_frame, style="Card.TFrame", padding="12")
            card.grid(row=0, column=idx, sticky="ew", padx=4)

            title_lbl = ttk.Label(
                card,
                text=title,
                font=("Segoe UI", 9, "bold"),
                foreground="#64748b",
                background="#ffffff"
            )
            title_lbl.pack(anchor="w")

            val_lbl = ttk.Label(
                card,
                text="0",
                font=("Segoe UI", 16, "bold"),
                foreground=color,
                background="#ffffff"
            )
            val_lbl.pack(anchor="w", pady=(4, 0))
            self.kpi_labels[key] = val_lbl

        # 3. Chart Control Buttons
        ctrl_frame = ttk.Frame(self.container, style="Card.TFrame", padding="10 8")
        ctrl_frame.pack(fill="x", pady=(0, 8))

        ttk.Label(
            ctrl_frame,
            text="Select View:",
            font=("Segoe UI", 9, "bold"),
            background="#ffffff"
        ).pack(side="left", padx=(0, 8))

        self.btn_overview = ttk.Button(
            ctrl_frame,
            text="Dual Dashboard",
            command=lambda: self._set_chart_mode("overview")
        )
        self.btn_overview.pack(side="left", padx=(0, 6))

        self.btn_cat = ttk.Button(
            ctrl_frame,
            text="Category Donut",
            command=lambda: self._set_chart_mode("category")
        )
        self.btn_cat.pack(side="left", padx=(0, 6))

        self.btn_loc = ttk.Button(
            ctrl_frame,
            text="Campus Hotspots",
            command=lambda: self._set_chart_mode("location")
        )
        self.btn_loc.pack(side="left")

        # 4. Canvas Frame
        self.canvas_card = ttk.Frame(self.container, style="Card.TFrame", padding="8")
        self.canvas_card.pack(fill="both", expand=True)

    def _set_chart_mode(self, mode: str) -> None:
        self.current_chart_mode = mode
        self._render_chart()

    def refresh(self) -> None:
        """Fetch fresh metrics, update KPI cards, and redraw the active chart."""
        kpis = self.metrics.get_summary_kpis()

        self.kpi_labels["total"].configure(text=str(kpis["total_items"]))
        self.kpi_labels["lost"].configure(text=str(kpis["lost_items"]))
        self.kpi_labels["found"].configure(text=str(kpis["found_items"]))
        self.kpi_labels["returned"].configure(text=str(kpis["returned_items"]))
        self.kpi_labels["recovery"].configure(text=f"{kpis['recovery_rate']}%")

        self._render_chart()

    def _render_chart(self) -> None:
        """Generate Matplotlib figure and embed on Tkinter canvas."""
        # Close old figure to prevent memory leak
        if self.fig is not None:
            plt.close(self.fig)

        # Clear existing canvas widget
        if self.canvas is not None:
            self.canvas.get_tk_widget().destroy()
            self.canvas = None

        # Build figure according to active mode
        if self.current_chart_mode == "category":
            self.fig = self.builder.create_category_donut()
        elif self.current_chart_mode == "location":
            self.fig = self.builder.create_location_bar()
        else:
            self.fig = self.builder.create_overview_dashboard()

        # Mount on Tkinter canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.canvas_card)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _on_export_chart(self) -> None:
        """Export current figure to PNG or PDF file."""
        if not self.fig:
            return

        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Save Analytics Chart",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF Document", "*.pdf"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                self.fig.savefig(filepath, dpi=300, bbox_inches="tight")
                messagebox.showinfo("Export Successful", f"Chart successfully saved to:\n{filepath}", parent=self)
            except Exception as e:
                messagebox.showerror("Export Failed", f"Could not save chart: {e}", parent=self)

    def destroy(self) -> None:
        """Clean up Matplotlib figures when frame is destroyed."""
        if self.fig is not None:
            plt.close(self.fig)
        super().destroy()
