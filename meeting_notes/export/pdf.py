"""Rendering of Markdown meeting notes into a styled PDF document with Qt."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, Iterator, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QBrush,
    QColor,
    QFont,
    QGuiApplication,
    QTextBlock,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFrame,
    QTextFormat,
    QTextFrameFormat,
    QTextLength,
    QTextTable,
)
from PyQt5.QtPrintSupport import QPrinter

DOCUMENT_TITLE = "Meeting Notes"
BODY_FONT = {"win32": "Segoe UI", "darwin": "Helvetica Neue"}.get(sys.platform, "DejaVu Sans")
BODY_POINT_SIZE = 10.5
TITLE_POINT_SIZE = 22
SUBTITLE_POINT_SIZE = 10
TITLE_COLOR = QColor("#00008b")
SUBTITLE_COLOR = QColor("#666666")
TABLE_BORDER_COLOR = QColor("#9fb8b3")
TABLE_HEADER_COLOR = QColor("#e3f4f0")
HEADING_STYLES: Dict[int, tuple] = {
    1: (18, QColor("#006400")),
    2: (15, QColor("#8b0000")),
    3: (13, QColor("#00008b")),
}

CODE_BACKGROUND_COLOR = QColor("#f3f6f5")

_TASK_ITEM = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)\[([ xX])\]\s+")
_STAR_BULLET = re.compile(r"^(\s*)[*+](\s+\S)")
_THEMATIC_BREAK = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_CODE_SPAN = re.compile(r"(`+)(.+?)\1")
_LINE_BREAK_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)
_UNCHECKED_BOX = "☐ "
_CHECKED_BOX = "☑ "
_HARD_LINE_BREAK = "  "


def build_document(markdown: str, subtitle: Optional[str] = None) -> QTextDocument:
    """Convert Markdown (GitHub dialect) into a styled document with a title block."""
    header = f"# {DOCUMENT_TITLE}\n\n" + (f"{_escape_markdown(subtitle)}\n\n" if subtitle else "")
    document = QTextDocument()
    body_font = QFont(BODY_FONT)
    body_font.setPointSizeF(BODY_POINT_SIZE)
    document.setDefaultFont(body_font)
    document.setMarkdown(header + _prepare(markdown), QTextDocument.MarkdownDialectGitHub)

    _style_headings(document)
    _style_code_blocks(document)
    _style_title(document, has_subtitle=bool(subtitle))
    _style_tables(document.rootFrame())
    return document


def render_markdown_pdf(markdown: str, path: Path, subtitle: Optional[str] = None) -> None:
    """
    Write ``markdown`` to ``path`` as a paginated PDF with page numbers.

    Raises:
        RuntimeError: If no Qt application object exists.
    """
    if QGuiApplication.instance() is None:
        raise RuntimeError("A QApplication must exist before rendering PDFs.")
    document = build_document(markdown, subtitle)
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setDocName(DOCUMENT_TITLE)
    printer.setOutputFileName(str(path))
    document.print_(printer)


def _prepare(markdown: str) -> str:
    """
    Normalise model output for Qt's Markdown importer.

    Outside code, angle brackets are escaped so text like ``<draft>`` is shown
    instead of being swallowed as HTML, ``*``/``+`` bullets become ``-`` (Qt only
    draws a bullet for ``-``), task-list markers become checkbox symbols, and
    single line breaks are kept (models often put one item per line without a
    list marker, which Markdown would otherwise merge into one paragraph).
    """
    lines = []
    in_fence = False
    for line in markdown.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            lines.append(line)
            continue
        if in_fence:
            lines.append(line)
            continue
        if not _THEMATIC_BREAK.match(line):
            line = _STAR_BULLET.sub(r"\1-\2", line)
        line = _TASK_ITEM.sub(
            lambda match: match.group(1)
            + (_CHECKED_BOX if match.group(2) in "xX" else _UNCHECKED_BOX),
            line,
        )
        line = _escape_outside_code(_LINE_BREAK_TAG.sub(" ", line))
        if line.strip() and not line.lstrip().startswith("|"):
            line = line.rstrip() + _HARD_LINE_BREAK
        lines.append(line)
    return "\n".join(lines)


def _escape_outside_code(line: str) -> str:
    parts = []
    position = 0
    for match in _CODE_SPAN.finditer(line):
        parts.append(_escape_angles(line[position:match.start()]))
        parts.append(match.group(0))
        position = match.end()
    parts.append(_escape_angles(line[position:]))
    return "".join(parts)


def _escape_angles(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _escape_markdown(text: str) -> str:
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|<>])", r"\\\1", text)


def _blocks(document: QTextDocument) -> Iterator[QTextBlock]:
    block = document.begin()
    while block.isValid():
        yield block
        block = block.next()


def _style_headings(document: QTextDocument) -> None:
    for block in _blocks(document):
        level = block.blockFormat().headingLevel()
        if not level:
            continue
        size, color = HEADING_STYLES.get(level, HEADING_STYLES[3])
        _format_block(block, size, color, True, top_margin=size * 0.9, bottom_margin=size * 0.4)


def _style_code_blocks(document: QTextDocument) -> None:
    for block in _blocks(document):
        if block.blockFormat().hasProperty(QTextFormat.BlockCodeFence):
            block_format = QTextBlockFormat()
            block_format.setBackground(QBrush(CODE_BACKGROUND_COLOR))
            QTextCursor(block).mergeBlockFormat(block_format)


def _style_title(document: QTextDocument, has_subtitle: bool) -> None:
    title = document.begin()
    _format_block(title, TITLE_POINT_SIZE, TITLE_COLOR, True, top_margin=0, bottom_margin=4)
    _center(title)
    if has_subtitle:
        subtitle = title.next()
        _format_block(
            subtitle, SUBTITLE_POINT_SIZE, SUBTITLE_COLOR, False, top_margin=0, bottom_margin=14
        )
        _center(subtitle)


def _format_block(
    block: QTextBlock,
    point_size: float,
    color: QColor,
    bold: bool,
    top_margin: float,
    bottom_margin: float,
) -> None:
    cursor = QTextCursor(block)
    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
    char_format = QTextCharFormat()
    char_format.setFontPointSize(point_size)
    char_format.setForeground(QBrush(color))
    char_format.setFontWeight(QFont.Bold if bold else QFont.Normal)
    cursor.mergeCharFormat(char_format)

    block_format = QTextBlockFormat()
    block_format.setTopMargin(top_margin)
    block_format.setBottomMargin(bottom_margin)
    cursor.mergeBlockFormat(block_format)


def _center(block: QTextBlock) -> None:
    block_format = QTextBlockFormat()
    block_format.setAlignment(Qt.AlignHCenter)
    QTextCursor(block).mergeBlockFormat(block_format)


def _style_tables(frame: QTextFrame) -> None:
    for child in frame.childFrames():
        if isinstance(child, QTextTable):
            table_format = child.format()
            table_format.setBorder(0.6)
            table_format.setBorderBrush(QBrush(TABLE_BORDER_COLOR))
            table_format.setBorderStyle(QTextFrameFormat.BorderStyle_Solid)
            table_format.setCellPadding(5)
            table_format.setCellSpacing(0)
            table_format.setWidth(QTextLength(QTextLength.PercentageLength, 100))
            child.setFormat(table_format)
            for column in range(child.columns()):
                cell = child.cellAt(0, column)
                cell_format = cell.format()
                cell_format.setBackground(QBrush(TABLE_HEADER_COLOR))
                cell.setFormat(cell_format)
        _style_tables(child)
