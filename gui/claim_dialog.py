"""
CampusConnect: Item Claim Submission Dialog
Allows students to submit private distinguishing proof details to claim a found item.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from models.item import Item
from services.claim_service import ClaimService, ClaimWorkflowError
from services.session_manager import SessionManager, session_manager as default_session_manager


class ClaimItemDialog(tk.Toplevel):
    """Modal dialog for submitting ownership claims with proof description."""

    def __init__(
        self,
        parent: tk.Widget,
        item: Item,
        db_path: Optional[str] = None,
        session: Optional[SessionManager] = None,
        on_claim_submitted: Optional[Callable[[int], None]] = None
    ) -> None:
        super().__init__(parent)
        self.item = item
        self.db_path = db_path
        self.session = session if session is not None else default_session_manager
        self.on_claim_submitted = on_claim_submitted
        self.claim_service = ClaimService(db_path=db_path)

        self.title(f"Claim Item — #{item.id} {item.title}")
        self.geometry("560x480")
        self.minsize(500, 420)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct claim submission form."""
        container = ttk.Frame(self, padding="24")
        container.pack(fill="both", expand=True)

        # Title
        ttk.Label(
            container,
            text=f"✋ Claim Ownership of Item #{self.item.id}",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", pady=(0, 4))

        ttk.Label(
            container,
            text=f"Item: {self.item.title} ({self.item.category})",
            font=("Segoe UI", 10, "bold"),
            foreground="#2563eb"
        ).pack(anchor="w", pady=(0, 16))

        # Instructions banner
        notice = ttk.Label(
            container,
            text="⚠️ To verify ownership, provide specific details not visible in the public title\n"
                 "(e.g., lock screen wallpaper, specific scratches, contents, serial numbers).",
            font=("Segoe UI", 9),
            foreground="#d97706",
            justify="left"
        )
        notice.pack(anchor="w", pady=(0, 16))

        # Proof Description Box
        ttk.Label(container, text="Distinguishing Proof Description *", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.proof_text = tk.Text(
            container,
            height=6,
            wrap="word",
            font=("Segoe UI", 10),
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=8
        )
        self.proof_text.pack(fill="both", expand=True, pady=(6, 16))

        # Buttons
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill="x")

        submit_btn = ttk.Button(
            btn_bar,
            text="Submit Ownership Claim",
            style="Primary.TButton",
            command=self._handle_submit
        )
        submit_btn.pack(side="left", padx=(0, 8))

        cancel_btn = ttk.Button(
            btn_bar,
            text="Cancel",
            style="Secondary.TButton",
            command=self.destroy
        )
        cancel_btn.pack(side="right")

    def _handle_submit(self) -> None:
        """Process claim submission."""
        user = self.session.current_user
        if not user:
            messagebox.showerror("Error", "You must be signed in to submit a claim.", parent=self)
            return

        proof = self.proof_text.get("1.0", tk.END).strip()
        try:
            claim = self.claim_service.submit_claim(
                item_id=self.item.id,
                claimant_id=user.id,
                proof_description=proof
            )
            messagebox.showinfo(
                "Claim Submitted",
                f"Your claim #{claim.id} for '{self.item.title}' has been submitted for review.\n"
                f"The campus administrator or finder will verify your proof details.",
                parent=self
            )
            if self.on_claim_submitted:
                self.on_claim_submitted(claim.id)
            self.destroy()
        except ClaimWorkflowError as err:
            messagebox.showerror("Claim Error", str(err), parent=self)
        except Exception as err:
            messagebox.showerror("Error", f"Failed to submit claim: {err}", parent=self)
