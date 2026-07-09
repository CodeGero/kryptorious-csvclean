"""CSVClean — CSV analysis and cleaning engine."""

import csv
import io
import os
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


def analyze_csv(path: str) -> Dict[str, Any]:
    """Analyze a CSV file and return diagnostic info.

    Detects: encoding, delimiter, quote char, header issues,
    empty rows, inconsistent column counts, type patterns, duplicates.
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {path}")

    size = filepath.stat().st_size
    raw = filepath.read_bytes()

    # Detect encoding
    encoding = _detect_encoding(raw)

    # Read with detected encoding
    text = raw.decode(encoding, errors="replace")
    lines = text.splitlines()

    if not lines:
        return {"error": "File is empty", "rows": 0, "columns": 0}

    # Detect delimiter
    delimiter = _detect_delimiter(lines)

    # Parse with csv module
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)

    if not rows:
        return {"error": "No data rows found", "rows": 0, "columns": 0}

    header = rows[0]
    data_rows = rows[1:]

    # Build result
    result = {
        "path": str(filepath),
        "size_bytes": size,
        "size_human": _format_size(size),
        "encoding": encoding,
        "delimiter": delimiter if delimiter != "," else "comma",
        "total_rows": len(data_rows),
        "total_columns": len(header),
        "headers": header,
        "issues": [],
    }

    # Check for empty headers
    empty_headers = [i for i, h in enumerate(header) if not h.strip()]
    if empty_headers:
        result["issues"].append({
            "severity": "error",
            "message": f"Empty header at column(s): {', '.join(str(i+1) for i in empty_headers)}"
        })

    # Check for duplicate headers
    seen = set()
    dupes = []
    for h in header:
        clean = h.strip().lower()
        if clean in seen:
            dupes.append(h)
        seen.add(clean)
    if dupes:
        result["issues"].append({
            "severity": "warning",
            "message": f"Duplicate headers: {', '.join(dupes)}"
        })

    # Check rows
    empty_rows = 0
    short_rows = 0
    long_rows = 0
    type_patterns = {i: Counter() for i in range(len(header))}

    for i, row in enumerate(data_rows, start=2):
        # Empty row
        if all(not cell.strip() for cell in row):
            empty_rows += 1
            continue

        # Column count mismatch
        if len(row) < len(header):
            short_rows += 1
        elif len(row) > len(header):
            long_rows += 1

        # Type inference per column
        for j, cell in enumerate(row):
            if j >= len(header):
                continue
            val = cell.strip()
            if not val:
                type_patterns[j]["empty"] += 1
            elif val.replace(".", "").replace("-", "").isdigit():
                type_patterns[j]["int" if "." not in val and "-" not in val else "float"] += 1
            elif val.lower() in ("true", "false", "yes", "no"):
                type_patterns[j]["bool"] += 1
            else:
                type_patterns[j]["string"] += 1

    result["empty_rows"] = empty_rows
    result["column_count_issues"] = short_rows + long_rows

    if empty_rows:
        result["issues"].append({
            "severity": "warning",
            "message": f"{empty_rows} empty row(s)"
        })
    if short_rows:
        result["issues"].append({
            "severity": "error",
            "message": f"{short_rows} row(s) with fewer columns than header"
        })
    if long_rows:
        result["issues"].append({
            "severity": "warning",
            "message": f"{long_rows} row(s) with more columns than header"
        })

    # Infer types
    result["column_types"] = {}
    for j, counter in type_patterns.items():
        if j < len(header):
            col_name = header[j].strip() or f"column_{j}"
            dominant = counter.most_common(1)[0][0] if counter else "empty"
            result["column_types"][col_name] = {
                "dominant_type": dominant,
                "distribution": dict(counter.most_common()),
                "empty_count": counter.get("empty", 0),
                "empty_pct": round(counter.get("empty", 0) / max(len(data_rows), 1) * 100, 1),
            }

    # Duplicate detection
    seen_rows = set()
    duplicate_count = 0
    for row in data_rows:
        row_key = tuple(cell.strip() for cell in row)
        if row_key in seen_rows:
            duplicate_count += 1
        seen_rows.add(row_key)

    result["duplicate_rows"] = duplicate_count
    if duplicate_count:
        result["issues"].append({
            "severity": "warning",
            "message": f"{duplicate_count} duplicate row(s)"
        })

    # Health score
    max_score = 100
    penalties = 0
    for issue in result["issues"]:
        if issue["severity"] == "error":
            penalties += 15
        else:
            penalties += 5
    penalties += duplicate_count * 2
    result["health_score"] = max(0, max_score - penalties)

    return result


def clean_csv(path: str, output: str, fix_encoding: bool = True,
              remove_empty: bool = True, normalize_delimiter: bool = True) -> Dict:
    """Clean a CSV file and write the result to OUTPUT.

    Real, free operation: decodes with detected encoding, optionally
    drops fully-empty rows and normalizes the delimiter to comma.
    Returns a summary of what was changed.
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {path}")

    raw = filepath.read_bytes()
    encoding = _detect_encoding(raw)
    text = raw.decode(encoding, errors="replace")
    lines = text.splitlines()

    if not lines:
        return {"source": path, "output": output, "removed_empty": 0,
                "normalized_delimiter": False, "wrote": False}

    delimiter = _detect_delimiter(lines)
    target_delim = "," if normalize_delimiter else (delimiter or ",")
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)

    header = rows[0] if rows else []
    data_rows = rows[1:]

    seen = set()
    kept = []
    removed_empty = 0
    removed_dupes = 0
    for row in data_rows:
        if all(not cell.strip() for cell in row):
            removed_empty += 1
            continue
        key = tuple(cell.strip() for cell in row)
        if key in seen:
            removed_dupes += 1
            continue
        seen.add(key)
        kept.append(row)

    out_rows = [header] + kept if header else kept
    with open(output, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter=target_delim)
        writer.writerows(out_rows)

    return {
        "source": path,
        "output": output,
        "removed_empty": removed_empty,
        "removed_duplicates": removed_dupes,
        "normalized_delimiter": bool(normalize_delimiter and delimiter not in (",", "")),
        "encoding_used": encoding,
        "wrote": True,
    }


def dedupe_csv(path: str, output: str | None = None) -> Dict:
    """Remove duplicate data rows from a CSV, writing to OUTPUT (or stdout summary)."""
    filepath = Path(path)
    raw = filepath.read_bytes()
    encoding = _detect_encoding(raw)
    text = raw.decode(encoding, errors="replace")
    lines = text.splitlines()
    if not lines:
        return {"source": path, "removed": 0, "wrote": False}
    delimiter = _detect_delimiter(lines)
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    header = rows[0] if rows else []
    data_rows = rows[1:]
    seen = set()
    kept = []
    removed = 0
    for row in data_rows:
        key = tuple(cell.strip() for cell in row)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        kept.append(row)
    if output:
        with open(output, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh, delimiter=delimiter).writerows([header] + kept if header else kept)
        return {"source": path, "output": output, "removed": removed, "wrote": True}
    return {"source": path, "removed": removed, "wrote": False}


def _detect_encoding(raw: bytes) -> str:
    """Detect file encoding from BOM or content."""
    if raw.startswith(b"\xff\xfe"):
        return "utf-16-le"
    if raw.startswith(b"\xfe\xff"):
        return "utf-16-be"
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        try:
            raw.decode("latin-1")
            return "latin-1"
        except UnicodeDecodeError:
            return "utf-8"


def _detect_delimiter(lines: List[str]) -> str:
    """Detect CSV delimiter from content."""
    if not lines:
        return ","

    # Check first 5 non-empty lines
    sample = [l for l in lines[:20] if l.strip()][:5]
    if not sample:
        return ","

    candidates = [",", "\t", ";", "|"]
    header_line = sample[0]

    # Count occurrences
    counts = {}
    for delim in candidates:
        counts[delim] = header_line.count(delim)

    # Find the delimiter that appears consistently across lines
    best_delim = ","
    best_score = 0

    for delim in candidates:
        line_counts = [line.count(delim) for line in sample]
        if len(set(line_counts)) <= 1 and line_counts[0] > 0:
            # Consistent count across lines
            score = line_counts[0] * 10 + (5 if delim != "," else 0)
            if score > best_score:
                best_score = score
                best_delim = delim
        elif line_counts[0] > counts.get(best_delim, 0):
            best_delim = delim

    return best_delim


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.2f} GB"
