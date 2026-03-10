import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepInFrame
)
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from models.bill import Bill
from config_loader import load_company_config

# ── Brand colours ──────────────────────────────────────────────────────────
GREEN_DARK  = colors.HexColor("#2C5F2E")
GREEN_LIGHT = colors.HexColor("#EAF2EA")
GREY_DARK   = colors.HexColor("#1A1A1A")
GREY_MID    = colors.HexColor("#5A5550")
GREY_LIGHT  = colors.HexColor("#D9D0C5")
WHITE       = colors.white


# ── Styles ─────────────────────────────────────────────────────────────────
def _styles():
    return {
        "company": ParagraphStyle(
            "company", fontName="Helvetica-Bold",
            fontSize=20, textColor=WHITE, spaceAfter=4, leading=24
        ),
        "tagline": ParagraphStyle(
            "tagline", fontName="Helvetica-Oblique",
            fontSize=9, textColor=colors.HexColor("#A8C8AA"), spaceAfter=2
        ),
        "company_detail": ParagraphStyle(
            "company_detail", fontName="Helvetica",
            fontSize=8, textColor=colors.HexColor("#C8DFC8"), leading=13, spaceAfter=0
        ),
        "invoice_title": ParagraphStyle(
            "invoice_title", fontName="Helvetica-Bold",
            fontSize=22, textColor=WHITE,
            alignment=TA_RIGHT, spaceAfter=6, leading=26
        ),
        "invoice_meta": ParagraphStyle(
            "invoice_meta", fontName="Helvetica",
            fontSize=9, textColor=colors.HexColor("#D0E8D0"),
            alignment=TA_RIGHT, leading=14
        ),
        "section_label": ParagraphStyle(
            "section_label", fontName="Helvetica-Bold",
            fontSize=8, textColor=GREY_MID, spaceAfter=3
        ),
        "field_value": ParagraphStyle(
            "field_value", fontName="Helvetica",
            fontSize=10, textColor=GREY_DARK, spaceAfter=0
        ),
        "footer": ParagraphStyle(
            "footer", fontName="Helvetica-Oblique",
            fontSize=8, textColor=GREY_MID, alignment=TA_CENTER
        ),
        "total_label": ParagraphStyle(
            "total_label", fontName="Helvetica-Bold",
            fontSize=11, textColor=WHITE, alignment=TA_LEFT
        ),
        "total_value": ParagraphStyle(
            "total_value", fontName="Helvetica-Bold",
            fontSize=13, textColor=WHITE, alignment=TA_RIGHT
        ),
    }


def export_bill_to_pdf(bill: Bill, output_dir: str = None) -> str:
    """
    Export a Bill to a formatted A4 PDF invoice.
    Company details are read from config.ini automatically.
    Returns the full path to the saved PDF file.
    """
    company = load_company_config()

    if output_dir is None:
        output_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    os.makedirs(output_dir, exist_ok=True)

    bill_id  = bill.id or "DRAFT"
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"Invoice_{bill_id}_{date_str}.pdf")

    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=16*mm,  bottomMargin=16*mm,
    )

    S = _styles()
    W = A4[0] - 36*mm
    story = []

    # ── Header ────────────────────────────────────────────────────────── #
    # Build left cell: company name + tagline + address/phone/email
    left_content = [
        Paragraph(company["name"], S["company"]),
        Paragraph(company["tagline"], S["tagline"]),
    ]
    if company["address"]:
        left_content.append(Paragraph(f'📍 {company["address"]}', S["company_detail"]))
    if company["phone"]:
        left_content.append(Paragraph(f'📞 {company["phone"]}', S["company_detail"]))
    if company["email"]:
        left_content.append(Paragraph(f'✉ {company["email"]}', S["company_detail"]))

    left_cell = KeepInFrame(W * 0.55 - 28, 80, left_content, mode="shrink")

    right_cell = KeepInFrame(
        W * 0.45 - 28, 80,
        [Paragraph("INVOICE", S["invoice_title"]),
         Paragraph(f"Invoice No: <b>#{bill_id}</b><br/>Date: {bill.date}",
                   S["invoice_meta"])],
        mode="shrink"
    )

    header_table = Table([[left_cell, right_cell]],
                         colWidths=[W * 0.55, W * 0.45])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), GREEN_DARK),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (0,  -1), 14),
        ("RIGHTPADDING", (1, 0), (1,  -1), 14),
        ("LEFTPADDING",  (1, 0), (1,  -1), 8),
        ("TOPPADDING",   (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 14),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 7*mm))

    # ── Bill-to panel ─────────────────────────────────────────────────── #
    bill_left = KeepInFrame(
        W * 0.55 - 20, 50,
        [Paragraph("BILL TO", S["section_label"]),
         Paragraph(bill.customer_name, S["field_value"])],
        mode="shrink"
    )
    bill_right = KeepInFrame(
        W * 0.45 - 20, 50,
        [Paragraph("PAYMENT STATUS", S["section_label"]),
         Paragraph("Due on Receipt", S["field_value"])],
        mode="shrink"
    )
    bill_to_table = Table([[bill_left, bill_right]],
                          colWidths=[W * 0.55, W * 0.45])
    bill_to_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), GREEN_LIGHT),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("LINEBELOW",    (0, 0), (-1, -1), 0.5, GREY_LIGHT),
    ]))
    story.append(bill_to_table)
    story.append(Spacer(1, 6*mm))

    # ── Items table ───────────────────────────────────────────────────── #
    col_widths = [W*0.06, W*0.34, W*0.12, W*0.10, W*0.19, W*0.19]

    hdr_style = ParagraphStyle("th", fontName="Helvetica-Bold",
                               fontSize=8, textColor=WHITE)
    table_data = [[
        Paragraph("#",          hdr_style),
        Paragraph("Item",       hdr_style),
        Paragraph("Size",       hdr_style),
        Paragraph("Qty",        hdr_style),
        Paragraph("Unit Price", hdr_style),
        Paragraph("Subtotal",   hdr_style),
    ]]

    cell_style = ParagraphStyle("td", fontName="Helvetica",
                                fontSize=9, textColor=GREY_DARK)
    num_style  = ParagraphStyle("num", fontName="Helvetica",
                                fontSize=9, textColor=GREY_DARK, alignment=TA_RIGHT)

    for i, item in enumerate(bill.items):
        table_data.append([
            Paragraph(str(i + 1),                    cell_style),
            Paragraph(item.item_name,                cell_style),
            Paragraph(item.size,                     cell_style),
            Paragraph(str(item.quantity),            num_style),
            Paragraph(f"LKR {item.unit_price:,.2f}", num_style),
            Paragraph(f"LKR {item.subtotal:,.2f}",   num_style),
        ])

    row_bg = []
    for r in range(1, len(table_data)):
        bg = WHITE if r % 2 == 0 else colors.HexColor("#F7F3EE")
        row_bg.append(("BACKGROUND", (0, r), (-1, r), bg))

    items_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), GREEN_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.4, GREY_LIGHT),
        ("LINEBELOW",     (0, 0), (-1, 0),  1.0, GREEN_DARK),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        *row_bg,
    ]))
    story.append(items_table)
    story.append(Spacer(1, 5*mm))

    # ── Totals block ──────────────────────────────────────────────────── #
    total_table = Table(
        [[Paragraph("TOTAL AMOUNT", S["total_label"]),
          Paragraph(f"LKR {bill.total:,.2f}", S["total_value"])]],
        colWidths=[W * 0.7, W * 0.3]
    )
    total_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), GREEN_DARK),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING",   (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 10),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 10*mm))

    # ── Footer ────────────────────────────────────────────────────────── #
    story.append(HRFlowable(width="100%", thickness=0.5,
                            color=GREY_LIGHT, spaceAfter=4))
    footer_parts = [f"Thank you for your business, {bill.customer_name}!",
                    company["name"]]
    if company["phone"]:
        footer_parts.append(company["phone"])
    if company["email"]:
        footer_parts.append(company["email"])
    story.append(Paragraph("  •  ".join(footer_parts), S["footer"]))

    doc.build(story)
    return filepath


# ── Standalone test ────────────────────────────────────────────────────── #
if __name__ == "__main__":
    from models.bill import Bill, BillItem

    bill = Bill(customer_name="Jane Smith")
    bill.id = 42
    bill.add_item(BillItem(item_id=1, item_name="Cotton Shirt",
                           size="M", quantity=3, unit_price=1599.00))
    bill.add_item(BillItem(item_id=2, item_name="Linen Trousers",
                           size="L", quantity=1, unit_price=2950.00))

    path = export_bill_to_pdf(bill)
    print(f"PDF saved to: {path}")