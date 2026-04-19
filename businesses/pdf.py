"""ReportLab print templates for the review QR — one PDF per design.

Designs (all PDFs, black+white QR for reliable scanning, accent colour in chrome):

- build_standee_pdf        A5 portrait — desk/counter standee (original)
- build_a4_poster_pdf      A4 portrait — big wall poster, "Scan to review"
- build_table_tent_pdf     A4 landscape — fold along centre, two mirrored panels
- build_counter_card_pdf   A6 portrait — small counter card (fits at checkout)
- build_sticker_sheet_pdf  A4 portrait — 6-up sticker sheet (2x3 grid)
"""

from io import BytesIO

import qrcode
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.pagesizes import A4, A5, A6, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .models import Location


BRAND = HexColor("#2563eb")
BRAND_DARK = HexColor("#1d4ed8")
ACCENT = HexColor("#7c3aed")
INK = HexColor("#0b1220")
INK_2 = HexColor("#1f2937")
MUTED = HexColor("#64748b")
STAR = HexColor("#fbbf24")
SOFT_BG = HexColor("#f8fafc")
BORDER = HexColor("#e5e7eb")


# ----------------------- shared helpers -----------------------

def _qr_image_reader(url: str, size_px: int = 1400) -> ImageReader:
    """High-res QR for crisp print. Error correction H → 30% recovery."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        border=1,
        box_size=max(4, size_px // 45),
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img = img.resize((size_px, size_px))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def _draw_stars(c, cx, cy, size=10, count=5, color=STAR):
    """Draw 5 filled stars horizontally centred at (cx, cy)."""
    gap = size * 1.3
    total_w = gap * (count - 1)
    start_x = cx - total_w / 2
    c.setFillColor(color)
    for i in range(count):
        _star_path(c, start_x + i * gap, cy, size)


def _star_path(c, x, y, size):
    """Draw a single 5-pointed star, centred at (x, y), outer radius ~size."""
    import math
    path = c.beginPath()
    outer = size
    inner = size * 0.45
    pts = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = outer if i % 2 == 0 else inner
        pts.append((x + r * math.cos(angle), y + r * math.sin(angle)))
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    path.close()
    c.drawPath(path, stroke=0, fill=1)


def _draw_logo(c, business, x, y, max_h):
    """Draw the business logo anchored at (x, y) with max height max_h. Returns drawn height or 0."""
    if not business.logo:
        return 0
    try:
        business.logo.open("rb")
        try:
            logo = ImageReader(business.logo.file)
            iw, ih = logo.getSize()
            draw_h = max_h
            draw_w = draw_h * (iw / ih)
            c.drawImage(logo, x, y, width=draw_w, height=draw_h, mask="auto", preserveAspectRatio=True)
            return draw_h
        finally:
            business.logo.close()
    except Exception:
        return 0


def _draw_rounded_rect(c, x, y, w, h, r, stroke=0, fill=1):
    c.roundRect(x, y, w, h, r, stroke=stroke, fill=fill)


def _wrap(c, text, max_w, font, size):
    """Tiny word-wrap helper returning a list of lines that fit max_w."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if stringWidth(trial, font, size) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ----------------------- 1. A5 standee (original, polished) -----------------------

def build_standee_pdf(location: Location, review_url: str) -> bytes:
    page_w, page_h = A5
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A5, pageCompression=1)
    c.setTitle(f"Tapstar standee — {location.business.name} ({location.name})")
    business = location.business

    # Top gradient-ish band (two solid strips to fake a gradient cheaply)
    c.setFillColor(BRAND)
    c.rect(0, page_h - 10 * mm, page_w, 10 * mm, stroke=0, fill=1)
    c.setFillColor(ACCENT)
    c.rect(0, page_h - 6 * mm, page_w, 2 * mm, stroke=0, fill=1)

    top_y = page_h - 24 * mm

    # Logo
    drew = _draw_logo(c, business, (page_w - 22 * mm) / 2, top_y - 22 * mm, 22 * mm)
    if drew:
        top_y -= drew + 6 * mm

    # 5 gold stars
    _draw_stars(c, page_w / 2, top_y - 4 * mm, size=5)
    top_y -= 14 * mm

    # Headline
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(page_w / 2, top_y, "Scan to review us")

    # Sub-headline
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 11)
    c.drawCentredString(page_w / 2, top_y - 8 * mm, "Takes 10 seconds — in your language")

    # QR in a rounded frame
    qr_size = 95 * mm
    qr_x = (page_w - qr_size) / 2
    qr_y = (page_h - qr_size) / 2 - 12 * mm
    c.setFillColor(SOFT_BG)
    _draw_rounded_rect(c, qr_x - 6 * mm, qr_y - 6 * mm, qr_size + 12 * mm, qr_size + 12 * mm, 8 * mm, stroke=0, fill=1)
    c.drawImage(_qr_image_reader(review_url), qr_x, qr_y, width=qr_size, height=qr_size)

    # Business name
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(page_w / 2, qr_y - 14 * mm, business.name)

    if location.name and location.name.lower() != "main":
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 11)
        c.drawCentredString(page_w / 2, qr_y - 20 * mm, location.name)

    # Footer
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawCentredString(page_w / 2, 10 * mm, "Powered by Tapstar")

    c.showPage()
    c.save()
    return buf.getvalue()


# ----------------------- 2. A4 wall poster -----------------------

def build_a4_poster_pdf(location: Location, review_url: str) -> bytes:
    page_w, page_h = A4  # 210 x 297 mm
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, pageCompression=1)
    c.setTitle(f"Tapstar poster — {location.business.name}")
    business = location.business

    # Bold coloured header band
    header_h = 48 * mm
    c.setFillColor(BRAND)
    c.rect(0, page_h - header_h, page_w, header_h, stroke=0, fill=1)

    # Diagonal accent strip
    c.setFillColor(ACCENT)
    path = c.beginPath()
    path.moveTo(0, page_h - header_h)
    path.lineTo(page_w, page_h - header_h + 6 * mm)
    path.lineTo(page_w, page_h - header_h)
    path.close()
    c.drawPath(path, stroke=0, fill=1)

    # Logo in header (left)
    drew = _draw_logo(c, business, 18 * mm, page_h - header_h + 12 * mm, 24 * mm)

    # Business name in header (right)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 22)
    text_x = 50 * mm if drew else 18 * mm
    c.drawString(text_x, page_h - header_h + 26 * mm, business.name)
    c.setFillColor(HexColor("#dbeafe"))
    c.setFont("Helvetica", 11)
    c.drawString(text_x, page_h - header_h + 18 * mm, business.get_business_type_display())

    # Stars row
    _draw_stars(c, page_w / 2, page_h - header_h - 16 * mm, size=7)

    # Headline
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(page_w / 2, page_h - header_h - 32 * mm, "Scan to review us")

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 14)
    c.drawCentredString(page_w / 2, page_h - header_h - 42 * mm, "Point your camera at the code — then follow the steps.")

    # QR centred
    qr_size = 110 * mm
    qr_x = (page_w - qr_size) / 2
    qr_y = page_h - header_h - 42 * mm - qr_size - 14 * mm

    # Frame around QR
    c.setFillColor(SOFT_BG)
    _draw_rounded_rect(c, qr_x - 10 * mm, qr_y - 10 * mm, qr_size + 20 * mm, qr_size + 20 * mm, 10 * mm, stroke=0, fill=1)
    c.drawImage(_qr_image_reader(review_url), qr_x, qr_y, width=qr_size, height=qr_size)

    # "How it works" footer row — 3 steps
    steps = [("1", "Scan"), ("2", "Rate"), ("3", "Done")]
    step_y = 32 * mm
    slot_w = page_w / 3
    for i, (num, label) in enumerate(steps):
        cx = slot_w * i + slot_w / 2
        # Numbered circle
        c.setFillColor(BRAND)
        c.circle(cx - 18 * mm, step_y, 5 * mm, stroke=0, fill=1)
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(cx - 18 * mm, step_y - 2 * mm, num)
        # Label
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(cx - 10 * mm, step_y - 2 * mm, label)

    # Footer
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_w / 2, 14 * mm, "Your review helps us grow · Powered by Tapstar")

    c.showPage()
    c.save()
    return buf.getvalue()


# ----------------------- 3. Table tent (A4 landscape, fold in middle) -----------------------

def build_table_tent_pdf(location: Location, review_url: str) -> bytes:
    """A4 landscape with two mirrored panels (top rotated 180°) — fold along middle to stand."""
    page = landscape(A4)  # 297 x 210 mm
    page_w, page_h = page
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=page, pageCompression=1)
    c.setTitle(f"Tapstar table tent — {location.business.name}")
    business = location.business

    half_h = page_h / 2
    qr_reader = _qr_image_reader(review_url)

    def draw_panel():
        """Draw one panel's worth of content, anchored at origin (0,0) with width page_w, height half_h."""
        # Soft background
        c.setFillColor(HexColor("#ffffff"))
        c.rect(0, 0, page_w, half_h, stroke=0, fill=1)

        # Left: branding + copy
        left_x = 18 * mm
        text_block_y = half_h - 26 * mm

        drew = _draw_logo(c, business, left_x, text_block_y - 22 * mm, 22 * mm)
        if drew:
            text_block_y -= drew + 6 * mm
        else:
            text_block_y -= 4 * mm

        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 28)
        c.drawString(left_x, text_block_y, business.name)

        c.setFillColor(MUTED)
        c.setFont("Helvetica", 12)
        c.drawString(left_x, text_block_y - 9 * mm, "Enjoying your visit?")

        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(left_x, text_block_y - 22 * mm, "Scan to review us")

        # Stars
        _draw_stars(c, left_x + 30 * mm, text_block_y - 34 * mm, size=6)

        c.setFillColor(MUTED)
        c.setFont("Helvetica", 11)
        c.drawString(left_x, text_block_y - 45 * mm, "Takes 10 seconds · In your language")

        # Right: QR
        qr_size = 70 * mm
        qr_x = page_w - qr_size - 22 * mm
        qr_y = (half_h - qr_size) / 2
        c.setFillColor(SOFT_BG)
        _draw_rounded_rect(c, qr_x - 6 * mm, qr_y - 6 * mm, qr_size + 12 * mm, qr_size + 12 * mm, 8 * mm, stroke=0, fill=1)
        c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

        # Footer
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 8)
        c.drawString(left_x, 8 * mm, "Powered by Tapstar")

    # Bottom (upright) panel
    c.saveState()
    c.translate(0, 0)
    draw_panel()
    c.restoreState()

    # Top panel — rotated 180° so when the paper is folded, the top reads right-side up from the other side
    c.saveState()
    c.translate(page_w, page_h)
    c.rotate(180)
    draw_panel()
    c.restoreState()

    # Fold line
    c.setStrokeColor(BORDER)
    c.setDash(2, 3)
    c.setLineWidth(0.5)
    c.line(0, half_h, page_w, half_h)
    c.setDash()

    # Tiny "Fold here" label
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    c.drawCentredString(page_w / 2, half_h + 1 * mm, "– – – fold here – – –")

    c.showPage()
    c.save()
    return buf.getvalue()


# ----------------------- 4. A6 counter card -----------------------

def build_counter_card_pdf(location: Location, review_url: str) -> bytes:
    """Small A6 card (105 x 148 mm) — fits at the checkout counter / register."""
    page_w, page_h = A6
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A6, pageCompression=1)
    c.setTitle(f"Tapstar counter card — {location.business.name}")
    business = location.business

    # Accent header
    header_h = 22 * mm
    c.setFillColor(BRAND)
    c.rect(0, page_h - header_h, page_w, header_h, stroke=0, fill=1)

    # Header text
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(page_w / 2, page_h - header_h + 12 * mm, "Loved your visit?")
    c.setFillColor(HexColor("#dbeafe"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_w / 2, page_h - header_h + 6 * mm, "Help us with a 10-second review")

    # Stars
    _draw_stars(c, page_w / 2, page_h - header_h - 10 * mm, size=5)

    # QR
    qr_size = 60 * mm
    qr_x = (page_w - qr_size) / 2
    qr_y = page_h - header_h - 16 * mm - qr_size

    c.setFillColor(SOFT_BG)
    _draw_rounded_rect(c, qr_x - 4 * mm, qr_y - 4 * mm, qr_size + 8 * mm, qr_size + 8 * mm, 6 * mm, stroke=0, fill=1)
    c.drawImage(_qr_image_reader(review_url), qr_x, qr_y, width=qr_size, height=qr_size)

    # Business name
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(page_w / 2, qr_y - 10 * mm, business.name)

    # Footer
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    c.drawCentredString(page_w / 2, 8 * mm, "Powered by Tapstar")

    c.showPage()
    c.save()
    return buf.getvalue()


# ----------------------- 5. A4 sticker sheet (6-up) -----------------------

def build_sticker_sheet_pdf(location: Location, review_url: str) -> bytes:
    """A4 portrait with 6 identical stickers (2 cols x 3 rows). Cut lines included."""
    page_w, page_h = A4  # 210 x 297 mm
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, pageCompression=1)
    c.setTitle(f"Tapstar sticker sheet — {location.business.name}")
    business = location.business

    cols, rows = 2, 3
    margin_x = 10 * mm
    margin_y = 15 * mm
    gap = 6 * mm
    cell_w = (page_w - 2 * margin_x - (cols - 1) * gap) / cols
    cell_h = (page_h - 2 * margin_y - (rows - 1) * gap) / rows
    qr_reader = _qr_image_reader(review_url)

    def draw_sticker(x, y, w, h):
        # Rounded white card with subtle border
        c.setFillColor(HexColor("#ffffff"))
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.6)
        _draw_rounded_rect(c, x, y, w, h, 6 * mm, stroke=1, fill=1)

        # Top coloured strip (sticker accent)
        c.setFillColor(BRAND)
        c.rect(x, y + h - 10 * mm, w, 10 * mm, stroke=0, fill=1)

        # Re-round the top corners
        c.setFillColor(HexColor("#ffffff"))
        c.rect(x, y + h - 10 * mm - 1, 4 * mm, 1, stroke=0, fill=1)

        # "Scan to review"
        c.setFillColor(HexColor("#ffffff"))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x + w / 2, y + h - 7 * mm, "Scan to review us")

        # QR
        qr_size = min(w, h) - 32 * mm
        qr_size = max(qr_size, 30 * mm)
        qr_x = x + (w - qr_size) / 2
        qr_y = y + (h - qr_size) / 2 - 3 * mm
        c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

        # Business name
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x + w / 2, y + 7 * mm, business.name[:28])

    for row in range(rows):
        for col in range(cols):
            cx = margin_x + col * (cell_w + gap)
            cy = margin_y + row * (cell_h + gap)
            draw_sticker(cx, cy, cell_w, cell_h)

    # Dashed cut guides between rows/cols (outside the cards, near margins)
    c.setStrokeColor(BORDER)
    c.setDash(2, 3)
    c.setLineWidth(0.4)
    # vertical cut lines
    for i in range(1, cols):
        x = margin_x + i * cell_w + (i - 0.5) * gap
        c.line(x, 5 * mm, x, page_h - 5 * mm)
    # horizontal cut lines
    for i in range(1, rows):
        y = margin_y + i * cell_h + (i - 0.5) * gap
        c.line(5 * mm, y, page_w - 5 * mm, y)
    c.setDash()

    # Bottom caption
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    c.drawCentredString(page_w / 2, 8 * mm, "Cut along dashed lines · Powered by Tapstar")

    c.showPage()
    c.save()
    return buf.getvalue()
