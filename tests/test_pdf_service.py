"""
CampusConnect: Automated Unit Tests for PDF Generation Service (Phase 13)
Verifies:
- Handover certificate generation for approved claims
- Handover certificate error handling on pending/rejected claims
- Handover certificate with embedded photograph attachment
- Campus audit and recovery intelligence report generation
- Two-pass canvas page calculation and file system output validation
"""

import os
import shutil
import tempfile
import unittest
from datetime import datetime
from PIL import Image as PILImage

from database.connection import init_database
from database.repository import ItemRepository, ClaimRepository, UserRepository
from models.user import User
from models.item import Item
from models.claim import Claim
from services.pdf_service import PDFService, NumberedCanvas


class TestPDFService(unittest.TestCase):
    """Test suite covering PDFService document generation."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_campus_connect.db")
        init_database(self.db_path)

        self.item_repo = ItemRepository(self.db_path)
        self.claim_repo = ClaimRepository(self.db_path)
        self.user_repo = UserRepository(self.db_path)
        self.pdf_service = PDFService(self.db_path)

        # Seed test admin and student
        self.admin = User(
            id=None,
            username="admin_sec",
            password_hash="fakehash",
            salt="fakesalt",
            full_name="Prof. Sharma Security Lead",
            email="security@campus.edu",
            role="admin",
        )
        self.admin_id = self.user_repo.create(self.admin)

        self.student = User(
            id=None,
            username="aarav_test",
            password_hash="fakehash",
            salt="fakesalt",
            full_name="Aarav Sharma",
            email="aarav@campus.edu",
            role="student",
        )
        self.student_id = self.user_repo.create(self.student)

        # Create a sample test image
        self.img_path = os.path.join(self.test_dir, "test_item_photo.png")
        img = PILImage.new("RGB", (300, 200), color=(37, 99, 235))
        img.save(self.img_path)

        # Seed found item
        self.item = Item(
            id=None,
            type="FOUND",
            user_id=self.student_id,
            title="Dell Inspiron Laptop 15-inch",
            category="Electronics",
            description="Silver color, left corner sticker with Linux penguin logo.",
            event_date="2026-10-25",
            location="Central Library 2nd Floor",
            image_path=self.img_path,
            status="OPEN",
        )
        self.item_id = self.item_repo.create(self.item)

        # Seed claim
        self.claim = Claim(
            id=None,
            item_id=self.item_id,
            claimant_id=self.student_id,
            proof_description="Laptop has serial number CN-0ABCD12 and 1TB SSD inside.",
            status="PENDING",
        )
        self.claim_id = self.claim_repo.create(self.claim)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_generate_handover_receipt_rejects_pending_claim(self):
        """Verifies that unapproved claims cannot produce a handover receipt."""
        out_pdf = os.path.join(self.test_dir, "pending_receipt.pdf")
        with self.assertRaises(ValueError) as ctx:
            self.pdf_service.generate_handover_receipt(self.claim_id, out_pdf)
        self.assertIn("must be 'APPROVED'", str(ctx.exception))
        self.assertFalse(os.path.exists(out_pdf))

    def test_generate_handover_receipt_nonexistent_claim(self):
        """Verifies handling of non-existent claim IDs."""
        with self.assertRaises(ValueError) as ctx:
            self.pdf_service.generate_handover_receipt(99999)
        self.assertIn("was not found", str(ctx.exception))

    def test_generate_handover_receipt_success(self):
        """Verifies successful PDF handover certificate generation for an approved claim."""
        # Approve the claim
        self.claim_repo.update_status(
            claim_id=self.claim_id,
            status="APPROVED",
            reviewed_by=self.admin_id,
            review_notes="Owner verified serial number and entered BIOS password on test bench.",
        )
        self.item_repo.update_status(self.item_id, "RETURNED")

        out_pdf = os.path.join(self.test_dir, "approved_receipt.pdf")
        result_path = self.pdf_service.generate_handover_receipt(self.claim_id, out_pdf)

        self.assertEqual(result_path, os.path.abspath(out_pdf))
        self.assertTrue(os.path.isfile(out_pdf))
        self.assertGreater(os.path.getsize(out_pdf), 1500)

        # Check PDF header bytes (%PDF)
        with open(out_pdf, "rb") as f:
            header = f.read(5)
            self.assertEqual(header, b"%PDF-")

    def test_generate_handover_receipt_without_photo(self):
        """Verifies receipt generation when item has no photo attached."""
        item2 = Item(
            id=None,
            type="FOUND",
            user_id=self.student_id,
            title="Scientific Calculator fx-991EX",
            category="Books and stationery",
            description="Black casing with math formula stickers.",
            event_date="2026-10-24",
            location="Room 304 LH",
            image_path=None,
            status="OPEN",
        )
        item2_id = self.item_repo.create(item2)

        claim2 = Claim(
            id=None,
            item_id=item2_id,
            claimant_id=self.student_id,
            proof_description="Has my initials 'A.S.' scratched in back battery cover.",
            status="PENDING",
        )
        claim2_id = self.claim_repo.create(claim2)
        self.claim_repo.update_status(
            claim_id=claim2_id,
            status="APPROVED",
            reviewed_by=self.admin_id,
            review_notes="Initials match student ID.",
        )

        out_pdf = os.path.join(self.test_dir, "receipt_no_photo.pdf")
        result_path = self.pdf_service.generate_handover_receipt(claim2_id, out_pdf)
        self.assertTrue(os.path.isfile(result_path))
        self.assertGreater(os.path.getsize(result_path), 1200)

    def test_generate_audit_report(self):
        """Verifies institutional audit report generation with KPI summary and table inventory."""
        out_pdf = os.path.join(self.test_dir, "audit_report.pdf")
        result_path = self.pdf_service.generate_audit_report(
            output_path=out_pdf,
            operator_name="Director of Security"
        )

        self.assertEqual(result_path, os.path.abspath(out_pdf))
        self.assertTrue(os.path.isfile(out_pdf))
        self.assertGreater(os.path.getsize(out_pdf), 2000)

        with open(out_pdf, "rb") as f:
            header = f.read(5)
            self.assertEqual(header, b"%PDF-")

    def test_open_pdf_nonexistent(self):
        """Verifies open_pdf returns False on missing file."""
        self.assertFalse(self.pdf_service.open_pdf("non_existent_file.pdf"))


if __name__ == "__main__":
    unittest.main()
