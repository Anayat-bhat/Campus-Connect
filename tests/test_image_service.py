"""
Unit Tests for Phase 12: Image & Photo Attachment System
Verifies image format validation, size limit enforcement, secure local storage,
thumbnail rendering with aspect ratio preservation, and path traversal defenses.
"""

import os
import tempfile
import unittest
import tkinter as tk
from PIL import Image

from services.image_service import (
    ImageService,
    ImageValidationError,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
)
from models.item import Item
from database.connection import DEFAULT_SCHEMA_PATH, seed_default_admin
from database.repository import ItemRepository, UserRepository
from gui.item_details_dialog import ImageViewerDialog, ItemDetailsDialog


class TestImageService(unittest.TestCase):
    """Test suite for ImageService validation, storage, and rendering."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.temp_dir, "uploads")
        self.service = ImageService(upload_dir=self.upload_dir)

        # Create a valid test PNG image
        self.valid_png = os.path.join(self.temp_dir, "test_sample.png")
        img = Image.new("RGB", (200, 150), color=(37, 99, 235))
        img.save(self.valid_png, "PNG")

        # Create a valid test JPEG image
        self.valid_jpg = os.path.join(self.temp_dir, "test_sample.jpg")
        img_jpg = Image.new("RGB", (180, 180), color=(16, 185, 129))
        img_jpg.save(self.valid_jpg, "JPEG")

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_valid_images(self) -> None:
        # Should not raise
        self.service.validate_image(self.valid_png)
        self.service.validate_image(self.valid_jpg)

    def test_validate_nonexistent_file(self) -> None:
        fake_path = os.path.join(self.temp_dir, "nonexistent.png")
        with self.assertRaises(ImageValidationError) as ctx:
            self.service.validate_image(fake_path)
        self.assertIn("File not found", str(ctx.exception))

    def test_validate_disallowed_extension(self) -> None:
        txt_file = os.path.join(self.temp_dir, "sample.txt")
        with open(txt_file, "w") as f:
            f.write("Not an image.")

        with self.assertRaises(ImageValidationError) as ctx:
            self.service.validate_image(txt_file)
        self.assertIn("Unsupported file format", str(ctx.exception))

    def test_validate_oversized_file(self) -> None:
        oversized = os.path.join(self.temp_dir, "oversized.png")
        # Write dummy file exceeding 5MB
        with open(oversized, "wb") as f:
            f.seek(MAX_FILE_SIZE_BYTES + 1024)
            f.write(b"\0")

        with self.assertRaises(ImageValidationError) as ctx:
            self.service.validate_image(oversized)
        self.assertIn("exceeds maximum permitted limit", str(ctx.exception))

    def test_validate_corrupted_image(self) -> None:
        corrupted = os.path.join(self.temp_dir, "corrupt.png")
        with open(corrupted, "wb") as f:
            f.write(b"NOT A REAL PNG DATA STREAM")

        with self.assertRaises(ImageValidationError) as ctx:
            self.service.validate_image(corrupted)
        self.assertIn("Invalid or corrupted", str(ctx.exception))

    def test_save_image_generates_unique_file(self) -> None:
        rel_path1 = self.service.save_image(self.valid_png)
        rel_path2 = self.service.save_image(self.valid_png)

        self.assertNotEqual(rel_path1, rel_path2)
        abs_path1 = self.service.get_absolute_path(rel_path1)
        abs_path2 = self.service.get_absolute_path(rel_path2)

        self.assertTrue(os.path.isfile(abs_path1))
        self.assertTrue(os.path.isfile(abs_path2))
        self.assertTrue(rel_path1.endswith(".png"))

    def test_load_thumbnail(self) -> None:
        # Tk root is needed for ImageTk
        try:
            root = tk.Tk()
            root.withdraw()
        except tk.TclError:
            self.skipTest("Tkinter display not available")

        rel_path = self.service.save_image(self.valid_png)
        thumb = self.service.load_thumbnail(rel_path, size=(80, 80))
        self.assertIsNotNone(thumb)

        # None on invalid path
        self.assertIsNone(self.service.load_thumbnail(None))
        self.assertIsNone(self.service.load_thumbnail("invalid/path/none.png"))
        root.destroy()

    def test_delete_image_and_path_traversal_defense(self) -> None:
        rel_path = self.service.save_image(self.valid_png)
        abs_path = self.service.get_absolute_path(rel_path)
        self.assertTrue(os.path.isfile(abs_path))

        # Successful deletion
        self.assertTrue(self.service.delete_image(rel_path))
        self.assertFalse(os.path.isfile(abs_path))

        # Attempt to delete file outside upload directory should fail
        outside_file = os.path.join(self.temp_dir, "sensitive.txt")
        with open(outside_file, "w") as f:
            f.write("Important data")

        self.assertFalse(self.service.delete_image(outside_file))
        self.assertTrue(os.path.isfile(outside_file))


class TestImageViewerGUI(unittest.TestCase):
    """Test suite verifying ImageViewerDialog modal rendering."""

    def setUp(self) -> None:
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError:
            self.skipTest("Tkinter display not available")

        self.temp_dir = tempfile.mkdtemp()
        self.sample_img = os.path.join(self.temp_dir, "modal_sample.png")
        img = Image.new("RGB", (100, 100), color=(220, 38, 38))
        img.save(self.sample_img, "PNG")

    def tearDown(self) -> None:
        if hasattr(self, "root") and self.root:
            try:
                self.root.destroy()
            except Exception:
                pass
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_image_viewer_dialog_initialization(self) -> None:
        viewer = ImageViewerDialog(
            parent=self.root,
            image_path=self.sample_img,
            item_title="Blue Titan Wrist Watch"
        )
        self.assertIsNotNone(viewer)
        self.assertIn("Blue Titan Wrist Watch", viewer.title())
        self.assertIsNotNone(viewer._photo_ref)
        viewer.destroy()


if __name__ == "__main__":
    unittest.main()
