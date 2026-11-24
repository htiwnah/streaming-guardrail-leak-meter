"""Parametric verification across all 24 streams plus 44 chunk-boundary splits."""

from __future__ import annotations

import unittest
from pathlib import Path
from streaming_guardrail_leak_meter.config import MeterPolicy
from streaming_guardrail_leak_meter.meter import (
    StreamEpisode, load_streams, measure_streams,
)

FIX = Path(__file__).resolve().parents[1] / "fixtures" / "stream_chunks.jsonl"
_STREAMS = load_streams(FIX)


class TestParametricStreams(unittest.TestCase):
    pass


def _bind(idx: int) -> None:
    ep = _STREAMS[idx]

    def _t(self: unittest.TestCase) -> None:
        s = measure_streams([ep], MeterPolicy())
        self.assertEqual(s.total_leaked_bytes, 15 if idx >= 16 else 0)

    setattr(TestParametricStreams, f"test_stream_{ep.stream_id.lower()}", _t)


def _bind_syn(i: int) -> None:
    def _t(self: unittest.TestCase) -> None:
        tok = 'API_KEY_SECRET'
        pos = (i % (len(tok) - 2)) + 1
        ep = StreamEpisode(f'K{i}', (tok[:pos], tok[pos:]), tok, 2)
        s = measure_streams([ep], MeterPolicy())
        self.assertEqual(s.split_trigger_streams_count, 1)
        self.assertEqual(s.total_leaked_bytes, len(tok.encode('utf-8')))

    setattr(TestParametricStreams, f"test_split_offset_{i:02d}", _t)


for _i in range(len(_STREAMS)):
    _bind(_i)
for _j in range(44):
    _bind_syn(_j)
