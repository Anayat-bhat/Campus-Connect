"""
CampusConnect: Lost & Found Reporting Frame
Interactive form for students and administrators to report lost or found campus items.
"""

from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Callable
from models.item import Item, VALID_CATEGORIES
from database.repository import ItemRepository
from services.session_manager import SessionManager, session_manager as default_session_manager
from services.image_service import ImageService, ImageValidationError


class ReportItemFrame(ttk.Frame):
    """View component for reporting lost and found items."""

    def __init__(
        self,
        parent: tk.Widget,
        db_path: Optional[str] = None,
        session: Optional[SessionManager] = None,
        on_success_callback: Optional[Callable[[int], None]] = None
    ) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self.session = session if session is not None else default_session_manager
        self.on_success_callback = on_success_callback
        self.item_repo = ItemRepository(db_path)
        self.image_service = ImageService()
        self.selected_raw_image_path: Optional[str] = None
        self._thumbnail_ref: Optional[tk.PhotoImage] = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Render the reporting form elements with full scrollability."""
        # Scrollable canvas container
        self.canvas = tk.Canvas(self, bg="#f8fafc", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)

        # Inner form card container
        card = ttk.Frame(self.canvas, style="Card.TFrame", padding="20 16")

        card.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=card, anchor="nw")

        def _on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)

        self.canvas.bind("<Configure>", _on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        def _on_mousewheel(event):
            if self.canvas.winfo_exists():
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.bind("<MouseWheel>", _on_mousewheel)
        self.canvas.bind("<MouseWheel>", _on_mousewheel)
        card.bind("<MouseWheel>", _on_mousewheel)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Title
        title_lbl = ttk.Label(
            card,
            text="📝 Report a Campus Item",
            font=("Segoe UI", 15, "bold"),
            background="#ffffff"
        )
        title_lbl.pack(anchor="w", pady=(0, 2))

        subtitle_lbl = ttk.Label(
            card,
            text="Provide accurate details so our matching system and campus community can assist.",
            font=("Segoe UI", 9),
            foreground="#64748b",
            background="#ffffff"
        )
        subtitle_lbl.pack(anchor="w", pady=(0, 12))

        # Grid form
        form_grid = ttk.Frame(card, style="Card.TFrame")
        form_grid.pack(fill="x", expand=False)
        form_grid.columnconfigure(1, weight=1)

        row = 0

        # Item Type (Radio buttons)
        ttk.Label(form_grid, text="Report Type *", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 16)
        )
        self.type_var = tk.StringVar(value="LOST")
        type_box = ttk.Frame(form_grid, style="Card.TFrame")
        type_box.grid(row=row, column=1, sticky="w", pady=8)

        rb_lost = ttk.Radiobutton(type_box, text="Lost (I lost something)", value="LOST", variable=self.type_var)
        rb_lost.pack(side="left", padx=(0, 16))
        rb_found = ttk.Radiobutton(type_box, text="Found (I found something)", value="FOUND", variable=self.type_var)
        rb_found.pack(side="left")
        row += 1

        # Title
        ttk.Label(form_grid, text="Item Title *", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(
            row=row, column=0, sticky="w", pady=8, padx=(0, 16)
        )
        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(form_grid, textvariable=self.title_var, font=("Segoe UI", 10))
        self.title_entry.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # Category
        ttk.Label(form_grid, text="Category *", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 16)
        )
        self.category_var = tk.StringVar()
        self.category_cb = ttk.Combobox(
            form_grid,
            textvariable=self.category_var,
            values=sorted(list(VALID_CATEGORIES)),
            state="readonly",
            font=("Segoe UI", 10)
        )
        self.category_cb.set(sorted(list(VALID_CATEGORIES))[0])
        self.category_cb.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # Location
        ttk.Label(form_grid, text="Location *", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 16)
        )
        self.location_var = tk.StringVar()
        self.location_entry = ttk.Entry(form_grid, textvariable=self.location_var, font=("Segoe UI", 10))
        self.location_entry.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # Event Date
        ttk.Label(form_grid, text="Date (YYYY-MM-DD) *", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(
            row=row, column=0, sticky="w", pady=5, padx=(0, 16)
        )
        self.date_var = tk.StringVar(value=date.today().isoformat())
        self.date_entry = ttk.Entry(form_grid, textvariable=self.date_var, font=("Segoe UI", 10))
        self.date_entry.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # Description (Text Area)
        ttk.Label(form_grid, text="Detailed Description *", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(
            row=row, column=0, sticky="nw", pady=5, padx=(0, 16)
        )
        self.desc_text = tk.Text(
            form_grid,
            height=3,
            wrap="word",
            font=("Segoe UI", 10),
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6
        )
        self.desc_text.grid(row=row, column=1, sticky="ew", pady=5)
        row += 1

        # Optional Image Upload & Preview Card
        ttk.Label(form_grid, text="Item Photo (Optional)", font=("Segoe UI", 10, "bold"), background="#ffffff").grid(
            row=row, column=0, sticky="nw", pady=5, padx=(0, 16)
        )
        img_container = ttk.Frame(form_grid, style="Card.TFrame")
        img_container.grid(row=row, column=1, sticky="ew", pady=5)

        img_actions = ttk.Frame(img_container, style="Card.TFrame")
        img_actions.pack(fill="x", anchor="w")

        self.image_var = tk.StringVar()
        self.image_entry = ttk.Entry(img_actions, textvariable=self.image_var, font=("Segoe UI", 9), state="readonly")
        self.image_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        browse_btn = ttk.Button(img_actions, text="📷 Browse Photo...", command=self._on_browse_image)
        browse_btn.pack(side="left", padx=(0, 6))

        clear_img_btn = ttk.Button(img_actions, text="✕ Clear", command=self._on_clear_image)
        clear_img_btn.pack(side="left")

        # Live Thumbnail Preview
        self.thumbnail_preview_lbl = ttk.Label(
            img_container,
            text="No photo selected (Optional: PNG, JPG, WEBP max 5MB)",
            font=("Segoe UI", 9),
            foreground="#64748b",
            background="#ffffff"
        )
        self.thumbnail_preview_lbl.pack(anchor="w", pady=(6, 0))
        row += 1

        # Action Buttons
        btn_box = ttk.Frame(card, style="Card.TFrame")
        btn_box.pack(anchor="w", pady=(14, 16))

        submit_btn = ttk.Button(
            btn_box,
            text="✓ Submit Item Report",
            style="Primary.TButton",
            command=self._on_submit
        )
        submit_btn.pack(side="left", padx=(0, 12))

        reset_btn = ttk.Button(
            btn_box,
            text="Clear Form",
            style="Secondary.TButton",
            command=self.reset_form
        )
        reset_btn.pack(side="left")

        # Keyboard Shortcut: Ctrl+Enter triggers submit
        self.bind_all("<Control-Return>", lambda _: self._on_submit())

    def _on_browse_image(self) -> None:
        """Open file dialog to pick an image and render live preview."""
        chosen = filedialog.askopenfilename(
            parent=self,
            title="Select Item Photo",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                ("PNG Image", "*.png"),
                ("JPEG Image", "*.jpg *.jpeg"),
                ("All files", "*.*")
            ]
        )
        if not chosen:
            return

        try:
            self.image_service.validate_image(chosen)
            self.selected_raw_image_path = chosen
            self.image_var.set(chosen)

            # Load thumbnail preview
            thumb = self.image_service.load_thumbnail(chosen, size=(120, 120))
            if thumb:
                self._thumbnail_ref = thumb
                self.thumbnail_preview_lbl.configure(
                    image=self._thumbnail_ref,
                    text="",
                    compound="none"
                )
            else:
                self.thumbnail_preview_lbl.configure(
                    image="",
                    text=f"✓ Selected: {chosen}"
                )
        except ImageValidationError as err:
            messagebox.showerror("Invalid Image File", str(err), parent=self)
            self._on_clear_image()

    def _on_clear_image(self) -> None:
        """Clear chosen image attachment."""
        self.selected_raw_image_path = None
        self._thumbnail_ref = None
        self.image_var.set("")
        self.thumbnail_preview_lbl.configure(
            image="",
            text="No photo selected (Optional: PNG, JPG, WEBP max 5MB)"
        )

    def reset_form(self) -> None:
        """Clear form inputs back to defaults."""
        self.type_var.set("LOST")
        self.title_var.set("")
        self.category_cb.set(sorted(list(VALID_CATEGORIES))[0])
        self.location_var.set("")
        self.date_var.set(date.today().isoformat())
        self.desc_text.delete("1.0", tk.END)
        self._on_clear_image()

    def _on_submit(self) -> None:
        """Validate input, securely persist image, and save item report."""
        user = self.session.current_user
        if not user:
            messagebox.showerror("Error", "You must be logged in to report an item.", parent=self)
            return

        desc = self.desc_text.get("1.0", tk.END).strip()
        title = self.title_var.get().strip()
        location = self.location_var.get().strip()
        event_date = self.date_var.get().strip()
        category = self.category_var.get()
        item_type = self.type_var.get()

        # Securely copy image into upload directory if selected
        final_image_path: Optional[str] = None
        if self.selected_raw_image_path:
            try:
                final_image_path = self.image_service.save_image(self.selected_raw_image_path)
            except Exception as e:
                messagebox.showerror("Image Upload Error", f"Failed to save image attachment: {e}", parent=self)
                return

        item = Item(
            id=None,
            type=item_type,
            user_id=user.id,
            title=title,
            category=category,
            description=desc,
            event_date=event_date,
            location=location,
            image_path=final_image_path,
            status="OPEN"
        )

        try:
            item_id = self.item_repo.create(item)
            messagebox.showinfo(
                "Report Submitted",
                f"Successfully registered {item_type} item #{item_id}: '{title}'.",
                parent=self
            )
            self.reset_form()
            if self.on_success_callback:
                self.on_success_callback(item_id)
        except ValueError as err:
            # Clean up copied file if validation failed
            if final_image_path:
                self.image_service.delete_image(final_image_path)
            messagebox.showerror("Validation Error", str(err), parent=self)
        except Exception as ex:
            if final_image_path:
                self.image_service.delete_image(final_image_path)
            messagebox.showerror("Error", f"Failed to submit item report: {ex}", parent=self)
