"""Explicit policy loader for streaming byte-leak ceilings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MeterPolicy:
    """Immutable leaked-byte ceiling policy."""

    policy_version: str = "1.0"
    max_allowed_leaked_bytes: int = 0
    fixture_path: str = "fixtures/stream_chunks.jsonl"

    def validate(self) -> None:
        """Reject negative leaked-byte budgets."""
        if self.max_allowed_leaked_bytes < 0:
            raise ValueError("max_allowed_leaked_bytes must be >= 0")


def load_policy(path: str | Path | None = None) -> MeterPolicy:
    """Load MeterPolicy from JSON or return validated defaults."""
    if path is None:
        cfg = MeterPolicy()
        cfg.validate()
        return cfg
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Policy not found: {p}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Policy must be a JSON object")
    cfg = MeterPolicy(**raw)
    cfg.validate()
    return cfg
