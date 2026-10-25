"""
CampusConnect: Matplotlib Visualization Chart Builder
Generates publication-quality charts for category distribution, location hotspots,
and resolution status breakdowns.
"""

from typing import Optional
import matplotlib
# Use Agg backend for headless / embedded Tkinter rendering
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd

from analytics.metrics import AnalyticsMetrics


CHART_COLORS = [
    "#2563eb",  # Blue
    "#10b981",  # Emerald Green
    "#f59e0b",  # Amber
    "#8b5cf6",  # Purple
    "#ef4444",  # Red
    "#06b6d4",  # Cyan
    "#64748b",  # Slate
]


class ChartBuilder:
    """Builds clean, modern Matplotlib figures for analytics dashboard."""

    def __init__(self, metrics: Optional[AnalyticsMetrics] = None, db_path: Optional[str] = None) -> None:
        self.metrics = metrics if metrics is not None else AnalyticsMetrics(db_path)

    def create_category_donut(self) -> Figure:
        """Generate donut chart for item category distribution."""
        fig, ax = plt.subplots(figsize=(5, 3.8), dpi=100)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        cats = self.metrics.get_category_distribution()
        if cats.empty:
            ax.text(0.5, 0.5, "No category data available yet", ha="center", va="center", color="#64748b", fontsize=11)
            ax.axis("off")
            fig.tight_layout()
            return fig

        colors = CHART_COLORS[:len(cats)]
        wedges, texts, autotexts = ax.pie(
            cats.values,
            labels=cats.index,
            autopct="%1.1f%%",
            startangle=140,
            colors=colors,
            pctdistance=0.75,
            textprops={"fontsize": 8, "color": "#1e293b"},
            wedgeprops={"width": 0.45, "edgecolor": "#ffffff", "linewidth": 2}
        )
        for autotext in autotexts:
            autotext.set_color("#ffffff")
            autotext.set_weight("bold")
            autotext.set_fontsize(8)

        ax.set_title("Items by Category", fontsize=12, fontweight="bold", pad=12, color="#0f172a")
        fig.tight_layout()
        return fig

    def create_location_bar(self) -> Figure:
        """Generate horizontal bar chart for campus location hotspots."""
        fig, ax = plt.subplots(figsize=(5, 3.8), dpi=100)
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#ffffff")

        locs = self.metrics.get_location_hotspots(top_n=6)
        if locs.empty:
            ax.text(0.5, 0.5, "No location data available yet", ha="center", va="center", color="#64748b", fontsize=11)
            ax.axis("off")
            fig.tight_layout()
            return fig

        # Plot horizontal bars
        y_positions = range(len(locs))
        bars = ax.barh(y_positions, locs.values, color="#2563eb", height=0.55, edgecolor="none")
        ax.set_yticks(y_positions)
        ax.set_yticklabels(locs.index, fontsize=9, color="#1e293b")
        ax.invert_yaxis()  # Top location at top

        # Remove chart borders for modern clean look
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color("#cbd5e1")
        ax.xaxis.grid(True, linestyle="--", alpha=0.5, color="#e2e8f0")
        ax.set_axisbelow(True)

        # Bar value annotations
        for bar in bars:
            width = bar.get_width()
            ax.text(width + 0.1, bar.get_y() + bar.get_height() / 2, f"{int(width)}",
                    va="center", ha="left", fontsize=8, fontweight="bold", color="#2563eb")

        ax.set_title("Campus Location Hotspots", fontsize=12, fontweight="bold", pad=12, color="#0f172a")
        ax.set_xlabel("Report Count", fontsize=9, color="#64748b")
        fig.tight_layout()
        return fig

    def create_overview_dashboard(self) -> Figure:
        """Generate a 2-panel composite figure showing Category and Location analysis side-by-side."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 3.8), dpi=100)
        fig.patch.set_facecolor("#ffffff")
        ax1.set_facecolor("#ffffff")
        ax2.set_facecolor("#ffffff")

        # Left Panel: Category Donut
        cats = self.metrics.get_category_distribution()
        if not cats.empty:
            colors = CHART_COLORS[:len(cats)]
            wedges, texts, autotexts = ax1.pie(
                cats.values,
                labels=cats.index,
                autopct="%1.0f%%",
                startangle=140,
                colors=colors,
                pctdistance=0.75,
                textprops={"fontsize": 8, "color": "#1e293b"},
                wedgeprops={"width": 0.45, "edgecolor": "#ffffff", "linewidth": 2}
            )
            for autotext in autotexts:
                autotext.set_color("#ffffff")
                autotext.set_weight("bold")
                autotext.set_fontsize(7.5)
            ax1.set_title("Category Distribution", fontsize=11, fontweight="bold", color="#0f172a", pad=10)
        else:
            ax1.text(0.5, 0.5, "No category records", ha="center", va="center", color="#64748b")
            ax1.axis("off")

        # Right Panel: Location Hotspots
        locs = self.metrics.get_location_hotspots(top_n=5)
        if not locs.empty:
            y_positions = range(len(locs))
            bars = ax2.barh(y_positions, locs.values, color="#3b82f6", height=0.55)
            ax2.set_yticks(y_positions)
            ax2.set_yticklabels(locs.index, fontsize=8.5, color="#1e293b")
            ax2.invert_yaxis()
            for spine in ["top", "right", "left"]:
                ax2.spines[spine].set_visible(False)
            ax2.spines["bottom"].set_color("#cbd5e1")
            ax2.xaxis.grid(True, linestyle="--", alpha=0.5, color="#e2e8f0")
            ax2.set_axisbelow(True)

            for bar in bars:
                width = bar.get_width()
                ax2.text(width + 0.1, bar.get_y() + bar.get_height() / 2, f"{int(width)}",
                         va="center", ha="left", fontsize=8, fontweight="bold", color="#1d4ed8")

            ax2.set_title("Campus Hotspots", fontsize=11, fontweight="bold", color="#0f172a", pad=10)
            ax2.set_xlabel("Items", fontsize=8, color="#64748b")
        else:
            ax2.text(0.5, 0.5, "No location records", ha="center", va="center", color="#64748b")
            ax2.axis("off")

        fig.tight_layout()
        return fig
