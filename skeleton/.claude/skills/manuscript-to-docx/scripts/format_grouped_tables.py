#!/usr/bin/env python3
"""Apply Word-only formatting to grouped parameter tables in a DOCX file.

A grouped table is one whose first column `mergecol.lua` has vertically merged: a
body cell in column 1 carries `w:vMerge`. The table is recognized by that structure,
not by its header text, so the step works on any manuscript. For each grouped table,
the merged group cells are centered vertically and every group after the first gets a
0.5 pt top border. A document without grouped tables is left untouched.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
ET.register_namespace("w", W_NS)


def get_or_add(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def set_vertical_center(cell: ET.Element) -> None:
    tc_pr = get_or_add(cell, f"{W}tcPr")
    valign = get_or_add(tc_pr, f"{W}vAlign")
    valign.set(f"{W}val", "center")


def set_top_border(cell: ET.Element) -> None:
    tc_pr = get_or_add(cell, f"{W}tcPr")
    borders = get_or_add(tc_pr, f"{W}tcBorders")
    top = get_or_add(borders, f"{W}top")
    top.set(f"{W}val", "single")
    top.set(f"{W}sz", "4")  # eighths of a point: 0.5 pt
    top.set(f"{W}space", "0")
    top.set(f"{W}color", "auto")


def format_grouped_table(table: ET.Element) -> bool:
    """Format one table if its first column is merged; return whether it was."""
    rows = table.findall(f"{W}tr")
    group_starts: list[int] = []
    grouped = False
    # Row 0 is the header row; mergecol.lua merges body rows only.
    for row_index, row in enumerate(rows[1:], start=1):
        cells = row.findall(f"{W}tc")
        if not cells:
            continue

        first_cell = cells[0]
        vmerge = first_cell.find(f"{W}tcPr/{W}vMerge")
        if vmerge is None:
            continue

        grouped = True
        set_vertical_center(first_cell)
        if vmerge.get(f"{W}val") == "restart":
            group_starts.append(row_index)

    for row_index in group_starts[1:]:
        for cell in rows[row_index].findall(f"{W}tc"):
            set_top_border(cell)

    return grouped


def process_docx(path: Path) -> int:
    with zipfile.ZipFile(path, "r") as source:
        root = ET.fromstring(source.read("word/document.xml"))
    matched = sum(format_grouped_table(table) for table in root.iter(f"{W}tbl"))
    if matched == 0:
        return 0

    fd, temporary_name = tempfile.mkstemp(
        prefix=f"{path.stem}-", suffix=".docx", dir=path.parent
    )
    os.close(fd)
    temporary_path = Path(temporary_name)
    try:
        updated_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(
            temporary_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as destination:
            for item in source.infolist():
                data = (
                    updated_xml
                    if item.filename == "word/document.xml"
                    else source.read(item.filename)
                )
                destination.writestr(item, data)

        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return matched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("docx", type=Path)
    args = parser.parse_args()
    path = args.docx.resolve()
    matched = process_docx(path)
    if matched:
        print(f"Formatted {matched} grouped parameter table(s): {path}")
    else:
        print(f"No grouped parameter tables (merged first column) to format: {path}")


if __name__ == "__main__":
    main()
