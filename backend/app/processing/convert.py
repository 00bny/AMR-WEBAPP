"""
Convert .xls files to .xlsx - adapted from convert_xls.py.

The original script looped over a hardcoded folder. Here we convert one
file at a time (called right after each month finishes downloading) so the
frontend can show "converting" progress immediately rather than waiting for
every month to download first.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger("amr.convert")


def convert_xls_to_xlsx(xls_path: str, xlsx_dir: Path) -> str:
    """Converts one .xls file to .xlsx, same table-extraction approach as
    the original convert_xls.py (pd.read_html, since these are HTML-based
    .xls exports from the AMR site, not real binary .xls files)."""
    xls_path = Path(xls_path)
    tables = pd.read_html(xls_path)

    output_path = xlsx_dir / (xls_path.stem + ".xlsx")
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for i, df in enumerate(tables):
            sheet_name = f"Sheet{i + 1}"
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    log.info("converted %s -> %s", xls_path.name, output_path.name)
    return str(output_path)
