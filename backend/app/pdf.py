"""Dependency-free PDF writer for official documents (notices, court reports).

Produces PDF 1.4 with the standard Helvetica/Courier fonts (no embedding), flowing
text with word wrap, tables that repeat their header across pages, vector bar
charts and simple flow diagrams. Text is encoded as WinAnsi (cp1252); characters
outside it are replaced.
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Sequence

PAGE_W, PAGE_H = 595.28, 841.89  # A4 in points
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 50.0, 64.0, 60.0

FONTS = {"regular": ("F1", "Helvetica"), "bold": ("F2", "Helvetica-Bold"), "italic": ("F3", "Helvetica-Oblique"), "mono": ("F4", "Courier")}

# Standard AFM advance widths (1/1000 em) for ASCII 32..126.
_HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584]
_HELV_B = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584]

Color = tuple[float, float, float]
BLACK: Color = (0, 0, 0)
GREY: Color = (0.42, 0.45, 0.5)
LIGHT: Color = (0.93, 0.94, 0.96)
RULE: Color = (0.78, 0.8, 0.84)
NAVY: Color = (0.08, 0.16, 0.33)
ACCENT: Color = (0.05, 0.45, 0.55)
AMBER: Color = (0.75, 0.47, 0.02)
RED: Color = (0.72, 0.12, 0.12)
GREEN: Color = (0.1, 0.5, 0.25)

_REPLACEMENTS = {"→": "->", "←": "<-", "✓": "[x]", "✗": "[ ]", "≤": "<=", "≥": ">=", "₹": "Rs.", "×": "x"}


def clean(text: object) -> str:
    s = "" if text is None else str(text)
    for k, v in _REPLACEMENTS.items():
        s = s.replace(k, v)
    return s.encode("cp1252", errors="replace").decode("cp1252")


def text_width(text: str, font: str = "regular", size: float = 10) -> float:
    if font == "mono":
        return len(text) * 600 * size / 1000
    table = _HELV_B if font == "bold" else _HELV
    total = 0
    for ch in text:
        o = ord(ch)
        total += table[o - 32] if 32 <= o <= 126 else 556
    return total * size / 1000


def wrap(text: str, width: float, font: str = "regular", size: float = 10) -> list[str]:
    lines: list[str] = []
    for para in clean(text).split("\n"):
        words, line = para.split(" "), ""
        for word in words:
            candidate = f"{line} {word}" if line else word
            if text_width(candidate, font, size) <= width:
                line = candidate
                continue
            if line:
                lines.append(line)
            # Hard-break tokens longer than the line (hashes, addresses).
            while text_width(word, font, size) > width:
                cut = len(word)
                while cut > 1 and text_width(word[:cut], font, size) > width:
                    cut -= 1
                lines.append(word[:cut])
                word = word[cut:]
            line = word
        lines.append(line)
    return lines


def _esc(s: str) -> bytes:
    raw = clean(s).encode("cp1252", errors="replace")
    return raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


@dataclass
class _Page:
    ops: list[bytes] = field(default_factory=list)
    links: list[tuple[float, float, float, float, str]] = field(default_factory=list)


class PdfDocument:
    """A flowing A4 document. Coordinates for drawing primitives use PDF space (origin bottom-left)."""

    def __init__(self, title: str, header_left: str = "", header_right: str = "", footer_note: str = ""):
        self.title, self.header_left, self.header_right, self.footer_note = title, header_left, header_right, footer_note
        self.pages: list[_Page] = []
        self.y = 0.0
        self.content_width = PAGE_W - 2 * MARGIN_X
        self.new_page()

    # ---- primitives -------------------------------------------------------
    @property
    def _page(self) -> _Page:
        return self.pages[-1]

    def _op(self, s: str | bytes) -> None:
        self._page.ops.append(s if isinstance(s, bytes) else s.encode("latin-1"))

    def text(self, x: float, y: float, s: str, font: str = "regular", size: float = 10, color: Color = BLACK) -> None:
        name = FONTS[font][0]
        self._op(f"BT {color[0]:.3f} {color[1]:.3f} {color[2]:.3f} rg /{name} {size:.2f} Tf {x:.2f} {y:.2f} Td (".encode() + _esc(s) + b") Tj ET")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: Color = RULE, width: float = 0.6) -> None:
        self._op(f"{color[0]:.3f} {color[1]:.3f} {color[2]:.3f} RG {width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def rect(self, x: float, y: float, w: float, h: float, fill: Color | None = None, stroke: Color | None = None, width: float = 0.6) -> None:
        ops = ""
        if fill:
            ops += f"{fill[0]:.3f} {fill[1]:.3f} {fill[2]:.3f} rg "
        if stroke:
            ops += f"{stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} RG {width:.2f} w "
        paint = "B" if fill and stroke else "f" if fill else "S"
        self._op(f"{ops}{x:.2f} {y:.2f} {w:.2f} {h:.2f} re {paint}")

    def circle(self, cx: float, cy: float, r: float, fill: Color, stroke: Color = BLACK) -> None:
        k = 0.5523 * r
        self._op(
            f"{fill[0]:.3f} {fill[1]:.3f} {fill[2]:.3f} rg {stroke[0]:.3f} {stroke[1]:.3f} {stroke[2]:.3f} RG 0.6 w "
            f"{cx + r:.2f} {cy:.2f} m {cx + r:.2f} {cy + k:.2f} {cx + k:.2f} {cy + r:.2f} {cx:.2f} {cy + r:.2f} c "
            f"{cx - k:.2f} {cy + r:.2f} {cx - r:.2f} {cy + k:.2f} {cx - r:.2f} {cy:.2f} c "
            f"{cx - r:.2f} {cy - k:.2f} {cx - k:.2f} {cy - r:.2f} {cx:.2f} {cy - r:.2f} c "
            f"{cx + k:.2f} {cy - r:.2f} {cx + r:.2f} {cy - k:.2f} {cx + r:.2f} {cy:.2f} c B"
        )

    def link(self, x: float, y: float, w: float, h: float, url: str) -> None:
        self._page.links.append((x, y, x + w, y + h, url))

    # ---- flow layout ------------------------------------------------------
    def new_page(self) -> None:
        self.pages.append(_Page())
        self.y = PAGE_H - MARGIN_TOP

    def ensure(self, height: float) -> None:
        if self.y - height < MARGIN_BOTTOM:
            self.new_page()

    def space(self, h: float = 8) -> None:
        self.y -= h

    def heading(self, s: str, level: int = 1) -> None:
        size = {0: 18, 1: 13, 2: 11}[level]
        self.ensure(size + 24)
        self.space(6 if level else 0)
        self.text(MARGIN_X, self.y - size, s, "bold", size, NAVY)
        self.y -= size + 4
        if level == 1:
            self.line(MARGIN_X, self.y, PAGE_W - MARGIN_X, self.y, NAVY, 0.9)
        self.y -= 8

    def paragraph(self, s: str, size: float = 10, font: str = "regular", color: Color = BLACK, indent: float = 0, leading: float = 1.35) -> None:
        for ln in wrap(s, self.content_width - indent, font, size):
            self.ensure(size * leading)
            self.text(MARGIN_X + indent, self.y - size, ln, font, size, color)
            self.y -= size * leading
        self.y -= 3

    def bullets(self, items: Sequence[str], size: float = 10) -> None:
        for item in items:
            lines = wrap(item, self.content_width - 14, "regular", size)
            for i, ln in enumerate(lines):
                self.ensure(size * 1.35)
                if i == 0:
                    self.text(MARGIN_X + 2, self.y - size, "•", "regular", size)
                self.text(MARGIN_X + 14, self.y - size, ln, "regular", size)
                self.y -= size * 1.35
        self.y -= 3

    def notice_box(self, s: str, color: Color = AMBER, size: float = 8.5) -> None:
        lines = wrap(s, self.content_width - 16, "regular", size)
        h = len(lines) * size * 1.35 + 10
        self.ensure(h + 4)
        self.rect(MARGIN_X, self.y - h, self.content_width, h, fill=(1, 0.97, 0.9) if color == AMBER else LIGHT, stroke=color)
        yy = self.y - 5 - size
        for ln in lines:
            self.text(MARGIN_X + 8, yy, ln, "regular", size, BLACK)
            yy -= size * 1.35
        self.y -= h + 8

    def kv(self, rows: Sequence[tuple[str, str]], key_width: float = 150, size: float = 9.5) -> None:
        for key, value in rows:
            lines = wrap(value or "-", self.content_width - key_width, "mono" if _looks_like_id(value) else "regular", size)
            h = len(lines) * size * 1.35 + 4
            self.ensure(h)
            self.text(MARGIN_X, self.y - size, key, "bold", size, GREY)
            yy = self.y - size
            for ln in lines:
                self.text(MARGIN_X + key_width, yy, ln, "mono" if _looks_like_id(value) else "regular", size)
                yy -= size * 1.35
            self.y -= h
            self.line(MARGIN_X, self.y + 1, PAGE_W - MARGIN_X, self.y + 1, LIGHT, 0.5)
        self.y -= 6

    def table(self, headers: Sequence[str], rows: Sequence[Sequence[object]], widths: Sequence[float], size: float = 8, mono_cols: Sequence[int] = ()) -> None:
        total = sum(widths)
        widths = [w * self.content_width / total for w in widths]
        pad = 3

        def draw_header() -> None:
            h = size * 1.35 + 2 * pad
            self.ensure(h + size * 3)
            self.rect(MARGIN_X, self.y - h, self.content_width, h, fill=NAVY)
            x = MARGIN_X
            for head, w in zip(headers, widths):
                self.text(x + pad, self.y - pad - size, head, "bold", size, (1, 1, 1))
                x += w
            self.y -= h

        draw_header()
        for index, row in enumerate(rows):
            cells = []
            for col, (value, w) in enumerate(zip(row, widths)):
                font = "mono" if col in mono_cols else "regular"
                cells.append((font, wrap(clean(value), w - 2 * pad, font, size)))
            h = max(len(c[1]) for c in cells) * size * 1.3 + 2 * pad
            if self.y - h < MARGIN_BOTTOM:
                self.new_page()
                draw_header()
            if index % 2:
                self.rect(MARGIN_X, self.y - h, self.content_width, h, fill=LIGHT)
            x = MARGIN_X
            for (font, lines), w in zip(cells, widths):
                yy = self.y - pad - size
                for ln in lines:
                    self.text(x + pad, yy, ln, font, size)
                    yy -= size * 1.3
                x += w
            self.y -= h
        self.line(MARGIN_X, self.y, PAGE_W - MARGIN_X, self.y, RULE)
        self.y -= 8

    def bar_chart(self, title: str, labels: Sequence[str], values: Sequence[float], height: float = 150, color: Color = ACCENT, value_fmt: Callable[[float], str] = lambda v: f"{v:,.0f}") -> None:
        self.ensure(height + 40)
        self.text(MARGIN_X, self.y - 10, title, "bold", 9.5, NAVY)
        top = self.y - 20
        base = top - height + 26
        chart_h = height - 40
        n = max(1, len(values))
        slot = self.content_width / n
        peak = max(values) if values and max(values) > 0 else 1
        self.line(MARGIN_X, base, PAGE_W - MARGIN_X, base, GREY, 0.7)
        for i, (label, value) in enumerate(zip(labels, values)):
            bw = min(46, slot * 0.62)
            x = MARGIN_X + i * slot + (slot - bw) / 2
            h = chart_h * (value / peak) if value > 0 else 0
            if h:
                self.rect(x, base, bw, max(h, 1), fill=color)
            v = value_fmt(value)
            self.text(x + bw / 2 - text_width(v, "regular", 7) / 2, base + h + 3, v, "regular", 7, GREY)
            lab = label if text_width(label, "regular", 7) <= slot - 2 else wrap(label, slot - 2, "regular", 7)[0]
            self.text(MARGIN_X + i * slot + slot / 2 - text_width(lab, "regular", 7) / 2, base - 10, lab, "regular", 7)
        if not values:
            self.text(MARGIN_X, base + 10, "No data recorded.", "italic", 8, GREY)
        self.y = top - height + 6

    def hbar_chart(self, title: str, labels: Sequence[str], values: Sequence[float], color: Color = ACCENT, value_fmt: Callable[[float], str] = lambda v: f"{v:.2f}", max_value: float | None = None) -> None:
        row_h = 15
        self.ensure(len(values) * row_h + 30)
        self.text(MARGIN_X, self.y - 10, title, "bold", 9.5, NAVY)
        self.y -= 18
        label_w, value_w = 150, 50
        bar_w = self.content_width - label_w - value_w
        peak = max_value or (max(values) if values and max(values) > 0 else 1)
        for label, value in zip(labels, values):
            lab = wrap(label, label_w - 6, "regular", 8)[0]
            self.text(MARGIN_X, self.y - 9, lab, "regular", 8)
            self.rect(MARGIN_X + label_w, self.y - 11, bar_w, 9, fill=LIGHT)
            if value > 0:
                self.rect(MARGIN_X + label_w, self.y - 11, max(1.5, bar_w * min(1, value / peak)), 9, fill=color)
            self.text(MARGIN_X + label_w + bar_w + 6, self.y - 9, value_fmt(value), "regular", 8)
            self.y -= row_h
        self.y -= 8

    def signature_block(self, lines: Sequence[str], label: str = "Signature and seal") -> None:
        self.ensure(90)
        self.space(26)
        self.line(PAGE_W - MARGIN_X - 200, self.y, PAGE_W - MARGIN_X, self.y, BLACK, 0.7)
        self.text(PAGE_W - MARGIN_X - 200, self.y - 11, label, "italic", 8, GREY)
        self.y -= 16
        for ln in lines:
            self.text(PAGE_W - MARGIN_X - 200, self.y - 9, ln, "regular", 9)
            self.y -= 12
        self.y -= 6

    # ---- output -----------------------------------------------------------
    def _decorate(self) -> None:
        total = len(self.pages)
        for number, page in enumerate(self.pages, start=1):
            ops = page.ops
            header: list[bytes] = []
            footer: list[bytes] = []
            saved = self.pages
            self.pages = [page]
            page.ops = header
            right_w = text_width(clean(self.header_right), "regular", 8)
            left = clean(self.header_left)
            while left and text_width(left, "bold", 8) > self.content_width - right_w - 16:
                left = left[:-2] + "…" if len(left) > 2 else ""
                left = clean(left)
            self.text(MARGIN_X, PAGE_H - 36, left, "bold", 8, NAVY)
            self.text(PAGE_W - MARGIN_X - right_w, PAGE_H - 36, self.header_right, "regular", 8, GREY)
            self.line(MARGIN_X, PAGE_H - 42, PAGE_W - MARGIN_X, PAGE_H - 42, RULE, 0.5)
            page.ops = footer
            self.line(MARGIN_X, 44, PAGE_W - MARGIN_X, 44, RULE, 0.5)
            self.text(MARGIN_X, 32, self.footer_note, "regular", 7, GREY)
            label = f"Page {number} of {total}"
            self.text(PAGE_W - MARGIN_X - text_width(label, "regular", 8), 32, label, "regular", 8, GREY)
            page.ops = header + ops + footer
            self.pages = saved

    def to_bytes(self, created: datetime | None = None) -> bytes:
        self._decorate()
        created = created or datetime.now(timezone.utc)
        objects: list[bytes] = []

        def add(obj: bytes) -> int:
            objects.append(obj)
            return len(objects)

        font_ids = {key: add(f"<< /Type /Font /Subtype /Type1 /BaseFont /{base} /Encoding /WinAnsiEncoding >>".encode()) for key, (_, base) in FONTS.items()}
        font_res = " ".join(f"/{FONTS[k][0]} {font_ids[k]} 0 R" for k in FONTS)
        pages_id = len(objects) + 1
        objects.append(b"")  # placeholder for /Pages
        page_ids = []
        for page in self.pages:
            stream = zlib.compress(b"\n".join(page.ops))
            content_id = add(f"<< /Length {len(stream)} /Filter /FlateDecode >>\nstream\n".encode() + stream + b"\nendstream")
            annots = []
            for x1, y1, x2, y2, url in page.links:
                annots.append(add(f"<< /Type /Annot /Subtype /Link /Rect [{x1:.2f} {y1:.2f} {x2:.2f} {y2:.2f}] /Border [0 0 0] /A << /S /URI /URI (".encode() + _esc(url) + b") >> >>"))
            annot_str = f" /Annots [{' '.join(f'{a} 0 R' for a in annots)}]" if annots else ""
            page_ids.append(add(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] /Resources << /Font << {font_res} >> >> /Contents {content_id} 0 R{annot_str} >>".encode()))
        objects[pages_id - 1] = f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] /Count {len(page_ids)} >>".encode()
        stamp = created.strftime("D:%Y%m%d%H%M%SZ")
        info_id = add(b"<< /Title (" + _esc(self.title) + f") /Producer (VAULT-X document engine) /CreationDate ({stamp}) >>".encode())
        catalog_id = add(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(out))
            out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
        xref = len(out)
        out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
        for off in offsets:
            out += f"{off:010d} 00000 n \n".encode()
        out += f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R /Info {info_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        return bytes(out)


def _looks_like_id(value: str | None) -> bool:
    v = value or ""
    return " " not in v and len(v) >= 24
