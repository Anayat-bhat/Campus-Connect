"""
CampusConnect: Official PDF Handover Receipt & Campus Audit Report Service
Generates professional, printable, secure PDF documents using ReportLab:
1. Official Item Handover Certificate (Receipt of Return)
2. Campus Lost & Found Comprehensive Audit & Recovery Report
"""

import os
import hashlib
import platform
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from PIL import Image as PILImage

from database.repository import ClaimRepository, ItemRepository, UserRepository
from database.connection import get_connection
from analytics.metrics import AnalyticsMetrics
from models.claim import Claim
from models.item import Item
from models.user import User


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and stamp total page count (Page X of Y).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.75)
        self.line(36, 36, 576, 36)

        # Left footer: System identifier
        self.drawString(36, 24, "CampusConnect Lost & Found Intelligence System — Official Document")

        # Right footer: Page count
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 24, page_text)
        self.restoreState()


class PDFService:
    """
    Service responsible for compiling and generating formal PDF handover
    certificates, verification receipts, and institutional audit reports.
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self.claim_repo = ClaimRepository(db_path)
        self.item_repo = ItemRepository(db_path)
        self.user_repo = UserRepository(db_path)
        self.metrics = AnalyticsMetrics(db_path)

        # Base export directory
        self.default_export_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "exports")
        )
        os.makedirs(self.default_export_dir, exist_ok=True)

    def _get_styles(self) -> Dict[str, ParagraphStyle]:
        """Produce consistent typography and palette styles."""
        styles = getSampleStyleSheet()

        custom_styles = {
            "BannerTitle": ParagraphStyle(
                "BannerTitle",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=17,
                leading=21,
                textColor=colors.HexColor("#ffffff"),
                alignment=1,  # Center
            ),
            "BannerSubtitle": ParagraphStyle(
                "BannerSubtitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9,
                leading=13,
                textColor=colors.HexColor("#94a3b8"),
                alignment=1,
            ),
            "DocMeta": ParagraphStyle(
                "DocMeta",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#1e293b"),
            ),
            "SectionHeader": ParagraphStyle(
                "SectionHeader",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=15,
                textColor=colors.HexColor("#0f172a"),
            ),
            "CellBold": ParagraphStyle(
                "CellBold",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=8.5,
                leading=11,
                textColor=colors.HexColor("#334155"),
            ),
            "CellNormal": ParagraphStyle(
                "CellNormal",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8.5,
                leading=11,
                textColor=colors.HexColor("#1e293b"),
            ),
            "CellNormalMuted": ParagraphStyle(
                "CellNormalMuted",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#64748b"),
            ),
            "LegalDisclaimer": ParagraphStyle(
                "LegalDisclaimer",
                parent=styles["Normal"],
                fontName="Helvetica-Oblique",
                fontSize=7.5,
                leading=10.5,
                textColor=colors.HexColor("#475569"),
            ),
            "BadgeSuccess": ParagraphStyle(
                "BadgeSuccess",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=9,
                leading=11,
                textColor=colors.HexColor("#166534"),
                alignment=1,
            ),
            "KPITitle": ParagraphStyle(
                "KPITitle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#64748b"),
                alignment=1,
            ),
            "KPIValue": ParagraphStyle(
                "KPIValue",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=18,
                leading=22,
                textColor=colors.HexColor("#0f172a"),
                alignment=1,
            ),
        }
        return custom_styles

    def _prepare_image_flowable(self, image_path: Optional[str], max_width: float = 2.0, max_height: float = 2.0):
        """Prepare an aspect-scaled ReportLab Image flowable or fallback string."""
        if not image_path or not os.path.isfile(image_path):
            return None

        try:
            with PILImage.open(image_path) as img:
                orig_w, orig_h = img.size
                if orig_w <= 0 or orig_h <= 0:
                    return None

                ratio = min((max_width * inch) / orig_w, (max_height * inch) / orig_h)
                dest_w = orig_w * ratio
                dest_h = orig_h * ratio
                return RLImage(image_path, width=dest_w, height=dest_h)
        except Exception:
            return None

    def generate_handover_receipt(
        self,
        claim_id: int,
        output_path: Optional[str] = None
    ) -> str:
        """
        Compile and generate an Official Item Handover Certificate (Receipt of Return)
        for a verified and approved claim.

        Raises:
            ValueError: If the claim does not exist or has not been approved.
        """
        claim = self.claim_repo.get_by_id(claim_id)
        if not claim:
            raise ValueError(f"Claim #{claim_id} was not found.")

        if claim.status != "APPROVED":
            raise ValueError(
                f"Cannot generate Handover Receipt for Claim #{claim_id}: "
                f"Status is '{claim.status}', but must be 'APPROVED'."
            )

        item = self.item_repo.get_by_id(claim.item_id)
        if not item:
            raise ValueError(f"Referenced Item #{claim.item_id} does not exist.")

        claimant = self.user_repo.get_by_id(claim.claimant_id)
        reviewer = self.user_repo.get_by_id(claim.reviewed_by) if claim.reviewed_by else None

        # Determine target file destination
        if not output_path:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"handover_receipt_claim_{claim.id}_{timestamp_str}.pdf"
            output_path = os.path.join(self.default_export_dir, filename)

        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate unique verification hash & certificate number
        hash_input = f"{claim.id}:{item.id}:{claim.claimant_id}:{claim.reviewed_at}:{claim.status}"
        security_token = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:16].upper()
        cert_num = f"CC-REC-{claim.id:04d}-{datetime.now().strftime('%Y%m')}"

        styles = self._get_styles()
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=48,
        )

        story = []

        # 1. Header Banner
        banner_data = [
            [
                Paragraph("CAMPUSCONNECT VERIFIED RECOVERY SERVICE", styles["BannerSubtitle"]),
            ],
            [
                Paragraph("OFFICIAL ITEM HANDOVER CERTIFICATE", styles["BannerTitle"]),
            ],
            [
                Paragraph(
                    "Department of Campus Safety, Security & Student Affairs • Lost & Found Dispatch",
                    styles["BannerSubtitle"],
                ),
            ],
        ]
        banner_table = Table(banner_data, colWidths=[540])
        banner_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("PADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])
        )
        story.append(banner_table)
        story.append(Spacer(1, 12))

        # 2. Document Metadata Card
        meta_left = [
            Paragraph(f"<b>Certificate No:</b> {cert_num}", styles["CellNormal"]),
            Paragraph(f"<b>Handover Date:</b> {claim.reviewed_at or datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["CellNormal"]),
            Paragraph(f"<b>Security Hash:</b> <font color='#64748b'>{security_token}</font>", styles["CellNormal"]),
        ]
        meta_right = [
            Paragraph("<b>Custody Status:</b>", styles["CellNormal"]),
            Paragraph("<b>✓ OFFICIALLY RETURNED</b>", styles["BadgeSuccess"]),
            Paragraph(f"<b>Verified By Admin:</b> {reviewer.full_name if reviewer else 'Campus Security'}", styles["CellNormal"]),
        ]

        meta_table = Table(
            [[meta_left, meta_right]],
            colWidths=[310, 230],
        )
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 14))

        # 3. Item Information Section
        story.append(Paragraph("1. RECOVERED PROPERTY SPECIFICATIONS", styles["SectionHeader"]))
        story.append(Spacer(1, 4))

        img_flowable = self._prepare_image_flowable(item.image_path, max_width=1.9, max_height=1.9)

        item_rows = [
            [
                Paragraph("<b>Item Tracking ID:</b>", styles["CellBold"]),
                Paragraph(f"#{item.id} ({item.type})", styles["CellNormal"]),
                Paragraph("<b>Category:</b>", styles["CellBold"]),
                Paragraph(item.category, styles["CellNormal"]),
            ],
            [
                Paragraph("<b>Item Title:</b>", styles["CellBold"]),
                Paragraph(f"<b>{item.title}</b>", styles["CellNormal"]),
                Paragraph("<b>Found Location:</b>", styles["CellBold"]),
                Paragraph(item.location, styles["CellNormal"]),
            ],
            [
                Paragraph("<b>Date Discovered:</b>", styles["CellBold"]),
                Paragraph(item.event_date, styles["CellNormal"]),
                Paragraph("<b>Current Status:</b>", styles["CellBold"]),
                Paragraph(f"<font color='#16a34a'><b>{item.status}</b></font>", styles["CellNormal"]),
            ],
            [
                Paragraph("<b>Description:</b>", styles["CellBold"]),
                Paragraph(item.description or "None recorded", styles["CellNormal"]),
                Paragraph("", styles["CellNormal"]),
                Paragraph("", styles["CellNormal"]),
            ],
        ]

        if img_flowable:
            # Layout with thumbnail on the right
            details_subtable = Table(
                item_rows,
                colWidths=[100, 110, 85, 95],
            )
            details_subtable.setStyle(
                TableStyle([
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("SPAN", (1, 3), (3, 3)),  # Description spans remaining cols
                ])
            )

            photo_cell = [
                Paragraph("<b>Attached Photo</b>", styles["CellBold"]),
                Spacer(1, 3),
                img_flowable,
            ]

            spec_table = Table(
                [[details_subtable, photo_cell]],
                colWidths=[390, 150],
            )
            spec_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                    ("LINEBEFORE", (1, 0), (1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("PADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ])
            )
        else:
            spec_table = Table(
                item_rows,
                colWidths=[110, 160, 110, 160],
            )
            spec_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("SPAN", (1, 3), (3, 3)),
                ])
            )

        story.append(spec_table)
        story.append(Spacer(1, 14))

        # 4. Claimant & Verification Audit Record
        story.append(Paragraph("2. CLAIMANT & VERIFICATION AUDIT TRAIL", styles["SectionHeader"]))
        story.append(Spacer(1, 4))

        claim_data = [
            [
                Paragraph("<b>Claimant Name:</b>", styles["CellBold"]),
                Paragraph(claimant.full_name if claimant else "Unknown", styles["CellNormal"]),
                Paragraph("<b>Username / Role:</b>", styles["CellBold"]),
                Paragraph(f"{claimant.username} ({claimant.role})" if claimant else "N/A", styles["CellNormal"]),
            ],
            [
                Paragraph("<b>Official Email:</b>", styles["CellBold"]),
                Paragraph(claimant.email if claimant else "N/A", styles["CellNormal"]),
                Paragraph("<b>Claim Filed Date:</b>", styles["CellBold"]),
                Paragraph(claim.submitted_at or "N/A", styles["CellNormal"]),
            ],
            [
                Paragraph("<b>Ownership Proof:</b>", styles["CellBold"]),
                Paragraph(claim.proof_description, styles["CellNormal"]),
                Paragraph("", styles["CellNormal"]),
                Paragraph("", styles["CellNormal"]),
            ],
            [
                Paragraph("<b>Verification Notes:</b>", styles["CellBold"]),
                Paragraph(claim.review_notes or "Verified against distinguishing characteristics.", styles["CellNormal"]),
                Paragraph("", styles["CellNormal"]),
                Paragraph("", styles["CellNormal"]),
            ],
        ]

        claim_table = Table(
            claim_data,
            colWidths=[115, 155, 115, 155],
        )
        claim_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("SPAN", (1, 2), (3, 2)),
                ("SPAN", (1, 3), (3, 3)),
            ])
        )
        story.append(claim_table)
        story.append(Spacer(1, 14))

        # 5. Legal Undertaking & Custody Release
        story.append(Paragraph("3. LEGAL DECLARATION & RELEASE OF CUSTODY", styles["SectionHeader"]))
        story.append(Spacer(1, 4))

        disclaimer_text = (
            "I hereby certify and declare under institutional honor that I am the rightful, lawful owner of the "
            "property described in Section 1 of this certificate. I confirm receipt of said property in complete, "
            "satisfactory condition and acknowledge that the Campus Lost & Found Administration and University "
            "personnel are released from any and all further liabilities, damages, or claims regarding this item. "
            "Any fraudulent representation of property ownership is subject to immediate student disciplinary code review."
        )
        disclaimer_box = Table(
            [[Paragraph(disclaimer_text, styles["LegalDisclaimer"])]],
            colWidths=[540],
        )
        disclaimer_box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 7),
            ])
        )
        story.append(disclaimer_box)
        story.append(Spacer(1, 18))

        # 6. Formal Signatures & Institution Seal Block
        sig_data = [
            [
                Paragraph("<b>RECIPIENT / CLAIMANT</b>", styles["CellBold"]),
                Paragraph("<b>CAMPUS DISPATCH OFFICER</b>", styles["CellBold"]),
                Paragraph("<b>OFFICIAL SEAL</b>", styles["CellBold"]),
            ],
            [
                Paragraph("<br/><br/>_____________________________________<br/>Signature: " + (claimant.full_name if claimant else "Claimant"), styles["CellNormal"]),
                Paragraph("<br/><br/>_____________________________________<br/>Signature: " + (reviewer.full_name if reviewer else "Security Officer"), styles["CellNormal"]),
                Paragraph("<br/><br/>[ CAMPUS SEAL / STAMP ]<br/>Date: " + datetime.now().strftime("%Y-%m-%d"), styles["CellNormalMuted"]),
            ],
        ]
        sig_table = Table(sig_data, colWidths=[200, 200, 140])
        sig_table.setStyle(
            TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ])
        )
        story.append(KeepTogether([sig_table]))

        # Build document with 2-pass page numbering
        doc.build(story, canvasmaker=NumberedCanvas)
        return output_path

    def generate_audit_report(
        self,
        output_path: Optional[str] = None,
        operator_name: Optional[str] = None
    ) -> str:
        """
        Compile and generate a comprehensive Campus Lost & Found Audit and
        Asset Recovery Intelligence Report in PDF format.
        """
        if not output_path:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"campus_audit_report_{timestamp_str}.pdf"
            output_path = os.path.join(self.default_export_dir, filename)

        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        kpis = self.metrics.get_summary_kpis()
        cat_dist = self.metrics.get_category_distribution()
        hotspots = self.metrics.get_location_hotspots(top_n=5)
        df_items = self.metrics.get_items_dataframe()

        styles = self._get_styles()
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=48,
        )

        story = []

        # 1. Header Banner
        banner_data = [
            [
                Paragraph("CAMPUSCONNECT INTELLIGENCE & AUDITING ENGINE", styles["BannerSubtitle"]),
            ],
            [
                Paragraph("CAMPUS LOST & FOUND AUDIT & RECOVERY REPORT", styles["BannerTitle"]),
            ],
            [
                Paragraph(
                    f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M:%S')} • Auditor: {operator_name or 'System Administrator'}",
                    styles["BannerSubtitle"],
                ),
            ],
        ]
        banner_table = Table(banner_data, colWidths=[540])
        banner_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("PADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])
        )
        story.append(banner_table)
        story.append(Spacer(1, 12))

        # 2. Executive KPI Cards Row
        kpi_cells = [
            [
                Paragraph("TOTAL LOGGED", styles["KPITitle"]),
                Paragraph("LOST INCIDENTS", styles["KPITitle"]),
                Paragraph("FOUND BELONGINGS", styles["KPITitle"]),
                Paragraph("SUCCESSFULLY RETURNED", styles["KPITitle"]),
                Paragraph("RECOVERY RATE", styles["KPITitle"]),
            ],
            [
                Paragraph(str(kpis.get("total_items", 0)), styles["KPIValue"]),
                Paragraph(f"<font color='#dc2626'>{kpis.get('lost_items', 0)}</font>", styles["KPIValue"]),
                Paragraph(f"<font color='#059669'>{kpis.get('found_items', 0)}</font>", styles["KPIValue"]),
                Paragraph(f"<font color='#16a34a'>{kpis.get('returned_items', 0)}</font>", styles["KPIValue"]),
                Paragraph(f"<font color='#7c3aed'>{kpis.get('recovery_rate', 0.0)}%</font>", styles["KPIValue"]),
            ]
        ]
        kpi_table = Table(kpi_cells, colWidths=[108, 108, 108, 108, 108])
        kpi_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ])
        )
        story.append(kpi_table)
        story.append(Spacer(1, 14))

        # 3. Category & Hotspot Distributions Side-by-Side
        story.append(Paragraph("1. OPERATIONAL INCIDENT BREAKDOWN & HOTSPOTS", styles["SectionHeader"]))
        story.append(Spacer(1, 4))

        # Build Category subtable
        cat_rows = [[Paragraph("<b>Category</b>", styles["CellBold"]), Paragraph("<b>Items</b>", styles["CellBold"])]]
        for cat_name, count in cat_dist.items():
            cat_rows.append([Paragraph(str(cat_name), styles["CellNormal"]), Paragraph(str(count), styles["CellNormal"])])
        if len(cat_rows) == 1:
            cat_rows.append([Paragraph("No records", styles["CellNormalMuted"]), Paragraph("0", styles["CellNormalMuted"])])

        cat_table = Table(cat_rows, colWidths=[180, 80])
        cat_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ])
        )

        # Build Hotspots subtable
        hot_rows = [[Paragraph("<b>Campus Location</b>", styles["CellBold"]), Paragraph("<b>Incidents</b>", styles["CellBold"])]]
        for loc_name, count in hotspots.items():
            hot_rows.append([Paragraph(str(loc_name), styles["CellNormal"]), Paragraph(str(count), styles["CellNormal"])])
        if len(hot_rows) == 1:
            hot_rows.append([Paragraph("No records", styles["CellNormalMuted"]), Paragraph("0", styles["CellNormalMuted"])])

        hot_table = Table(hot_rows, colWidths=[180, 80])
        hot_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("PADDING", (0, 0), (-1, -1), 4),
            ])
        )

        side_by_side = Table(
            [[cat_table, hot_table]],
            colWidths=[270, 270],
        )
        side_by_side.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 0),
            ])
        )
        story.append(side_by_side)
        story.append(Spacer(1, 14))

        # 4. Item Inventory Audit Trail Table
        story.append(Paragraph("2. ASSET INVENTORY & RESOLUTION LOGS", styles["SectionHeader"]))
        story.append(Spacer(1, 4))

        inv_headers = [
            Paragraph("<b>#</b>", styles["CellBold"]),
            Paragraph("<b>Type</b>", styles["CellBold"]),
            Paragraph("<b>Title</b>", styles["CellBold"]),
            Paragraph("<b>Category</b>", styles["CellBold"]),
            Paragraph("<b>Location</b>", styles["CellBold"]),
            Paragraph("<b>Date</b>", styles["CellBold"]),
            Paragraph("<b>Status</b>", styles["CellBold"]),
        ]
        inv_data = [inv_headers]

        if not df_items.empty:
            # Sort newest first, top 35 items
            recent_items = df_items.sort_values(by="id", ascending=False).head(35)
            for _, row in recent_items.iterrows():
                status_color = "#16a34a" if row["status"] == "RETURNED" else ("#d97706" if row["status"] == "CLAIM_PENDING" else "#2563eb")
                inv_data.append([
                    Paragraph(f"#{row['id']}", styles["CellNormalMuted"]),
                    Paragraph(str(row["type"]), styles["CellNormal"]),
                    Paragraph(str(row["title"])[:35], styles["CellNormal"]),
                    Paragraph(str(row["category"]), styles["CellNormal"]),
                    Paragraph(str(row["location"])[:20], styles["CellNormal"]),
                    Paragraph(str(row["event_date"]), styles["CellNormalMuted"]),
                    Paragraph(f"<font color='{status_color}'><b>{row['status']}</b></font>", styles["CellNormal"]),
                ])
        else:
            inv_data.append([
                Paragraph("No item records registered in database.", styles["CellNormalMuted"]),
                "", "", "", "", "", ""
            ])

        inv_table = Table(
            inv_data,
            colWidths=[35, 45, 150, 85, 95, 60, 70],
            repeatRows=1,
        )
        inv_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#ffffff")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("PADDING", (0, 0), (-1, -1), 3.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ])
        )
        story.append(inv_table)
        story.append(Spacer(1, 14))

        # 5. Administrative Audit Sign-Off
        audit_cert_text = (
            "This report was compiled and verified directly from the CampusConnect relational SQLite audit logs. "
            "All recovery percentages, status modifications, and registered incidents represent verified operational "
            "records as of the report generation timestamp."
        )
        sign_block = [
            Paragraph(audit_cert_text, styles["LegalDisclaimer"]),
            Spacer(1, 10),
            Paragraph(
                f"<b>Authorized Auditor / Security Directorate:</b> {operator_name or 'Administrator'} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                f"<b>Official Seal / Stamp:</b> [ VERIFIED CAMPUS AUDIT ]",
                styles["CellNormal"],
            ),
        ]
        story.append(KeepTogether(sign_block))

        doc.build(story, canvasmaker=NumberedCanvas)
        return output_path

    @staticmethod
    def open_pdf(filepath: str) -> bool:
        """
        Open the PDF document in the default platform application.
        Returns True if launch succeeded, False otherwise.
        """
        if not filepath or not os.path.isfile(filepath):
            return False

        try:
            sys_name = platform.system()
            if sys_name == "Windows":
                os.startfile(filepath)
            elif sys_name == "Darwin":
                subprocess.Popen(["open", filepath])
            else:
                subprocess.Popen(["xdg-open", filepath])
            return True
        except Exception:
            return False
