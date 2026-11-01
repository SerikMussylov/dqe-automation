"""Helper keywords: read the report table, read a partitioned Parquet dataset, compare."""

import time
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.by import By

ROW_TOLERANCE_PX = 6

# Parquet column name -> column name shown in the HTML table
COLUMN_NAMES = {
    "facility_type": "Facility Type",
    "visit_date": "Visit Date",
    "avg_time_spent": "Average Time Spent",
}
TYPE_COL, DATE_COL, AVG_COL = COLUMN_NAMES.values()


def path_to_file_uri(path):
    """Converts a local path (also with spaces / Windows backslashes) to a file:// URI."""
    return Path(path).expanduser().resolve().as_uri()


def _text(element):
    return (element.text or element.get_attribute("textContent") or "").strip()


def _normalize(df):
    """Same types and order on both sides so an exact comparison is meaningful."""
    df = df.copy()
    df[TYPE_COL] = df[TYPE_COL].astype(str).str.strip()
    df[DATE_COL] = pd.to_datetime(df[DATE_COL]).dt.strftime("%Y-%m-%d")
    df[AVG_COL] = pd.to_numeric(df[AVG_COL]).round(2)
    return df.sort_values([DATE_COL, TYPE_COL]).reset_index(drop=True)


def _flush(rows, current, width):
    if len(current) == width:  # skip partially rendered rows at the edges
        rows.append(tuple(current[i] for i in range(width)))


def _read_visible_rows(table):
    """Returns (headers, rows). Cells are paired by vertical position, not by DOM order."""
    columns = table.find_elements(By.CLASS_NAME, "y-column")
    if not columns:
        raise NoSuchElementException("No 'y-column' elements found in the table")

    headers, entries = [], []
    for index, column in enumerate(columns):
        header = _text(column.find_element(By.ID, "header"))
        headers.append(header)
        for cell in column.find_elements(By.CLASS_NAME, "cell-text"):
            text = _text(cell)
            if text == header:      # exclude the header cell
                continue
            rect = cell.rect
            entries.append((rect["y"] + rect["height"] / 2, index, text))

    entries.sort(key=lambda e: (e[0], e[1]))
    rows, current, row_y = [], {}, None
    for y, index, text in entries:
        if row_y is None or y - row_y > ROW_TOLERANCE_PX:   # a new visual row starts
            _flush(rows, current, len(columns))
            current, row_y = {}, y
        current[index] = text
    _flush(rows, current, len(columns))
    return headers, rows


def read_html_table(table, max_scrolls=40, max_idle_scrolls=3):
    """Reads the located table element into a DataFrame, scrolling to load all rows."""
    driver = table.parent  # the WebDriver that located the element
    headers, rows = _read_visible_rows(table)
    collected, seen, idle = list(rows), set(rows), 0

    for _ in range(max_scrolls):
        current = driver.find_element(By.CLASS_NAME, "table")  # DOM is redrawn on scroll
        ActionChains(driver).scroll_from_origin(ScrollOrigin.from_element(current), 0, 200).perform()
        time.sleep(0.3)
        _, rows = _read_visible_rows(driver.find_element(By.CLASS_NAME, "table"))
        new_rows = [r for r in rows if r not in seen]
        if new_rows:
            collected.extend(new_rows)
            seen.update(new_rows)
            idle = 0
        else:
            idle += 1
            if idle >= max_idle_scrolls:
                break

    df = pd.DataFrame(collected, columns=headers)
    missing = [c for c in COLUMN_NAMES.values() if c not in df.columns]
    if missing:
        raise AssertionError(f"HTML table lacks expected columns {missing}; found {list(df.columns)}")
    return _normalize(df)[list(COLUMN_NAMES.values())]


def _partition_before_cutoff(folder_name, cutoff):
    """True for a partition folder like 'partition_date=2026-08' older than the cutoff month."""
    if "=" not in folder_name:
        return False
    try:
        return pd.Period(folder_name.split("=", 1)[1], freq="M") < cutoff.to_period("M")
    except (ValueError, TypeError):
        return False


def read_parquet_dataset(folder, filter_date=None):
    """Reads a partitioned Parquet dataset; keeps rows with Visit Date >= filter_date (YYYY-MM-DD).

    Files are read one by one, so hive partition folders do not become extra columns.
    Whole partitions older than the filter month are skipped.
    """
    root = Path(folder)
    if not root.is_dir():
        raise FileNotFoundError(f"Parquet folder not found: {folder}")
    cutoff = pd.Timestamp(filter_date) if filter_date else None

    files = [f for f in sorted(root.rglob("*"))
             if f.is_file() and not f.name.startswith((".", "_"))
             and not (cutoff is not None and _partition_before_cutoff(f.parent.name, cutoff))]
    if not files:
        raise FileNotFoundError(f"No parquet files to read under {folder} (filter date: {filter_date})")

    df = pd.concat([pq.ParquetFile(f).read().to_pandas() for f in files], ignore_index=True)
    df = df.rename(columns=COLUMN_NAMES)
    if cutoff is not None:
        df = df[pd.to_datetime(df[DATE_COL]) >= cutoff]
    return _normalize(df)[list(COLUMN_NAMES.values())]


def compare_dataframes(html_df, parquet_df):
    """Exact comparison (row multiset). Returns a DataFrame of differences; empty means a match."""
    columns = list(parquet_df.columns)
    if list(html_df.columns) != columns:
        raise AssertionError(f"Column mismatch: HTML {list(html_df.columns)} vs Parquet {columns}")
    in_html = Counter(html_df[columns].itertuples(index=False, name=None))
    in_parquet = Counter(parquet_df[columns].itertuples(index=False, name=None))
    rows = []
    for row, count in (in_html - in_parquet).items():
        rows += [("only in HTML report", *row)] * count
    for row, count in (in_parquet - in_html).items():
        rows += [("only in Parquet", *row)] * count
    return pd.DataFrame(rows, columns=["Difference"] + columns)


def format_differences(diff, limit=50):
    if diff.empty:
        return "No differences"
    return f"{len(diff)} difference(s), first {min(limit, len(diff))}:\n" + diff.head(limit).to_string(index=False)