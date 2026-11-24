"""Deterministic streaming byte leak meter quantifying pre-cut UTF-8 exposure."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from streaming_guardrail_leak_meter.config import MeterPolicy


@dataclass(frozen=True)
class StreamEpisode:
    """Chunked SSE response with trigger token and cutoff chunk index."""

    stream_id: str
    chunks: tuple[str, ...]
    trigger_token: str
    cut_after_chunk_index: int


@dataclass(frozen=True)
class StreamVerdict:
    """Per-stream byte exposure and split-trigger classification."""

    stream_id: str
    trigger_detected: bool
    split_across_chunks: bool
    leaked_bytes: int
    status: str


@dataclass(frozen=True)
class LeakSummary:
    """Aggregated streaming leak report."""

    total_streams: int
    triggered_streams_count: int
    leaking_streams_count: int
    split_trigger_streams_count: int
    total_leaked_bytes: int
    worst_leaked_bytes: int
    resolution_floor_pct: float
    gate_passed: bool
    verdicts: list[StreamVerdict] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize summary to a plain JSON dictionary."""
        return {
            "total_streams": self.total_streams,
            "triggered_streams_count": self.triggered_streams_count,
            "leaking_streams_count": self.leaking_streams_count,
            "split_trigger_streams_count": self.split_trigger_streams_count,
            "total_leaked_bytes": self.total_leaked_bytes,
            "worst_leaked_bytes": self.worst_leaked_bytes,
            "resolution_floor_pct": self.resolution_floor_pct,
            "gate_passed": self.gate_passed,
            "verdicts": [
                {
                    "stream_id": v.stream_id,
                    "trigger_detected": v.trigger_detected,
                    "split_across_chunks": v.split_across_chunks,
                    "leaked_bytes": v.leaked_bytes,
                    "status": v.status,
                }
                for v in self.verdicts
            ],
        }


def load_streams(path: str | Path) -> list[StreamEpisode]:
    """Load JSONL chunked streams with explicit schema validation."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Stream fixture not found: {p}")
    out: list[StreamEpisode] = []
    for ln_no, raw_ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = raw_ln.strip()
        if not s:
            continue
        r = json.loads(s)
        if not isinstance(r, dict):
            raise ValueError(f"Line {ln_no} must be a JSON object")
        raw_c = r["chunks"]
        if not isinstance(raw_c, list) or not raw_c:
            raise ValueError(f"chunks must be non-empty list on line {ln_no}")
        chunks = tuple("" if c is None else str(c) for c in raw_c)
        trig = "" if r.get("trigger_token") is None else str(r["trigger_token"])
        out.append(StreamEpisode(str(r["stream_id"]), chunks, trig, int(r["cut_after_chunk_index"])))
    if not out:
        raise ValueError(f"No streams in {p}")
    return out


def measure_streams(streams: list[StreamEpisode], policy: MeterPolicy) -> LeakSummary:
    """Compute pre-cutoff leaked UTF-8 bytes and split-trigger detections."""
    if not streams:
        raise ValueError("Cannot measure empty stream list")
    policy.validate()
    trig_cnt = leak_cnt = split_cnt = tot_b = worst_b = 0
    verdicts: list[StreamVerdict] = []
    for ep in streams:
        joined = "".join(ep.chunks)
        has_t = bool(ep.trigger_token) and (ep.trigger_token in joined)
        split = bool(has_t and not any(ep.trigger_token in c for c in ep.chunks))
        cut = max(0, min(ep.cut_after_chunk_index, len(ep.chunks)))
        lb = len("".join(ep.chunks[:cut]).encode("utf-8")) if has_t else 0
        trig_cnt += int(has_t)
        split_cnt += int(split)
        if lb > 0:
            leak_cnt += 1
            st = "LEAKED_BEFORE_CUT"
        elif has_t:
            st = "CUT_BEFORE_EMIT"
        else:
            st = "CLEAN_STREAM"
        tot_b += lb
        worst_b = max(worst_b, lb)
        verdicts.append(StreamVerdict(ep.stream_id, has_t, split, lb, st))
    n = len(verdicts)
    return LeakSummary(
        total_streams=n,
        triggered_streams_count=trig_cnt,
        leaking_streams_count=leak_cnt,
        split_trigger_streams_count=split_cnt,
        total_leaked_bytes=tot_b,
        worst_leaked_bytes=worst_b,
        resolution_floor_pct=round((1.0 / n) * 100.0, 2),
        gate_passed=tot_b <= policy.max_allowed_leaked_bytes,
        verdicts=verdicts,
    )
