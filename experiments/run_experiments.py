"""Deterministic streaming guardrail byte-leak experiments."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from streaming_guardrail_leak_meter.config import load_policy  # noqa: E402
from streaming_guardrail_leak_meter.meter import load_streams, measure_streams  # noqa: E402


def run_all_experiments(repo_root: Path | None = None) -> dict[str, object]:
    """Execute deterministic pre-cut byte-leak experiments."""
    root = repo_root or ROOT_DIR
    out_dir = root / "docs" / "experiments"
    out_dir.mkdir(parents=True, exist_ok=True)
    pol = load_policy(root / "policy" / "meter_policy.json")
    streams = load_streams(root / "fixtures" / "stream_chunks.jsonl")
    full = measure_streams(streams, pol)
    exp1 = {
        "total_streams": full.total_streams,
        "leaking_streams_count": full.leaking_streams_count,
        "split_trigger_streams_count": full.split_trigger_streams_count,
        "total_leaked_bytes": full.total_leaked_bytes,
        "worst_leaked_bytes": full.worst_leaked_bytes,
        "resolution_floor_pct": full.resolution_floor_pct,
    }
    (out_dir / "exp1_stream_leaks.json").write_text(
        json.dumps(exp1, indent=2) + "\n", encoding="utf-8"
    )
    return {"exp1": exp1}


def main() -> None:
    e1 = run_all_experiments()["exp1"]
    print(
        f"Exp1 | streams={e1['total_streams']} | leaking={e1['leaking_streams_count']} "
        f"| leaked_bytes={e1['total_leaked_bytes']}B | worst={e1['worst_leaked_bytes']}B"
    )


if __name__ == "__main__":
    main()
