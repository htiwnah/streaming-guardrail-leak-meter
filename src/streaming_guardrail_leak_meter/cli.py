"""CLI for streaming-guardrail-leak-meter with explicit 0/1/2 exit codes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from streaming_guardrail_leak_meter.config import load_policy
from streaming_guardrail_leak_meter.meter import LeakSummary, load_streams, measure_streams


def render_table(s: LeakSummary, max_rows: int = 12) -> str:
    """Render scannable stream leak table."""
    hdr = f"{'StreamID':<9} {'Trig':<5} {'Split':<5} {'LeakedB':>8} {'Status'}"
    lines = [
        "Streaming Guardrail Leak Meter: Pre-Cut UTF-8 Bytes Across Chunk Splits",
        (
            f"Streams: {s.total_streams} | Leaking: {s.leaking_streams_count} | "
            f"Split Triggers: {s.split_trigger_streams_count} | "
            f"Total Leaked: {s.total_leaked_bytes}B | Worst: {s.worst_leaked_bytes}B"
        ),
        hdr,
        "-" * len(hdr),
    ]
    ordered = sorted(s.verdicts, key=lambda v: (-v.leaked_bytes, v.stream_id))
    for v in ordered[:max_rows]:
        lines.append(
            f"{v.stream_id:<9} {str(v.trigger_detected):<5} "
            f"{str(v.split_across_chunks):<5} {v.leaked_bytes:>8} {v.status}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Execute CLI and return 0 (pass), 1 (answered no), or 2 (error)."""
    p = argparse.ArgumentParser(prog="guardrail-meter")
    sub = p.add_subparsers(dest="cmd", required=True)
    mp = sub.add_parser("measure")
    mp.add_argument("--fixture", default="fixtures/stream_chunks.jsonl")
    mp.add_argument("--policy", default=None)
    mp.add_argument("--out", default="reports/leak_audit.json")
    mp.add_argument("--max-rows", type=int, default=12)
    mp.add_argument("--json-only", action="store_true")
    try:
        args = p.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    try:
        pol = load_policy(args.policy)
        s = measure_streams(load_streams(args.fixture), pol)
        op = Path(args.out)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(json.dumps(s.to_dict(), indent=2) + "\n", encoding="utf-8")
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError, TypeError) as exc:
        sys.stderr.write(f"Meter input error: {exc}\n")
        return 2
    if args.json_only:
        sys.stdout.write(json.dumps(s.to_dict(), indent=2) + "\n")
    else:
        sys.stdout.write(render_table(s, max_rows=args.max_rows) + "\n")
    return 0 if s.gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
