"""Rendering of Markdown meeting notes into a styled PDF document."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Line
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

DOCUMENT_TITLE = "Meeting Notes"
RULE_WIDTH = 6.5 * inch

_BULLET_PREFIXES = ("- ", "* ", "+ ")
_NUMBERED_ITEM = re.compile(r"^\d+\.")
_THEMATIC_BREAK = re.compile(r"^([-*_])(?:\s*\1){2,}$")
_LINK = re.compile(r"\[(.*?)\]\((.*?)\)")
_EMPHASIS_TOKENS = ("*", "~~", "`")
_EMPHASIS_RULES = (
    (re.compile(r"\*\*(.*?)\*\*"), r"<b>\1</b>"),
    (re.compile(r"\*(.*?)\*|_(.*?)_"), r"<i>\1\2</i>"),
    (re.compile(r"~~(.*?)~~"), r"<strike>\1</strike>"),
    (re.compile(r"```(.*?)```"), r'<font face="Courier">\1</font>'),
    (re.compile(r"`(.*?)`"), r'<font face="Courier">\1</font>'),
)


@dataclass(frozen=True)
class _Styles:
    title: ParagraphStyle
    heading1: ParagraphStyle
    heading2: ParagraphStyle
    heading3: ParagraphStyle
    bullet: ParagraphStyle
    body: ParagraphStyle


def _build_styles() -> _Styles:
    base = getSampleStyleSheet()
    return _Styles(
        title=ParagraphStyle(
            "CustomTitle", parent=base["Title"], fontSize=24, spaceBefore=30, spaceAfter=30,
            alignment=TA_CENTER, textColor=colors.darkblue,
        ),
        heading1=ParagraphStyle(
            "CustomHeading1", parent=base["Heading1"], fontSize=18, spaceBefore=24, spaceAfter=14,
            textColor=colors.darkgreen,
        ),
        heading2=ParagraphStyle(
            "CustomHeading2", parent=base["Heading2"], fontSize=15, spaceBefore=18, spaceAfter=12,
            textColor=colors.darkred,
        ),
        heading3=ParagraphStyle(
            "CustomHeading3", parent=base["Heading3"], fontSize=13, spaceBefore=14, spaceAfter=10,
            textColor=colors.darkblue,
        ),
        bullet=ParagraphStyle(
            "BulletPoints", parent=base["Normal"], leftIndent=30, spaceAfter=6, bulletIndent=15,
            bulletFontName="Helvetica-Bold", bulletFontSize=10,
        ),
        body=base["Normal"],
    )


def _escape(text: str) -> str:
    return escape(text, {'"': "&quot;"})


def _paragraph(markup: str, plain_text: str, style: ParagraphStyle) -> Paragraph:
    """Build a paragraph, falling back to plain text if the generated markup is invalid."""
    try:
        return Paragraph(markup, style)
    except ValueError:
        return Paragraph(_escape(plain_text), style)


def _is_list_item(line: str) -> bool:
    if _THEMATIC_BREAK.match(line):
        return False
    return line.startswith(_BULLET_PREFIXES) or bool(_NUMBERED_ITEM.match(line))


def _list_item(line: str, style: ParagraphStyle) -> Paragraph:
    if line.startswith(_BULLET_PREFIXES):
        return _paragraph("&bull; " + _escape(line[2:]), line, style)
    return _paragraph(_escape(line), line, style)


def _inline_markup(line: str) -> str:
    """Convert inline Markdown (emphasis, code, or links) into reportlab markup."""
    markup = _escape(line)
    if any(token in line for token in _EMPHASIS_TOKENS):
        for pattern, replacement in _EMPHASIS_RULES:
            markup = pattern.sub(replacement, markup)
        return markup
    if "](" in line:
        return _LINK.sub(r'<link href="\2">\1</link>', markup)
    return markup


def _horizontal_rule() -> Drawing:
    line = Line(0, 0, RULE_WIDTH, 0)
    line.strokeColor = colors.grey
    line.strokeWidth = 1
    drawing = Drawing(RULE_WIDTH, 1)
    drawing.add(line)
    return drawing


def _block(line: str, styles: _Styles) -> List[Flowable]:
    if line.startswith("#"):
        level = len(line) - len(line.lstrip("#"))
        style = {1: styles.heading1, 2: styles.heading2}.get(level, styles.heading3)
        text = line.lstrip("# ").strip()
        return [_paragraph(_escape(text), text, style)]
    if _THEMATIC_BREAK.match(line):
        return [Spacer(1, 0.2 * inch), _horizontal_rule(), Spacer(1, 0.2 * inch)]
    return [_paragraph(_inline_markup(line), line, styles.body)]


def build_story(markdown: str) -> List[Flowable]:
    """Convert Markdown text into the list of flowables that make up the PDF."""
    styles = _build_styles()
    story: List[Flowable] = [Paragraph(DOCUMENT_TITLE, styles.title), Spacer(1, 0.25 * inch)]
    lines = [line.strip() for line in markdown.split("\n")]

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line:
            story.append(Spacer(1, 0.15 * inch))
            index += 1
        elif _is_list_item(line):
            while index < len(lines) and _is_list_item(lines[index]):
                story.append(_list_item(lines[index], styles.bullet))
                index += 1
            story.append(Spacer(1, 0.1 * inch))
        else:
            story.extend(_block(line, styles))
            story.append(Spacer(1, 0.1 * inch))
            index += 1
    return story


def render_markdown_pdf(markdown: str, path: Path) -> None:
    """Write ``markdown`` to ``path`` as a letter-size PDF."""
    document = SimpleDocTemplate(
        str(path), pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18
    )
    document.build(build_story(markdown))
