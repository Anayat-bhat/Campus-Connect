"""
Phase 1 Unit Tests: Environment & Structure Verification
"""

import os
import sys
import unittest


class TestPhase1Setup(unittest.TestCase):
    """Test suite for Phase 1 project scaffolding."""

    def setUp(self) -> None:
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_python_version(self) -> None:
        """Verify Python runtime version is at least 3.10."""
        self.assertGreaterEqual(
            sys.version_info[:2],
            (3, 10),
            f"Python 3.10 or higher is required. Found: {sys.version}"
        )

    def test_tkinter_availability(self) -> None:
        """Verify Tkinter standard library module can be imported."""
        try:
            import tkinter as tk
            from tkinter import ttk
            self.assertTrue(hasattr(tk, "Tk"))
            self.assertTrue(hasattr(ttk, "Style"))
        except ImportError as e:
            self.fail(f"Tkinter failed to import: {e}")

    def test_directory_structure_exists(self) -> None:
        """Verify all planned architectural directories exist."""
        expected_dirs = [
            "database",
            "models",
            "services",
            "gui",
            "analytics",
            "tests",
            "data",
            "assets",
        ]
        for dir_name in expected_dirs:
            dir_path = os.path.join(self.base_dir, dir_name)
            self.assertTrue(
                os.path.isdir(dir_path),
                f"Expected architectural directory '{dir_name}' is missing at {dir_path}"
            )

    def test_critical_files_exist(self) -> None:
        """Verify core root files exist."""
        expected_files = [
            ".gitignore",
            "requirements.txt",
            "README.md",
            "main.py",
        ]
        for file_name in expected_files:
            file_path = os.path.join(self.base_dir, file_name)
            self.assertTrue(
                os.path.isfile(file_path),
                f"Expected configuration file '{file_name}' is missing at {file_path}"
            )


if __name__ == "__main__":
    unittest.main()
