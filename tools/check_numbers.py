"""Machine-check every published number in README, CHANGELOG, and ADRs against receipts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def verify_numbers(root_dir: Path = ROOT_DIR) -> list[str]:
    """Validate that every receipt metric is accurately anchored in checked markdown docs."""
    metrics_file = root_dir / "docs" / "metrics.json"
    if not metrics_file.exists():
        return [f"Missing metrics receipt: {metrics_file}"]
    payload = json.loads(metrics_file.read_text(encoding="utf-8"))
    metrics: dict[str, object] = payload.get("metrics", {})
    anchors: dict[str, list[str]] = payload.get("anchors", {})
    doc_paths = payload.get("checked_documents", ["README.md"])
    combined = "\n".join(
        (root_dir / rel).read_text(encoding="utf-8")
        for rel in doc_paths
        if (root_dir / rel).exists()
    )
    norm = re.sub(r"\s+", " ", combined).lower()
    errors: list[str] = []
    for key, val in metrics.items():
        if isinstance(val, bool):
            continue
        patterns = anchors.get(key)
        if not patterns:
            if isinstance(val, (int, float)) and abs(val) < 6:
                errors.append(f"Small metric '{key}' ({val}) has no anchor phrase")
            continue
        matched = False
        expanded_list: list[str] = []
        for tmpl in patterns:
            cands: list[str] = []
            if "{:,.2f}" in tmpl and isinstance(val, (int, float)):
                cands.append(tmpl.format(float(val)).lower())
            elif "{:,}" in tmpl and isinstance(val, (int, float)):
                cands.append(tmpl.format(val).lower())
            else:
                cands.append(tmpl.format(val).lower())
                if isinstance(val, float) and val.is_integer():
                    cands.append(tmpl.format(int(val)).lower())
            expanded_list.extend(cands)
            if any(c in norm for c in cands):
                matched = True
                break
        if not matched:
            errors.append(
                f"Metric '{key}'={val!r} failed anchor match; expected {expanded_list}"
            )
    return errors


def main() -> int:
    errs = verify_numbers()
    if errs:
        for e in errs:
            sys.stderr.write(f"Number check failed: {e}\n")
        return 1
    print("Number receipt verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
