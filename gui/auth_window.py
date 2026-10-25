"""
CampusConnect: Authentication View & Login/Register Window
Clean tabbed desktop authentication interface supporting sign-in, account creation,
and credential validation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from models.user import User
from services.auth_service import AuthService, RegistrationError
from services.session_manager import SessionManager, AuthenticationError, session_manager as default_session_manager


class AuthWindow(ttk.Frame):
    """Authentication view providing seamless Login and Registration forms."""

    def __init__(
        self,
        parent: tk.Widget,
        db_path: Optional[str] = None,
        session: Optional[SessionManager] = None,
        on_login_success: Optional[Callable[[User], None]] = None
    ) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.session = session if session is not None else default_session_manager
        self.on_login_success = on_login_success
        self.auth_service = AuthService(session=self.session)

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the centered authentication card."""
        self.configure(style="TFrame")

        # Centering wrapper
        center_frame = ttk.Frame(self, style="TFrame")
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Header Logo & Subtitle
        header_box = ttk.Frame(center_frame, style="TFrame")
        header_box.pack(pady=(0, 16))

        brand_lbl = ttk.Label(
            header_box,
            text="🎓 CampusConnect",
            font=("Segoe UI", 22, "bold"),
            foreground="#2563eb"
        )
        brand_lbl.pack(anchor="center")

        sub_lbl = ttk.Label(
            header_box,
            text="Smart Campus Lost & Found Management System",
            font=("Segoe UI", 10),
            foreground="#64748b"
        )
        sub_lbl.pack(anchor="center", pady=(4, 0))

        # Main Card
        self.card = ttk.Frame(center_frame, style="Card.TFrame", padding="28")
        self.card.pack(fill="both", expand=True)

        # Tab Notebook: Sign In vs Register
        self.notebook = ttk.Notebook(self.card)
        self.notebook.pack(fill="both", expand=True)

        self.login_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding="20 16")
        self.register_tab = ttk.Frame(self.notebook, style="Card.TFrame", padding="20 16")

        self.notebook.add(self.login_tab, text="  Sign In  ")
        self.notebook.add(self.register_tab, text="  Create Account  ")

        self._build_login_tab()
        self._build_register_tab()

    def _build_login_tab(self) -> None:
        """Construct sign-in form."""
        ttk.Label(
            self.login_tab,
            text="Sign in to your campus account",
            font=("Segoe UI", 11, "bold"),
            background="#ffffff"
        ).pack(anchor="w", pady=(0, 14))

        # Username / Email
        ttk.Label(self.login_tab, text="Username or Email", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(anchor="w")
        self.login_ident_var = tk.StringVar()
        self.login_ident_entry = ttk.Entry(self.login_tab, textvariable=self.login_ident_var, width=32, font=("Segoe UI", 10))
        self.login_ident_entry.pack(fill="x", pady=(4, 12))

        # Password
        ttk.Label(self.login_tab, text="Password", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(anchor="w")
        self.login_pwd_var = tk.StringVar()
        self.login_pwd_entry = ttk.Entry(
            self.login_tab,
            textvariable=self.login_pwd_var,
            show="•",
            width=32,
            font=("Segoe UI", 10)
        )
        self.login_pwd_entry.pack(fill="x", pady=(4, 8))
        self.login_pwd_entry.bind("<Return>", lambda _: self._handle_login())

        # Show password toggle
        self.show_pwd_var = tk.BooleanVar(value=False)
        show_cb = ttk.Checkbutton(
            self.login_tab,
            text="Show password",
            variable=self.show_pwd_var,
            command=self._toggle_password_visibility
        )
        show_cb.pack(anchor="w", pady=(0, 16))

        # Sign In button
        sign_in_btn = ttk.Button(
            self.login_tab,
            text="Sign In",
            style="Primary.TButton",
            command=self._handle_login
        )
        sign_in_btn.pack(fill="x", pady=(0, 10))

        # Quick default admin hint
        admin_hint = ttk.Label(
            self.login_tab,
            text="Default Admin: admin / Admin@Campus2026",
            font=("Segoe UI", 8),
            foreground="#94a3b8",
            background="#ffffff"
        )
        admin_hint.pack(anchor="center", pady=(6, 0))

    def _build_register_tab(self) -> None:
        """Construct registration form."""
        ttk.Label(
            self.register_tab,
            text="Register a new student account",
            font=("Segoe UI", 11, "bold"),
            background="#ffffff"
        ).pack(anchor="w", pady=(0, 14))

        # Full Name
        ttk.Label(self.register_tab, text="Full Name *", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(anchor="w")
        self.reg_name_var = tk.StringVar()
        ttk.Entry(self.register_tab, textvariable=self.reg_name_var, width=32, font=("Segoe UI", 10)).pack(fill="x", pady=(4, 10))

        # Username
        ttk.Label(self.register_tab, text="Username *", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(anchor="w")
        self.reg_user_var = tk.StringVar()
        ttk.Entry(self.register_tab, textvariable=self.reg_user_var, width=32, font=("Segoe UI", 10)).pack(fill="x", pady=(4, 10))

        # College Email
        ttk.Label(self.register_tab, text="Campus Email *", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(anchor="w")
        self.reg_email_var = tk.StringVar()
        ttk.Entry(self.register_tab, textvariable=self.reg_email_var, width=32, font=("Segoe UI", 10)).pack(fill="x", pady=(4, 10))

        # Password
        ttk.Label(self.register_tab, text="Password (min 6 chars) *", font=("Segoe UI", 9, "bold"), background="#ffffff").pack(anchor="w")
        self.reg_pwd_var = tk.StringVar()
        ttk.Entry(self.register_tab, textvariable=self.reg_pwd_var, show="•", width=32, font=("Segoe UI", 10)).pack(fill="x", pady=(4, 16))

        # Register Button
        register_btn = ttk.Button(
            self.register_tab,
            text="Create Student Account",
            style="Success.TButton",
            command=self._handle_register
        )
        register_btn.pack(fill="x")

    def _toggle_password_visibility(self) -> None:
        show_char = "" if self.show_pwd_var.get() else "•"
        self.login_pwd_entry.configure(show=show_char)

    def _handle_login(self) -> None:
        """Process sign-in attempt."""
        ident = self.login_ident_var.get().strip()
        pwd = self.login_pwd_var.get()

        if not ident or not pwd:
            messagebox.showwarning("Missing Information", "Please enter both username/email and password.", parent=self)
            return

        try:
            user = self.auth_service.login(ident, pwd)
            if self.on_login_success:
                self.on_login_success(user)
        except AuthenticationError as err:
            messagebox.showerror("Authentication Failed", str(err), parent=self)
        except Exception as err:
            messagebox.showerror("Error", f"Login error: {err}", parent=self)

    def _handle_register(self) -> None:
        """Process registration attempt."""
        name = self.reg_name_var.get().strip()
        username = self.reg_user_var.get().strip()
        email = self.reg_email_var.get().strip()
        pwd = self.reg_pwd_var.get()

        try:
            user = self.auth_service.register_user(
                username=username,
                password=pwd,
                full_name=name,
                email=email,
                role="student"
            )
            messagebox.showinfo(
                "Account Created",
                f"Welcome {user.full_name}! Your account has been registered successfully.\nYou may now sign in.",
                parent=self
            )
            # Switch back to login tab with prefilled username
            self.login_ident_var.set(username)
            self.login_pwd_var.set("")
            self.notebook.select(self.login_tab)
        except (RegistrationError, ValueError) as err:
            messagebox.showerror("Registration Failed", str(err), parent=self)
        except Exception as err:
            messagebox.showerror("Error", f"Failed to register account: {err}", parent=self)
