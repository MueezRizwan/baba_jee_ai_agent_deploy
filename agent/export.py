"""Export the final report as a Microsoft Word document.

The report is authored as markdown, so this module walks that markdown and
rebuilds it with real Word constructs - styled headings, bullet and numbered
lists, and proper tables - rather than dumping the raw text into a paragraph.
"""

from __future__ import annotations

import io
import re
from datetime import datetime

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

BRAND = RGBColor(0x5B, 0x3F, 0xD6)
MUTED = RGBColor(0x64, 0x74, 0x8B)

_INLINE = re.compile(r"(\*\*.+?\*\*|`.+?`|_.+?_)")
_TABLE_DIVIDER = re.compile(r"^\|[\s:|-]+\|$")


def _add_runs(paragraph, text: str) -> None:
    """Render **bold**, `code` and _italic_ spans as real Word runs."""
    for piece in _INLINE.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            paragraph.add_run(piece[2:-2]).bold = True
        elif piece.startswith("`") and piece.endswith("`"):
            run = paragraph.add_run(piece[1:-1])
            run.font.name = "Consolas"
            run.font.color.rgb = BRAND
        elif piece.startswith("_") and piece.endswith("_") and len(piece) > 2:
            paragraph.add_run(piece[1:-1]).italic = True
        else:
            paragraph.add_run(piece)


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _add_table(document: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    width = max(len(row) for row in rows)
    table = document.add_table(rows=0, cols=width)
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for index, row in enumerate(rows):
        cells = table.add_row().cells
        for position in range(width):
            value = row[position] if position < len(row) else ""
            paragraph = cells[position].paragraphs[0]
            _add_runs(paragraph, value)
            for run in paragraph.runs:
                run.font.size = Pt(9)
                if index == 0:
                    run.bold = True
    document.add_paragraph()


def _configure(document: Document) -> None:
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)


def _cover(document: Document, agent_name: str, source_name: str | None) -> None:
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = title.add_run("Data analysis report")
    run.bold = True
    run.font.size = Pt(26)
    run.font.color.rgb = BRAND

    meta = document.add_paragraph()
    stamp = datetime.now().strftime("%d %B %Y, %H:%M")
    run = meta.add_run(f"Prepared by {agent_name}  ·  {source_name or 'unknown source'}  ·  {stamp}")
    run.font.size = Pt(9.5)
    run.font.color.rgb = MUTED


def markdown_to_docx(markdown: str, agent_name: str = "Baba_Jee", source_name: str | None = None) -> bytes:
    """Convert the report markdown into a .docx file and return its bytes."""
    document = Document()
    _configure(document)
    _cover(document, agent_name, source_name)

    table_buffer: list[list[str]] = []
    skip_first_heading = True

    def flush_table() -> None:
        nonlocal table_buffer
        if table_buffer:
            _add_table(document, table_buffer)
            table_buffer = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        # Table rows accumulate until a non-table line arrives.
        if line.startswith("|"):
            if not _TABLE_DIVIDER.match(line):
                table_buffer.append(_split_row(line))
            continue
        flush_table()

        if not line.strip():
            continue

        if line.startswith("---"):
            document.add_paragraph()
            continue

        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            text = line[level:].strip()
            if level == 1 and skip_first_heading:
                # The cover block already carries the document title.
                skip_first_heading = False
                continue
            heading = document.add_heading(level=min(level, 4))
            _add_runs(heading, text)
            for run in heading.runs:
                run.font.color.rgb = BRAND
            continue

        if line.lstrip().startswith(("- ", "* ")):
            paragraph = document.add_paragraph(style="List Bullet")
            _add_runs(paragraph, line.lstrip()[2:])
            continue

        numbered = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if numbered:
            paragraph = document.add_paragraph(style="List Number")
            _add_runs(paragraph, numbered.group(2))
            continue

        paragraph = document.add_paragraph()
        _add_runs(paragraph, line.strip())

    flush_table()

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
