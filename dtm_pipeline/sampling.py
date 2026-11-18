"""Declared temporal views of one corpus; source bytes remain unchanged."""
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

CAMPAIGN = ["2015-06-16", "2016-11-08"]
PRESIDENCY = ["2017-01-20", "2021-01-08"]


def parse_window(window):
    if window is None:
        return None
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("A date window must contain an inclusive start and end date.")
    try:
        start, end = [date.fromisoformat(value) for value in window]
    except (TypeError, ValueError) as exc:
        raise ValueError("Window dates must be ISO YYYY-MM-DD.") from exc
    if start > end:
        raise ValueError("Window start must not follow its end.")
    return start, end


def validate_design(cfg):
    discovery = parse_window(cfg.discovery_window)
    target = parse_window(cfg.target_window)
    if cfg.require_disjoint_windows:
        if discovery is None or target is None:
            raise ValueError("The transfer design requires discovery and target windows.")
        if max(discovery[0], target[0]) <= min(discovery[1], target[1]):
            raise ValueError("Discovery and target windows overlap: target leakage is not allowed.")
        if discovery[1] >= target[0]:
            raise ValueError("Discovery must precede the target period.")


def read_selected(cfg, role):
    """Read strings, validate all source dates, and select an inclusive window.

    Never silently drop invalid dates, duplicate IDs or blank text. The caller
    decides how to handle genuinely empty modeled documents after selection.
    """
    if role not in ("discovery", "target"):
        raise ValueError("Unknown sampling role.")
    validate_design(cfg)
    path = Path((cfg.discovery_input_csv or cfg.input_csv) if role == "discovery" else cfg.input_csv)
    window = parse_window(getattr(cfg, f"{role}_window"))
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "tweet" not in reader.fieldnames:
            raise ValueError(f"{path} needs a tweet column.")
        rows = list(reader)
    if not rows:
        raise ValueError("The source corpus is empty.")
    if "post_id" in rows[0]:
        ids = [row["post_id"] for row in rows]
        if any(not value or not value.strip() for value in ids) or len(set(ids)) != len(ids):
            raise ValueError("Source post_id values must be nonempty and unique.")
    else:
        # Positional IDs are stable only while the exact source bytes/order stay fixed.
        for i, row in enumerate(rows, 1):
            row["post_id"] = f"source-row-{i:09d}"
    selected = []
    for row in rows:
        if window:
            try:
                observed = date.fromisoformat(row.get("date", ""))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Missing or invalid ISO date for post {row['post_id']}.") from exc
            if not window[0] <= observed <= window[1]:
                continue
        selected.append(row)
    if not selected:
        raise ValueError(f"No records fall in the {role} window.")
    ids = [row["post_id"] for row in selected]
    report = {
        "role": role,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "window_inclusive": [d.isoformat() for d in window] if window else None,
        "source_records": len(rows), "selected_records": len(selected),
        "outside_window_records": len(rows) - len(selected),
        "ordered_selected_ids_sha256": hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest(),
    }
    return selected, report
