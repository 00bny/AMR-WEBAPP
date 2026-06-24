"""
Merge & clean monthly kW Excel reports - adapted from merge.py (v2).

The cleaning logic (FORMAT A/B/C detection, datetime parsing, footer
stripping, RATE A/B/C dedup) is copied verbatim from the original script -
that part is hard-won and file-format-specific, so it's untouched. Only the
outer "merge_files" entrypoint changed: instead of globbing a folder by
pattern, it takes an explicit ordered list of xlsx paths (the job's own
converted files), so jobs never accidentally merge another job's files.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

log = logging.getLogger("amr.merge")

DATETIME_PATTERN = re.compile(r"\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}[.:]?\d{2}")

THAI_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}
DAY_NAMES = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
    4: "Friday", 5: "Saturday", 6: "Sunday",
}

FOOTER_KEYWORDS = ("กิโลวัตต์ต่ำสุด", "กิโลวัตต์เฉลี่ย", "กิโลวัตต์สูงสุด", "***", "พิมพ์โดย")


# -----------------------------------------------------------------------
# Utility helpers (unchanged from merge.py)
# -----------------------------------------------------------------------

def is_datetime_like(val) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    return bool(DATETIME_PATTERN.match(str(val).strip()))


def is_footer_row(val) -> bool:
    s = str(val).strip()
    return any(kw in s for kw in FOOTER_KEYWORDS)


def parse_datetime(val):
    s = str(val).strip()
    s = re.sub(r"(\d{2})\.(\d{2})$", r"\1:\2", s)
    parts = s.split()
    if len(parts) < 2:
        return None
    date_part, time_part = parts[0], parts[1]
    try:
        d, m, y = date_part.split("/")
    except ValueError:
        return None
    y_int = int(y)
    if y_int > 2500:
        y_int -= 543
    if time_part == "24:00":
        time_part = "00:00"
    try:
        return pd.Timestamp(f"{y_int:04d}-{int(m):02d}-{int(d):02d} {time_part}")
    except Exception:
        return None


def time_group(t: pd.Timestamp) -> str:
    h = t.hour
    return f"{h:02d}:00-{h:02d}:59"


def _add_derived_cols(df: pd.DataFrame, time_col: str) -> pd.DataFrame:
    df["_dt"] = df[time_col].apply(parse_datetime)
    df["Date"] = df["_dt"].dt.strftime("%d/%m/%Y")
    df["Time"] = df["_dt"].dt.strftime("%H:%M")
    df["DateTime"] = df["Date"] + " " + df["Time"]
    df["Month"] = df["_dt"].dt.month.map(THAI_MONTHS)
    df["Days"] = df["_dt"].dt.dayofweek.map(DAY_NAMES)
    df["TimeGroup"] = df["_dt"].apply(lambda t: time_group(t) if pd.notna(t) else None)
    df.drop(columns=["_dt"], inplace=True)
    return df


def _has_rate_header(row_vals) -> bool:
    return any(re.search(r"RATE\s*[ABC]", str(v).strip(), re.I)
               for v in row_vals if not (isinstance(v, float) and pd.isna(v)))


def _find_data_start(raw: pd.DataFrame):
    for i in range(len(raw)):
        if is_datetime_like(raw.iloc[i, 0]):
            return i
    return None


def _find_last_data_row(raw: pd.DataFrame, data_start: int) -> int:
    last = data_start
    for i in range(data_start, len(raw)):
        cell = raw.iloc[i, 0]
        if is_footer_row(cell):
            break
        if is_datetime_like(cell):
            last = i
    return last


# -----------------------------------------------------------------------
# FORMAT A (unchanged from merge.py)
# -----------------------------------------------------------------------

def _find_weila_header_row(df: pd.DataFrame):
    for i, row in df.iterrows():
        for val in row:
            if isinstance(val, str) and val.strip().lower() in ("เวลา", "time"):
                return i
    return None


def clean_file_format_a(filepath: str, raw: pd.DataFrame) -> pd.DataFrame:
    header_row = _find_weila_header_row(raw)
    last_data_row = _find_last_data_row(raw, header_row + 1)

    sliced = raw.iloc[header_row: last_data_row + 1].copy()
    sliced.columns = sliced.iloc[0]
    sliced = sliced.iloc[1:].reset_index(drop=True)
    sliced = sliced.dropna(axis=1, how="all")

    cols, seen = [], {}
    for c in sliced.columns:
        name = str(c).strip() if not (isinstance(c, float) and pd.isna(c)) else "Unnamed"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        cols.append(name)
    sliced.columns = cols

    rate_cols = [c for c in sliced.columns if re.search(r"rate\s*[abc]", c, re.I)]
    rate_a = next((c for c in rate_cols if re.search(r"rate\s*a", c, re.I)), None)
    rate_b = next((c for c in rate_cols if re.search(r"rate\s*b", c, re.I)), None)
    rate_c = next((c for c in rate_cols if re.search(r"rate\s*c", c, re.I)), None)

    def pick_kw(row):
        for col in [rate_a, rate_b, rate_c]:
            if col and pd.notna(row.get(col)):
                return row[col]
        return None

    sliced["kW"] = sliced.apply(pick_kw, axis=1)

    time_col = next((c for c in sliced.columns if c.strip().lower() == "เวลา"), sliced.columns[0])
    sliced = _add_derived_cols(sliced, time_col)

    rename_map = {}
    if rate_a: rename_map[rate_a] = "RATE A"
    if rate_b: rename_map[rate_b] = "RATE B"
    if rate_c: rename_map[rate_c] = "RATE C"
    sliced = sliced.rename(columns=rename_map)
    sliced = sliced.rename(columns={time_col: "เวลา"})

    final_cols = ["เวลา", "Date", "Time", "DateTime", "Month", "Days", "TimeGroup",
                  "kW", "RATE A", "RATE B", "RATE C"]
    return sliced[[c for c in final_cols if c in sliced.columns]].copy()


# -----------------------------------------------------------------------
# FORMAT B/C (unchanged from merge.py)
# -----------------------------------------------------------------------

def clean_file_format_bc(filepath: str, raw: pd.DataFrame) -> pd.DataFrame:
    data_start = _find_data_start(raw)
    if data_start is None:
        raise ValueError("FORMAT B/C: ไม่พบแถวข้อมูล datetime")

    last_data = _find_last_data_row(raw, data_start)
    header_row_idx = data_start - 1
    header_vals = list(raw.iloc[header_row_idx]) if header_row_idx >= 0 else []

    data = raw.iloc[data_start: last_data + 1].copy().reset_index(drop=True)

    col_names, seen_rates, keep_cols = [], set(), []
    for ci, hval in enumerate(header_vals):
        hstr = str(hval).strip() if not (isinstance(hval, float) and pd.isna(hval)) else ""
        m = re.match(r"(?i)RATE\s*([ABC])", hstr)
        if m:
            rate_key = f"RATE {m.group(1).upper()}"
            if rate_key not in seen_rates:
                seen_rates.add(rate_key)
                col_names.append(rate_key)
                keep_cols.append(ci)
        else:
            col_names.append(hstr if hstr else f"col_{ci}")
            keep_cols.append(ci)

    if len(keep_cols) < data.shape[1]:
        keep_cols = list(range(data.shape[1]))
        col_names = [f"col_{i}" for i in range(data.shape[1])]

    data = data.iloc[:, keep_cols].copy()
    data.columns = col_names

    first_col = data.columns[0]
    data.rename(columns={first_col: "เวลา"}, inplace=True)

    rate_cols_present = [c for c in ["RATE A", "RATE B", "RATE C"] if c in data.columns]

    def pick_kw(row):
        for rc in rate_cols_present:
            if pd.notna(row.get(rc)):
                return row[rc]
        return None

    data["kW"] = data.apply(pick_kw, axis=1)
    data = _add_derived_cols(data, "เวลา")

    final_cols = ["เวลา", "Date", "Time", "DateTime", "Month", "Days", "TimeGroup",
                  "kW", "RATE A", "RATE B", "RATE C"]
    return data[[c for c in final_cols if c in data.columns]].copy()


# -----------------------------------------------------------------------
# Dispatcher (unchanged from merge.py)
# -----------------------------------------------------------------------

def clean_file(filepath: str) -> pd.DataFrame:
    xl = pd.ExcelFile(filepath)
    sheet_names = xl.sheet_names

    if len(sheet_names) >= 2:
        raw2 = pd.read_excel(filepath, header=None, sheet_name=1)
        ds = _find_data_start(raw2)
        if ds is not None and ds > 0 and _has_rate_header(raw2.iloc[ds - 1]):
            df = clean_file_format_bc(filepath, raw2)
            df["source_file"] = Path(filepath).name
            return df

    raw0 = pd.read_excel(filepath, header=None, sheet_name=0)

    if _find_weila_header_row(raw0) is not None:
        df = clean_file_format_a(filepath, raw0)
        df["source_file"] = Path(filepath).name
        return df

    ds = _find_data_start(raw0)
    if ds is not None and ds > 0 and _has_rate_header(raw0.iloc[ds - 1]):
        df = clean_file_format_bc(filepath, raw0)
        df["source_file"] = Path(filepath).name
        return df

    raise ValueError("ไม่สามารถระบุรูปแบบไฟล์ได้ (ไม่พบ header เวลา/RATE ก่อนแถว datetime)")


# -----------------------------------------------------------------------
# Merge - changed to take an explicit file list instead of glob pattern
# -----------------------------------------------------------------------

def merge_files(xlsx_paths: list[str], output_path: str) -> dict:
    """
    xlsx_paths: ordered list of this job's own converted .xlsx files.
    Returns a summary dict: {merged: bool, rows: int, files_ok: int,
    files_failed: int, errors: [{file, error}]}.
    """
    frames = []
    errors = []
    for fp in xlsx_paths:
        try:
            df = clean_file(fp)
            frames.append(df)
        except Exception as e:
            log.warning("failed to clean %s: %s", fp, e)
            errors.append({"file": Path(fp).name, "error": str(e)})

    if not frames:
        return {"merged": False, "rows": 0, "files_ok": 0,
                "files_failed": len(errors), "errors": errors}

    combined = pd.concat(frames, ignore_index=True)
    combined.to_excel(output_path, index=False)
    log.info("merged %d rows from %d files -> %s", len(combined), len(frames), output_path)

    return {
        "merged": True,
        "rows": len(combined),
        "files_ok": len(frames),
        "files_failed": len(errors),
        "errors": errors,
    }
