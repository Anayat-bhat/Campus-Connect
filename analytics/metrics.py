"""
CampusConnect: Data Analytics & KPI Metrics Engine
Extracts operational data from SQLite and computes summary statistics, recovery rates,
category distributions, and location hotspots using Pandas.
"""

from typing import Optional, Dict, Any, List, Tuple
import sqlite3
import pandas as pd
from database.connection import get_connection


class AnalyticsMetrics:
    """Computes operational KPIs and aggregation datasets from database."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path

    def get_items_dataframe(self) -> pd.DataFrame:
        """Fetch all items as a pandas DataFrame."""
        conn = get_connection(self.db_path)
        try:
            query = """
                SELECT id, type, user_id, title, category, description,
                       event_date, location, status, created_at
                FROM items
            """
            df = pd.read_sql_query(query, conn)
            return df
        finally:
            conn.close()

    def get_summary_kpis(self) -> Dict[str, Any]:
        """
        Compute high-level summary KPIs:
        - Total items reported
        - Lost count
        - Found count
        - Returned count
        - Active pending claims count
        - Recovery / Resolution Rate (%)
        """
        df = self.get_items_dataframe()
        if df.empty:
            return {
                "total_items": 0,
                "lost_items": 0,
                "found_items": 0,
                "returned_items": 0,
                "open_items": 0,
                "pending_claims": 0,
                "recovery_rate": 0.0,
            }

        total = len(df)
        lost = int((df["type"] == "LOST").sum())
        found = int((df["type"] == "FOUND").sum())
        returned = int((df["status"] == "RETURNED").sum())
        open_items = int((df["status"] == "OPEN").sum())
        pending = int((df["status"] == "CLAIM_PENDING").sum())

        # Recovery rate: percentage of found items that were successfully returned
        recovery_rate = (returned / found * 100.0) if found > 0 else 0.0

        return {
            "total_items": total,
            "lost_items": lost,
            "found_items": found,
            "returned_items": returned,
            "open_items": open_items,
            "pending_claims": pending,
            "recovery_rate": round(recovery_rate, 1),
        }

    def get_category_distribution(self) -> pd.Series:
        """Return counts of items by category sorted descending."""
        df = self.get_items_dataframe()
        if df.empty:
            return pd.Series(dtype=int)
        return df["category"].value_counts()

    def get_location_hotspots(self, top_n: int = 5) -> pd.Series:
        """Return top campus locations where items were lost or found."""
        df = self.get_items_dataframe()
        if df.empty:
            return pd.Series(dtype=int)
        # Normalize whitespace and case for grouping
        cleaned_locs = df["location"].astype(str).str.strip().str.title()
        return cleaned_locs.value_counts().head(top_n)

    def get_status_distribution(self) -> pd.Series:
        """Return distribution of item statuses (OPEN, CLAIM_PENDING, RETURNED)."""
        df = self.get_items_dataframe()
        if df.empty:
            return pd.Series(dtype=int)
        return df["status"].value_counts()
