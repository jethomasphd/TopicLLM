"""Render the software paper's PDF from its web edition.

    python -m pip install ".[docs]"
    python scripts/render-methods.py

Reads docs/paper/index.html (the maintained source) and writes
docs/preprints/TopicLLM_Software_Paper_2026-11-23.pdf, embedding the same SVG
figures the website uses as vector drawings. Renders every page to
build-qa/paper_pdf_qa/ for visual review.
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import urljoin

import pypdfium2 as pdfium
from lxml import html as LH
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Flowable, KeepTogether, LongTable, Paragraph, SimpleDocTemplate, Spacer,
                                TableStyle)
from svglib.svglib import svg2rlg

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "docs" / "paper" / "index.html"
OUT = REPO / "docs" / "preprints" / "TopicLLM_Software_Paper_2026-11-23.pdf"
QA = REPO / "build-qa" / "paper_pdf_qa"
WIDTH = 468  # text block, points

# Fonts with Greek and typographic glyphs (κ, ᵥ, –, “ ”). Liberation/DejaVu ship
# with most Linux systems; Windows and macOS fall back to their Times/Arial.
CANDIDATES = {
    "Text": ["/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", "C:/Windows/Fonts/times.ttf", "/Library/Fonts/Times New Roman.ttf"],
    "TextBold": ["/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", "C:/Windows/Fonts/timesbd.ttf", "/Library/Fonts/Times New Roman Bold.ttf"],
    "TextItalic": ["/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", "C:/Windows/Fonts/timesi.ttf", "/Library/Fonts/Times New Roman Italic.ttf"],
    "TextBI": ["/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf", "C:/Windows/Fonts/timesbi.ttf", "/Library/Fonts/Times New Roman Bold Italic.ttf"],
    "UI": ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "C:/Windows/Fonts/arial.ttf", "/Library/Fonts/Arial.ttf"],
    "UIBold": ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf", "/Library/Fonts/Arial Bold.ttf"],
    "Mono": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "C:/Windows/Fonts/consola.ttf", "/Library/Fonts/Courier New.ttf"],
}
FALLBACK = {"Text": "Times-Roman", "TextBold": "Times-Bold", "TextItalic": "Times-Italic", "TextBI": "Times-BoldItalic",
            "UI": "Helvetica", "UIBold": "Helvetica-Bold", "Mono": "Courier"}
for name, files in CANDIDATES.items():
    found = next((f for f in files if Path(f).exists()), None)
    if found:
        pdfmetrics.registerFont(TTFont(name, found))
    else:
        pdfmetrics.registerFont(pdfmetrics.Font(name, FALLBACK[name], "WinAnsiEncoding"))
pdfmetrics.registerFontFamily("Text", normal="Text", bold="TextBold", italic="TextItalic", boldItalic="TextBI")
pdfmetrics.registerFontFamily("UI", normal="UI", bold="UIBold", italic="UI", boldItalic="UIBold")

INK = colors.HexColor("#0f2436")
MUTED = colors.HexColor("#5b6b78")
S = {
    "edition": ParagraphStyle("edition", fontName="UI", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=10),
    "title": ParagraphStyle("title", fontName="UIBold", fontSize=20, leading=24, textColor=INK, spaceAfter=10),
    "byline": ParagraphStyle("byline", fontName="UI", fontSize=10, leading=13, textColor=INK, spaceAfter=18),
    "abstract_h": ParagraphStyle("abstract_h", fontName="UIBold", fontSize=10, leading=13, textColor=INK, spaceAfter=4),
    "abstract": ParagraphStyle("abstract", fontName="Text", fontSize=10, leading=13.4, textColor=INK, spaceAfter=6,
                               leftIndent=14, rightIndent=14),
    "h2": ParagraphStyle("h2", fontName="UIBold", fontSize=13, leading=16, textColor=INK, spaceBefore=16, spaceAfter=6, keepWithNext=True),
    "h3": ParagraphStyle("h3", fontName="UIBold", fontSize=10.5, leading=13, textColor=INK, spaceBefore=10, spaceAfter=4, keepWithNext=True),
    "body": ParagraphStyle("body", fontName="Text", fontSize=10.5, leading=14.2, textColor=INK, spaceAfter=7, allowWidows=0, allowOrphans=0),
    "small": ParagraphStyle("small", fontName="UI", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=6),
    "caption": ParagraphStyle("caption", fontName="UI", fontSize=8.5, leading=11.2, textColor=INK, spaceBefore=4, spaceAfter=12),
    "cell": ParagraphStyle("cell", fontName="UI", fontSize=8, leading=10, textColor=INK),
    "cellr": ParagraphStyle("cellr", fontName="UI", fontSize=8, leading=10, textColor=INK, alignment=2),
    "prompt": ParagraphStyle("prompt", fontName="Mono", fontSize=8.3, leading=11.5, textColor=INK, leftIndent=14, rightIndent=14,
                             spaceBefore=4, spaceAfter=10, backColor=colors.HexColor("#f2f5f7"), borderPadding=(6, 6, 6, 6)),
    "ref": ParagraphStyle("ref", fontName="Text", fontSize=9, leading=11.6, textColor=INK, leftIndent=16, firstLineIndent=-16, spaceAfter=4),
}


def markup(el) -> str:
    """Inline HTML → ReportLab paragraph markup."""
    out = html.escape(el.text or "")
    for child in el:
        inner = markup(child)
        tag = child.tag
        if tag == "br":
            out += "<br/>"
        elif tag in ("b", "strong"):
            out += f"<b>{inner}</b>"
        elif tag in ("i", "em"):
            out += f"<i>{inner}</i>"
        elif tag == "sub":
            out += f"<sub>{inner}</sub>"
        elif tag == "sup":
            out += f"<super>{inner}</super>"
        elif tag == "code":
            out += f'<font name="Mono" size="8.6">{inner}</font>'
        elif tag == "a" and child.get("href"):
            href = urljoin("https://topicllm.dev/paper/", child.get("href"))
            out += f'<link href="{html.escape(href, quote=True)}" color="#0d7d62">{inner}</link>'
        else:
            out += inner
        out += html.escape(child.tail or "")
    return re.sub(r"\s+", " ", out).strip()


class Figure(Flowable):
    """An SVG figure scaled to the text width."""

    def __init__(self, svg_path: Path):
        super().__init__()
        drawing: Drawing = svg2rlg(str(svg_path))
        # Fit the text width, but keep tall charts short enough to share a page.
        tallest = {"finding": 225, "compare": 250, "confusion": 400}.get(svg_path.stem, 260)
        scale = min(WIDTH / drawing.width, tallest / drawing.height)
        drawing.scale(scale, scale)
        drawing.width, drawing.height = drawing.width * scale, drawing.height * scale
        self.drawing = drawing
        self.width, self.height = WIDTH, drawing.height
        self.offset = (WIDTH - drawing.width) / 2

    def draw(self):
        self.drawing.drawOn(self.canv, self.offset, 0)


def table(el):
    caption = el.find("caption")
    rows = el.xpath(".//tr")
    ncols = len(rows[0])
    data = []
    for r in rows:
        data.append([Paragraph(markup(c), S["cellr"] if "n" in (c.get("class") or "").split() else S["cell"]) for c in r])
    widths = {4: [180, 180, 48, 60]}.get(ncols, [WIDTH / ncols] * ncols)
    if caption is not None and "Table 2" in caption.text_content():
        widths = [258, 70, 70, 70]
    t = LongTable(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK), ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#d5dce1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    parts = [Paragraph(markup(caption), S["caption"])] if caption is not None else []
    return [KeepTogether(parts + [t]), Spacer(1, 10)]


def pull_heading(story: list) -> list:
    """Keep a section heading on the same page as the figure or table that follows it."""
    if story and isinstance(story[-1], Paragraph) and story[-1].style.name in ("h2", "h3"):
        return [story.pop()]
    return []


def main() -> None:
    doc = LH.fromstring(SOURCE.read_text(encoding="utf-8"))
    header = doc.xpath('//header[@class="ph"]')[0]
    article = doc.xpath("//article")[0]
    story = [
        Paragraph(html.escape(header.xpath('.//p[@class="edition"]')[0].text_content()), S["edition"]),
        Paragraph(markup(header.find("h1")), S["title"]),
        Paragraph("Jacob E. Thomas · jethomasphd@gmail.com · https://topicllm.dev/paper/", S["byline"]),
    ]
    figures_dir = REPO / "docs" / "paper"
    for el in article.iter():
        if el.getparent() is not article and not (el.getparent() is not None and el.getparent().get("class") == "abstract"):
            continue
        cls = el.get("class") or ""
        if el.tag == "section" and "abstract" in cls:
            continue
        if el.getparent() is not None and el.getparent().get("class") == "abstract":
            if el.tag == "h2":
                story.append(Paragraph("Summary", S["abstract_h"]))
            elif el.tag == "p":
                story.append(Paragraph(markup(el), S["small"] if "small" in cls else S["abstract"]))
            continue
        if el.tag == "h2":
            story.append(Paragraph(markup(el), S["h2"]))
        elif el.tag == "h3":
            story.append(Paragraph(markup(el), S["h3"]))
        elif el.tag == "p":
            story.append(Paragraph(markup(el), S["prompt"] if "prompt" in cls else S["body"]))
        elif el.tag == "figure":
            img = el.find("img")
            svg = (figures_dir / img.get("src")).resolve()
            story.append(KeepTogether(pull_heading(story) + [Figure(svg), Paragraph(markup(el.find("figcaption")), S["caption"])]))
        elif el.tag == "table":
            head = pull_heading(story)
            parts = table(el)
            if head:
                parts[0] = KeepTogether(head + [parts[0]])
            story.extend(parts)
        elif el.tag == "ol" and "refs" in cls:
            story.extend(Paragraph(markup(li), S["ref"]) for li in el.findall("li"))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("UI", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(72, 36, "TopicLLM · software paper · pilot release 0.7.0 · 23 November 2026")
        canvas.drawRightString(540, 36, str(document.page))
        canvas.restoreState()

    SimpleDocTemplate(str(OUT), pagesize=(612, 792), leftMargin=72, rightMargin=72, topMargin=60, bottomMargin=60,
                      title=header.find("h1").text_content(), author="Jacob E. Thomas",
                      subject="TopicLLM software paper").build(story, onFirstPage=footer, onLaterPages=footer)
    QA.mkdir(parents=True, exist_ok=True)
    for old in QA.glob("page-*.png"):
        old.unlink()
    pdf = pdfium.PdfDocument(str(OUT))
    for i in range(len(pdf)):
        pdf[i].render(scale=1.4).to_pil().save(QA / f"page-{i + 1}.png")
    print(f"Wrote {OUT.relative_to(REPO)} ({len(pdf)} pages); QA renders in {QA.relative_to(REPO)}")


if __name__ == "__main__":
    main()
