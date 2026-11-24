"""Property, boundary, and CLI tests for streaming-guardrail-leak-meter."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from streaming_guardrail_leak_meter.cli import main as cli_main, render_table
from streaming_guardrail_leak_meter.config import MeterPolicy, load_policy
from streaming_guardrail_leak_meter.meter import StreamEpisode, load_streams, measure_streams

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures" / "stream_chunks.jsonl"
POL = ROOT / "policy" / "meter_policy.json"


class TestLeakMeterProperties(unittest.TestCase):
    def test_policies_validate_and_reject_invalid_values(self) -> None:
        MeterPolicy().validate()
        self.assertEqual(load_policy(POL).max_allowed_leaked_bytes, 0)
        self.assertEqual(load_policy(None).max_allowed_leaked_bytes, 0)
        with self.assertRaises(FileNotFoundError):
            load_policy(Path("/tmp/missing_mpol_999.json"))
        with self.assertRaises(ValueError):
            MeterPolicy(max_allowed_leaked_bytes=-1).validate()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "p.json"
            p.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_policy(p)

    def test_loader_boundary_checks_and_null_chunk_war_story(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_streams(Path("/tmp/missing_stfix_999.jsonl"))
        with tempfile.TemporaryDirectory() as tmp:
            e = Path(tmp) / "e.jsonl"
            e.write_text("\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_streams(e)
            b = Path(tmp) / "b.jsonl"
            b.write_text("[]\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_streams(b)
            ec = Path(tmp) / "ec.jsonl"
            ec.write_text(
                json.dumps(
                    {
                        "stream_id": "S1",
                        "chunks": [],
                        "trigger_token": "X",
                        "cut_after_chunk_index": 0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_streams(ec)
            n = Path(tmp) / "n.jsonl"
            row = {
                "stream_id": "SN",
                "chunks": [None, "abc"],
                "trigger_token": "abc",
                "cut_after_chunk_index": 0,
            }
            n.write_text(json.dumps(row) + "\n", encoding="utf-8")
            s = measure_streams(load_streams(n), MeterPolicy())
            self.assertEqual(s.verdicts[0].status, "CUT_BEFORE_EMIT")

    def test_committed_fixture_leaks_120_bytes_across_eight_split_streams(self) -> None:
        s = measure_streams(load_streams(FIX), load_policy(POL))
        self.assertEqual(s.total_streams, 24)
        self.assertEqual(s.leaking_streams_count, 8)
        self.assertEqual(s.split_trigger_streams_count, 8)
        self.assertEqual(s.total_leaked_bytes, 120)
        self.assertEqual(s.worst_leaked_bytes, 15)
        self.assertAlmostEqual(s.resolution_floor_pct, 4.17)
        self.assertFalse(s.gate_passed)

    def test_empty_streams_rejected(self) -> None:
        with self.assertRaises(ValueError):
            measure_streams([], MeterPolicy())

    def test_cli_exit_codes_and_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            oj = Path(tmp) / "o.json"
            rc = cli_main([
                "measure", "--fixture", str(FIX), "--policy", str(POL), "--out", str(oj)
            ])
            self.assertEqual(rc, 1)
            pf = Path(tmp) / "p.json"
            pf.write_text(json.dumps({"max_allowed_leaked_bytes": 5000}), encoding="utf-8")
            rc2 = cli_main([
                "measure", "--fixture", str(FIX), "--policy", str(pf),
                "--out", str(oj), "--json-only",
            ])
            self.assertEqual(rc2, 0)
        self.assertEqual(cli_main(["measure", "--fixture", "/tmp/missing_st_888.jsonl"]), 2)
        self.assertEqual(cli_main(["measure", "--max-rows", "abc"]), 2)
        self.assertEqual(cli_main(["--help"]), 0)
        s = measure_streams(load_streams(FIX), load_policy(POL))
        self.assertIn("LEAKED_BEFORE_CUT", render_table(s))
