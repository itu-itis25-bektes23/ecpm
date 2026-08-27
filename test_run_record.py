#!/usr/bin/env python3
"""Tests for raw-first records and cost tracking. Stdlib only."""

import json
import os
import tempfile

from run_record import (cost_record, finalize_record, resume_status,
                        save_pending_raw)


def test_cost_records():
    usage = {
        "input_tokens": 1_000_000,
        "cached_input_tokens": 200_000,
        "output_tokens": 100_000,
        "token_count_source": "api",
    }
    pricing = {
        "input_per_million": 2.0,
        "cached_input_per_million": 0.5,
        "output_per_million": 8.0,
        "pricing_source": "provider",
        "pricing_effective_date": "2026-01-01",
    }
    exact = cost_record(usage, pricing)
    assert exact["status"] == "exact"
    assert exact["amount"] == 2.5
    assert cost_record({}, {})["status"] == "unavailable"
    assert cost_record({}, {}, local=True)["status"] == "local_unpriced"


def test_raw_first_finalization_and_resume():
    with tempfile.TemporaryDirectory() as output_dir:
        run_id = "seed1-turnA-model"
        raw = '{"answer": true}'
        raw_hash = save_pending_raw(output_dir, run_id, raw)
        assert resume_status(output_dir, run_id) == "pending"
        record = {
            "run_id": run_id,
            "response": {"raw_text": raw, "raw_sha256": raw_hash},
            "parser": {"parse_status": "ok"},
            "scores": None,
        }
        final = finalize_record(output_dir, record)
        assert resume_status(output_dir, run_id) == "complete"
        assert not os.path.exists(os.path.join(
            output_dir, run_id + ".raw.pending"))
        with open(final, encoding="utf-8") as handle:
            assert json.load(handle) == record
        try:
            save_pending_raw(output_dir, run_id, raw)
        except FileExistsError:
            pass
        else:
            raise AssertionError("completed runs must not be overwritten")


def test_mismatched_raw_is_rejected():
    with tempfile.TemporaryDirectory() as output_dir:
        run_id = "mismatch"
        save_pending_raw(output_dir, run_id, "first")
        record = {
            "run_id": run_id,
            "response": {"raw_text": "different", "raw_sha256": "wrong"},
        }
        try:
            finalize_record(output_dir, record)
        except ValueError:
            pass
        else:
            raise AssertionError("mismatched raw response must fail")


if __name__ == "__main__":
    test_cost_records()
    test_raw_first_finalization_and_resume()
    test_mismatched_raw_is_rejected()
    print("ALL RUN RECORD TESTS PASSED")
