"""Extract clean financial tables from raw SEC filing HTML.

SEC filings lay tables out on a fine grid: one logical value is often split over several
cells ("$" | "201,183" | "" or "(7)" | "%"), values span columns via colspan, and empty
spacer cells separate columns. Docling's Markdown mirrors that grid, so tables are rebuilt
here from the HTML: each value becomes one token, and tokens are aligned into logical
columns by their grid position.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser

VOID_TAGS = {"br", "img", "hr", "meta", "link", "input", "col", "area", "base", "wbr"}
BLOCK_TAGS = {"div", "p", "table", "li", "h1", "h2", "h3", "h4", "h5", "h6"}

# An amount or percentage ("201,183", "$1.5", "(2)", "(7)%", "12.5 %"), a range of them
# ("0.1%-1.6%", "$0.62–0.68", "2.0% –5.4%"), or a dash placeholder ("—").
_AMOUNT = r"\(?\$?\(?-?[\d,]*\d(?:\.\d+)?\)?\s*%?\)?"
VALUE_RE = re.compile(rf"^{_AMOUNT}(?:\s*[–-]\s*{_AMOUNT})?$|^[—–-]+$")
YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")
UNITS_RE = re.compile(r"\bin (?:millions|thousands|billions)\b(?:, except [^)]*)?", re.IGNORECASE)
TITLE_MAX_LENGTH = 300
PROSE_CELL_LENGTH = 200


@dataclass
class _Node:
    tag: str
    attrs: dict[str, str]
    children: list[_Node | str] = field(default_factory=list)

    @property
    def hidden(self) -> bool:
        return "display:none" in self.attrs.get("style", "").replace(" ", "").lower()


class _TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("root", {})
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(tag, {key: value or "" for key, value in attrs})
        self._stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._stack[-1].children.append(_Node(tag, {key: value or "" for key, value in attrs}))

    def handle_endtag(self, tag: str) -> None:
        # Pop to the matching open tag; tolerates the occasional unclosed inline element.
        for depth in range(len(self._stack) - 1, 0, -1):
            if self._stack[depth].tag == tag:
                del self._stack[depth:]
                return

    def handle_data(self, data: str) -> None:
        self._stack[-1].children.append(data)


def _text(node: _Node) -> str:
    # Inline children are joined without spaces: filings split words across spans
    # ("B<span>USINESS</span>"). Block children get a space between them.
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        elif not child.hidden:
            text = _text(child)
            parts.append(f" {text} " if child.tag in BLOCK_TAGS or child.tag == "br" else text)
    return " ".join("".join(parts).split())


@dataclass
class _Token:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class ExtractedTable:
    table_index: int
    title: str | None
    units: str | None
    markdown: str
    table_data: dict
    source_html_hash: str


def _grid_tokens(rows: list[_Node]) -> list[list[_Token]]:
    """Place every cell on the table grid, honouring colspan and rowspan."""
    # Columns still covered by a rowspan cell from an earlier row: start -> (end, rows left).
    carried: dict[int, tuple[int, int]] = {}
    grid: list[list[_Token]] = []
    for row in rows:
        tokens: list[_Token] = []
        new_carried: dict[int, tuple[int, int]] = {}
        column = 0
        for cell in row.children:
            if isinstance(cell, str) or cell.tag not in ("td", "th"):
                continue
            while column in carried:
                column = carried[column][0]
            span = int(cell.attrs.get("colspan") or 1)
            rowspan = int(cell.attrs.get("rowspan") or 1)
            text = _text(cell)
            if text:
                tokens.append(_Token(column, column + span, text))
            if rowspan > 1:
                new_carried[column] = (column + span, rowspan - 1)
            column += span
        carried = {start: (end, left - 1) for start, (end, left) in carried.items() if left > 1} | new_carried
        grid.append(_merge_fragments(tokens))
    return grid


def _merge_fragments(tokens: list[_Token]) -> list[_Token]:
    merged: list[_Token] = []
    pending_prefix: _Token | None = None
    for token in tokens:
        if token.text in ("$", "(", "$("):
            pending_prefix = token
            continue
        if pending_prefix:
            token = _Token(pending_prefix.start, token.end, pending_prefix.text + token.text)
            pending_prefix = None
        if merged and token.text in ("%", ")", ")%", "%)"):
            previous = merged[-1]
            merged[-1] = _Token(previous.start, token.end, previous.text + token.text)
            continue
        merged.append(token)
    if pending_prefix:
        merged.append(pending_prefix)
    return _merge_ranges(merged)


def _same_kind(left: str, right: str) -> bool:
    return (left.endswith("%") and right.endswith("%")) or bool(YEAR_RE.match(left) and YEAR_RE.match(right))


def _merge_ranges(tokens: list[_Token]) -> list[_Token]:
    # "0.48%" | "–" | "0.63%" is one range value. An em dash ("—") stays separate: it is the
    # usual "nil" placeholder and can legitimately sit between two real values.
    merged: list[_Token] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if (
            merged
            and token.text in ("–", "-")
            and index + 1 < len(tokens)
            and _same_kind(merged[-1].text, tokens[index + 1].text)
        ):
            following = tokens[index + 1]
            merged[-1] = _Token(merged[-1].start, following.end, f"{merged[-1].text} – {following.text}")
            index += 2
            continue
        merged.append(token)
        index += 1
    return merged


def _is_value(text: str) -> bool:
    return bool(VALUE_RE.match(text))


def _overlap(token: _Token, start: int, end: int) -> int:
    return min(token.end, end) - max(token.start, start)


def _value_columns(data_rows: list[list[_Token]]) -> list[tuple[int, int]]:
    """Cluster the grid spans of every non-label cell in data rows into logical columns.

    Text cells count too, so a "Change" column holding "Up 53%" keeps its own column
    instead of being folded into the nearest amount column.
    """
    spans = sorted((token.start, token.end) for row in data_rows for token in row[1:])
    columns: list[list[int]] = []
    for start, end in spans:
        if columns and start < columns[-1][1]:
            columns[-1][1] = max(columns[-1][1], end)
        else:
            columns.append([start, end])
    return [(start, end) for start, end in columns]


def _column_for(token: _Token, columns: list[tuple[int, int]]) -> int:
    overlaps = [_overlap(token, start, end) for start, end in columns]
    best = max(range(len(columns)), key=lambda index: overlaps[index])
    if overlaps[best] > 0:
        return best
    return min(range(len(columns)), key=lambda index: abs(columns[index][0] - token.start))


def _is_data_row(tokens: list[_Token]) -> bool:
    # A row whose only numbers are years ("(In millions) | 2024 | 2023") is a header, not data.
    return (
        len(tokens) >= 2
        and not _is_value(tokens[0].text)
        and any(_is_value(t.text) and not YEAR_RE.match(t.text) for t in tokens[1:])
    )


def _escape(cell: str) -> str:
    return cell.replace("|", "\\|")


def _build_table(rows: list[list[_Token]]) -> tuple[list[str], list[dict]] | None:
    first_data = next((index for index, tokens in enumerate(rows) if _is_data_row(tokens)), None)
    if first_data is None:
        return None
    columns = _value_columns([tokens for tokens in rows[first_data:] if _is_data_row(tokens)])
    if not columns:
        return None
    label_end = columns[0][0]
    # Before the first data row, rows reaching into the value columns are headers ("2024 | 2023");
    # rows confined to the label column are section labels ("Operating expenses:") and belong to the body.
    header_rows = [tokens for tokens in rows[:first_data] if any(token.end > label_end for token in tokens)]
    body_rows = [tokens for tokens in rows[:first_data] if all(token.end <= label_end for token in tokens)]
    body_rows += rows[first_data:]

    headers = [""] * (len(columns) + 1)
    for tokens in header_rows:
        for token in tokens:
            if token.end <= label_end:
                headers[0] = f"{headers[0]} {token.text}".strip()
                continue
            # A group header ("Year Ended September") spanning several columns labels each of them.
            for index, (start, end) in enumerate(columns):
                if _overlap(token, start, end) > 0:
                    headers[index + 1] = f"{headers[index + 1]} {token.text}".strip()

    body: list[dict] = []
    for tokens in body_rows:
        label = ""
        values: list[str | None] = [None] * len(columns)
        for token in tokens:
            if token.end <= label_end or (not label and not _is_value(token.text) and token is tokens[0]):
                label = f"{label} {token.text}".strip()
                continue
            index = _column_for(token, columns)
            values[index] = token.text if values[index] is None else f"{values[index]} {token.text}"
        body.append({"label": label, "values": values})
    return headers, body


def _is_layout_table(rows: list[list[_Token]]) -> bool:
    # Filings also use tables to lay out prose (bullets, footnotes, audit matters) and the
    # exhibit index. Their text is already in the Markdown, and as tables they would only
    # yield half-parsed rows.
    texts = [token.text for tokens in rows for token in tokens]
    return any(len(text) > PROSE_CELL_LENGTH for text in texts) or any(
        text.lower().startswith("exhibit") for tokens in rows[:3] for text in (t.text for t in tokens)
    )


def _looks_like_financial_data(body: list[dict]) -> bool:
    # Tables of contents only hold small page numbers.
    values = [value for row in body for value in row["values"] if value and _is_value(value)]
    return any(re.search(r"[$%,]|\d\.\d", value) or len(value.strip("()")) >= 4 for value in values)


def _to_markdown(headers: list[str], body: list[dict]) -> str:
    lines = [
        "| " + " | ".join(_escape(header) for header in headers) + " |",
        "|" + "---|" * len(headers),
    ]
    for row in body:
        cells = [row["label"], *(value or "" for value in row["values"])]
        lines.append("| " + " | ".join(_escape(cell) for cell in cells) + " |")
    return "\n".join(lines)


def _collect_blocks(node: _Node, blocks: list[tuple[str, _Node | str]]) -> None:
    """Flatten the document into ordered ("text", str) and ("table", node) blocks."""
    for child in node.children:
        if isinstance(child, str) or child.hidden:
            continue
        if child.tag == "table":
            blocks.append(("table", child))
        elif child.tag in BLOCK_TAGS and not _contains_block(child):
            text = _text(child)
            if text:
                blocks.append(("text", text))
        else:
            _collect_blocks(child, blocks)


def _contains_block(node: _Node) -> bool:
    return any(
        isinstance(child, _Node) and (child.tag in BLOCK_TAGS or _contains_block(child)) for child in node.children
    )


def _rows(table: _Node) -> list[_Node]:
    found: list[_Node] = []
    for child in table.children:
        if isinstance(child, _Node):
            if child.tag == "tr":
                found.append(child)
            elif child.tag in ("thead", "tbody", "tfoot"):
                found.extend(_rows(child))
    return found


def extract_sec_tables(html: str) -> list[ExtractedTable]:
    parser = _TreeParser()
    parser.feed(html)
    parser.close()

    blocks: list[tuple[str, _Node | str]] = []
    _collect_blocks(parser.root, blocks)

    tables: list[ExtractedTable] = []
    last_text: str | None = None
    for kind, block in blocks:
        if kind == "text":
            last_text = block  # type: ignore[assignment]
            continue
        rows = [tokens for tokens in _grid_tokens(_rows(block)) if tokens]  # type: ignore[arg-type]
        if not rows or _is_layout_table(rows):
            continue
        built = _build_table(rows)
        if built is None or not _looks_like_financial_data(built[1]):
            continue
        headers, body = built
        title = last_text[:TITLE_MAX_LENGTH] if last_text else None
        units_match = UNITS_RE.search(" ".join(filter(None, [title, *headers])))
        units = units_match.group(0) if units_match else None
        raw_rows = [[token.text for token in tokens] for tokens in rows]
        tables.append(
            ExtractedTable(
                table_index=len(tables),
                title=title,
                units=units,
                markdown=_to_markdown(headers, body),
                table_data={"columns": headers, "rows": body},
                source_html_hash=hashlib.sha256(json.dumps(raw_rows).encode()).hexdigest(),
            )
        )
    return tables
