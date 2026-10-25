"""
CampusConnect: Claims Management & Verification Frame
Allows students to track their filed claims and provides administrators
with a queue to inspect proof details, approve handovers, or reject claims.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Callable
from services.claim_service import ClaimService, ClaimWorkflowError
from database.repository import ClaimRepository, ItemRepository
from services.session_manager import SessionManager, session_manager as default_session_manager


class ClaimsManagerFrame(ttk.Frame):
    """View component for managing and reviewing claims."""

    def __init__(
        self,
        parent: tk.Widget,
        db_path: Optional[str] = None,
        session: Optional[SessionManager] = None,
        on_claim_updated: Optional[Callable[[], None]] = None
    ) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.session = session if session is not None else default_session_manager
        self.on_claim_updated = on_claim_updated
        self.claim_service = ClaimService(db_path=db_path)
        self.claim_repo = ClaimRepository(db_path)
        self.item_repo = ItemRepository(db_path)

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        """Construct the claim management interface."""
        header_card = ttk.Frame(self, style="Card.TFrame", padding="16")
        header_card.pack(fill="x", padx=16, pady=(16, 8))

        is_admin = self.session.is_admin()
        header_title = "🛡️ Campus Claim Verification Queue" if is_admin else "📋 My Submitted Claims"
        ttk.Label(
            header_card,
            text=header_title,
            font=("Segoe UI", 12, "bold"),
            background="#ffffff"
        ).pack(side="left")

        self.count_lbl = ttk.Label(
            header_card,
            text="",
            font=("Segoe UI", 9),
            foreground="#64748b",
            background="#ffffff"
        )
        self.count_lbl.pack(side="left", padx=(12, 0))

        # Table Card
        table_card = ttk.Frame(self, style="Card.TFrame", padding="12")
        table_card.pack(fill="both", expand=True, padx=16, pady=8)

        if is_admin:
            columns = ("claim_id", "item_id", "item_title", "claimant", "proof", "submitted_at")
            self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")

            self.tree.heading("claim_id", text="Claim #", anchor="center")
            self.tree.heading("item_id", text="Item #", anchor="center")
            self.tree.heading("item_title", text="Item Title", anchor="w")
            self.tree.heading("claimant", text="Claimant", anchor="w")
            self.tree.heading("proof", text="Private Proof Description", anchor="w")
            self.tree.heading("submitted_at", text="Submitted Date", anchor="center")

            self.tree.column("claim_id", width=60, minwidth=50, anchor="center")
            self.tree.column("item_id", width=55, minwidth=45, anchor="center")
            self.tree.column("item_title", width=160, minwidth=120, anchor="w")
            self.tree.column("claimant", width=140, minwidth=110, anchor="w")
            self.tree.column("proof", width=280, minwidth=180, anchor="w")
            self.tree.column("submitted_at", width=110, minwidth=90, anchor="center")
        else:
            columns = ("claim_id", "item_title", "proof", "status", "submitted_at", "review_notes")
            self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")

            self.tree.heading("claim_id", text="Claim #", anchor="center")
            self.tree.heading("item_title", text="Item Title", anchor="w")
            self.tree.heading("proof", text="My Proof Description", anchor="w")
            self.tree.heading("status", text="Status", anchor="center")
            self.tree.heading("submitted_at", text="Submitted Date", anchor="center")
            self.tree.heading("review_notes", text="Review Feedback", anchor="w")

            self.tree.column("claim_id", width=60, minwidth=50, anchor="center")
            self.tree.column("item_title", width=170, minwidth=120, anchor="w")
            self.tree.column("proof", width=220, minwidth=150, anchor="w")
            self.tree.column("status", width=95, minwidth=80, anchor="center")
            self.tree.column("submitted_at", width=110, minwidth=90, anchor="center")
            self.tree.column("review_notes", width=200, minwidth=120, anchor="w")

        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("APPROVED", foreground="#15803d")
        self.tree.tag_configure("REJECTED", foreground="#b91c1c")
        self.tree.tag_configure("PENDING", foreground="#d97706")

        # Footer Action Bar
        footer = ttk.Frame(self, padding="16 6 16 12")
        footer.pack(fill="x")

        if is_admin:
            approve_btn = ttk.Button(
                footer,
                text="✓ Approve Handover",
                style="Success.TButton",
                command=self._on_approve_claim
            )
            approve_btn.pack(side="left", padx=(0, 8))

            reject_btn = ttk.Button(
                footer,
                text="✗ Reject Claim",
                style="Danger.TButton",
                command=self._on_reject_claim
            )
            reject_btn.pack(side="left", padx=(0, 8))

        refresh_btn = ttk.Button(footer, text="↻ Refresh", style="Secondary.TButton", command=self.refresh)
        refresh_btn.pack(side="left")

    def refresh(self) -> None:
        """Load fresh claim data based on role."""
        for child in self.tree.get_children():
            self.tree.delete(child)

        user = self.session.current_user
        if not user:
            self.count_lbl.configure(text="Sign in to view claims.")
            return

        if self.session.is_admin():
            pending_claims = self.claim_service.list_pending_claims_for_review()
            self.count_lbl.configure(text=f"{len(pending_claims)} claims pending verification")
            for c in pending_claims:
                self.tree.insert(
                    "",
                    "end",
                    iid=str(c["claim_id"]),
                    values=(
                        f"#{c['claim_id']}",
                        f"#{c['item_id']}",
                        c["item_title"],
                        f"{c['claimant_name']} ({c['claimant_email']})",
                        c["proof_description"],
                        c["submitted_at"][:10] if c.get("submitted_at") else ""
                    ),
                    tags=("PENDING",)
                )
        else:
            my_claims = self.claim_repo.list_by_claimant(user.id)
            self.count_lbl.configure(text=f"{len(my_claims)} total claims filed by you")
            for c in my_claims:
                item = self.item_repo.get_by_id(c.item_id)
                item_title = item.title if item else f"Item #{c.item_id}"
                self.tree.insert(
                    "",
                    "end",
                    iid=str(c.id),
                    values=(
                        f"#{c.id}",
                        item_title,
                        c.proof_description,
                        c.status,
                        c.submitted_at[:10] if c.submitted_at else "",
                        c.review_notes or "Under Review"
                    ),
                    tags=(c.status,)
                )

    def _on_approve_claim(self) -> None:
        """Admin approves claim and executes handover."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Claim", "Please select a pending claim from the queue to approve.", parent=self)
            return

        claim_id = int(selected[0])
        notes = simpledialog.askstring(
            "Approve & Hand Over",
            f"Enter handover verification notes for Claim #{claim_id} (optional):",
            parent=self
        )
        if notes is None:
            return  # Cancelled

        reviewer = self.session.current_user
        reviewer_id = reviewer.id if reviewer else 1

        try:
            self.claim_service.approve_claim(
                claim_id=claim_id,
                reviewer_id=reviewer_id,
                verification_notes=notes or "Verified identity and ownership proof."
            )
            messagebox.showinfo(
                "Handover Recorded",
                f"Claim #{claim_id} approved!\n"
                f"The item has been marked as RETURNED and recorded in audit logs.",
                parent=self
            )
            self.refresh()
            if self.on_claim_updated:
                self.on_claim_updated()
        except Exception as err:
            messagebox.showerror("Error", f"Failed to approve claim: {err}", parent=self)

    def _on_reject_claim(self) -> None:
        """Admin rejects invalid claim."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Select Claim", "Please select a claim from the queue to reject.", parent=self)
            return

        claim_id = int(selected[0])
        reason = simpledialog.askstring(
            "Reject Claim",
            f"Enter rejection reason for Claim #{claim_id}:",
            parent=self
        )
        if reason is None:
            return  # Cancelled

        reviewer = self.session.current_user
        reviewer_id = reviewer.id if reviewer else 1

        try:
            self.claim_service.reject_claim(
                claim_id=claim_id,
                reviewer_id=reviewer_id,
                reason=reason or "Proof did not match item characteristics."
            )
            messagebox.showinfo("Claim Rejected", f"Claim #{claim_id} was rejected.", parent=self)
            self.refresh()
            if self.on_claim_updated:
                self.on_claim_updated()
        except Exception as err:
            messagebox.showerror("Error", f"Failed to reject claim: {err}", parent=self)
