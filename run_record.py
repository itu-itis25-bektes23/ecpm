#!/usr/bin/env python3
"""Small helpers for append-safe evaluation records and API cost."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile


RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
COST_STATUSES = {"exact", "estimated", "unavailable", "local_unpriced"}


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cost_record(usage, pricing=None, local=False):
    """Return a cost record without inventing missing prices or usage."""
    if local:
        return {"currency": "USD", "status": "local_unpriced",
                "amount": None}

    usage = usage or {}
    pricing = pricing or {}
    input_tokens = usage.get("input_tokens")
    cached_tokens = usage.get("cached_input_tokens", 0)
    output_tokens = usage.get("output_tokens")
    input_rate = pricing.get("input_per_million")
    cached_rate = pricing.get("cached_input_per_million")
    output_rate = pricing.get("output_per_million")
    values = (input_tokens, cached_tokens, output_tokens,
              input_rate, output_rate)
    if any(not isinstance(value, (int, float)) or value < 0
           for value in values):
        return {"currency": "USD", "status": "unavailable",
                "amount": None}
    if cached_tokens > input_tokens:
        raise ValueError("cached_input_tokens cannot exceed input_tokens")
    if cached_tokens and (not isinstance(cached_rate, (int, float))
                          or cached_rate < 0):
        return {"currency": "USD", "status": "unavailable",
                "amount": None}
    if not cached_tokens:
        cached_rate = 0 if cached_rate is None else cached_rate

    uncached_tokens = input_tokens - cached_tokens
    amount = (
        uncached_tokens * input_rate
        + cached_tokens * cached_rate
        + output_tokens * output_rate
    ) / 1_000_000
    status = ("exact" if usage.get("token_count_source") == "api"
              else "estimated")
    return {
        "currency": "USD",
        "status": status,
        "input_per_million": input_rate,
        "cached_input_per_million": cached_rate,
        "output_per_million": output_rate,
        "amount": round(amount, 8),
        "pricing_source": pricing.get("pricing_source"),
        "pricing_effective_date": pricing.get("pricing_effective_date"),
    }


def _paths(output_dir, run_id):
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run_id may contain only letters, numbers, . _ and -")
    return (
        os.path.join(output_dir, run_id + ".raw.pending"),
        os.path.join(output_dir, run_id + ".json"),
    )


def resume_status(output_dir, run_id):
    pending, final = _paths(output_dir, run_id)
    if os.path.exists(final):
        return "complete"
    if os.path.exists(pending):
        return "pending"
    return "missing"


def save_pending_raw(output_dir, run_id, raw_text):
    """Persist the first raw response before parsing. Never overwrite."""
    if not isinstance(raw_text, str):
        raise TypeError("raw_text must be a string")
    os.makedirs(output_dir, exist_ok=True)
    pending, final = _paths(output_dir, run_id)
    if os.path.exists(final):
        raise FileExistsError(final)
    with open(pending, "x", encoding="utf-8") as handle:
        handle.write(raw_text)
        handle.flush()
        os.fsync(handle.fileno())
    return sha256_text(raw_text)


def finalize_record(output_dir, record):
    """Atomically create the final JSON after parsing/scoring."""
    if not isinstance(record, dict) or not isinstance(record.get("run_id"), str):
        raise ValueError("record requires run_id")
    run_id = record["run_id"]
    pending, final = _paths(output_dir, run_id)
    if os.path.exists(final):
        raise FileExistsError(final)
    with open(pending, encoding="utf-8") as handle:
        saved_raw = handle.read()
    response = record.get("response") or {}
    if response.get("raw_text") != saved_raw:
        raise ValueError("record raw_text does not match pending response")
    if response.get("raw_sha256") != sha256_text(saved_raw):
        raise ValueError("record raw_sha256 does not match raw_text")

    fd, temporary = tempfile.mkstemp(
        prefix=run_id + ".", suffix=".tmp", dir=output_dir, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, final)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    os.unlink(pending)
    return final
