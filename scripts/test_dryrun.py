"""Regression checks for the pre-deployment source gate; no network needed."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import dryrun_clues


class DryRunGate(unittest.TestCase):
    def run_gate(self, text):
        clue = {
            "title": "Fixture",
            "source_url": "https://example.com/fixture",
            "anchor": "the evidence begins",
            "window_chars": 300,
            "answer_pattern": "[a-z]+",
            "expected": "stout",
        }
        with tempfile.TemporaryDirectory() as directory:
            spec = Path(directory) / "clues.json"
            spec.write_text(json.dumps({"clues": [clue]}))
            with patch.object(dryrun_clues, "fetch", return_value=text):
                with contextlib.redirect_stdout(io.StringIO()):
                    return dryrun_clues.main(spec)

    def test_ready_source_passes(self):
        self.assertEqual(self.run_gate("the evidence begins stout " + "context " * 50), 0)

    def test_duplicate_anchor_blocks_deployment(self):
        text = "the evidence begins stout " + "context " * 50 + "the evidence begins"
        self.assertEqual(self.run_gate(text), 1)

    def test_answer_outside_window_blocks_deployment(self):
        text = "the evidence begins " + "context " * 50 + "stout"
        self.assertEqual(self.run_gate(text), 1)


if __name__ == "__main__":
    unittest.main()
