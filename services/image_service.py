"""
CampusConnect: Image & Photo Attachment Service
Handles secure validation, local storage, resizing, and Tkinter thumbnail rendering
for lost and found item photos.
"""

import os
import shutil
import uuid
from typing import Optional, Tuple, Any
from pathlib import Path

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


DEFAULT_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "uploads")
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 Megabytes


class ImageValidationError(Exception):
    """Raised when an uploaded file fails format, size, or integrity checks."""
    pass


class ImageService:
    """Manages file storage, integrity validation, and Tkinter thumbnail conversions."""

    def __init__(self, upload_dir: Optional[str] = None) -> None:
        self.upload_dir = upload_dir if upload_dir is not None else DEFAULT_UPLOAD_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    def validate_image(self, file_path: str) -> None:
        """
        Validate that the file exists, has a permitted extension, is within size limits,
        and constitutes a legitimate image format.
        """
        if not file_path or not os.path.isfile(file_path):
            raise ImageValidationError(f"File not found: '{file_path}'")

        ext = Path(file_path).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ImageValidationError(
                f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        file_size = os.path.getsize(file_path)
        if file_size > MAX_FILE_SIZE_BYTES:
            max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
            raise ImageValidationError(
                f"File size ({file_size / (1024*1024):.2f}MB) exceeds maximum permitted limit of {max_mb}MB."
            )

        if PIL_AVAILABLE:
            try:
                with Image.open(file_path) as img:
                    img.verify()
            except Exception as e:
                raise ImageValidationError(f"Invalid or corrupted image file: {str(e)}")

    def save_image(self, source_path: str) -> str:
        """
        Validate source image and securely persist a copy into the upload directory
        with an unguessable unique filename. Returns the relative storage path.
        """
        self.validate_image(source_path)

        ext = Path(source_path).suffix.lower()
        unique_name = f"item_{uuid.uuid4().hex[:12]}{ext}"
        destination_path = os.path.join(self.upload_dir, unique_name)

        shutil.copy2(source_path, destination_path)

        # Return path normalized with forward slashes for cross-platform portability
        rel_path = os.path.relpath(destination_path, os.path.dirname(os.path.dirname(__file__)))
        return rel_path.replace("\\", "/")

    def get_absolute_path(self, stored_path: Optional[str]) -> Optional[str]:
        """Convert a stored relative or absolute path into an absolute filesystem path."""
        if not stored_path:
            return None
        if os.path.isabs(stored_path):
            return stored_path
        base_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.normpath(os.path.join(base_dir, stored_path))

    def load_thumbnail(
        self,
        image_path: Optional[str],
        size: Tuple[int, int] = (140, 140)
    ) -> Optional[Any]:
        """
        Generate a resized PIL ImageTk.PhotoImage suitable for display in Tkinter widgets.
        Returns None if Pillow is unavailable or the image file cannot be loaded.
        """
        if not PIL_AVAILABLE or not image_path:
            return None

        abs_path = self.get_absolute_path(image_path)
        if not abs_path or not os.path.isfile(abs_path):
            return None

        try:
            with Image.open(abs_path) as img:
                img_copy = img.copy()
                img_copy.thumbnail(size, getattr(Image, "Resampling", Image).LANCZOS)
                return ImageTk.PhotoImage(img_copy)
        except Exception:
            return None

    def delete_image(self, image_path: Optional[str]) -> bool:
        """Safely delete an uploaded file from the storage directory."""
        if not image_path:
            return False
        abs_path = self.get_absolute_path(image_path)
        if abs_path and os.path.isfile(abs_path) and os.path.commonpath([abs_path, self.upload_dir]) == self.upload_dir:
            try:
                os.remove(abs_path)
                return True
            except OSError:
                return False
        return False
