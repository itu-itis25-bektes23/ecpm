#!/usr/bin/env python3
"""Provider-specific model-calling functions for run_pilot.py.

All three take a full `messages` list, so the same call works for a
one-shot probe and for a later turn that carries history.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request


# Claude models that run with thinking on by default and reject explicit
# sampling params (temperature/top_p/top_k).
_ANTHROPIC_NO_SAMPLING = {
    "claude-opus-5", "claude-sonnet-5", "claude-fable-5", "claude-mythos-5",
    "claude-opus-4-8", "claude-opus-4-7",
}


class TransientLLMError(Exception):
    """Empty/unparseable LLM response body, treated as retryable by
    run_pilot.with_retry, same spirit as a network error.
    """


def usage_totals(calls):
    """Count alternate provider names once; unknown usage is not measured zero."""
    conflicts = []
    def total(field, names):
        values = []
        for i, usage in enumerate(calls):
            if not isinstance(usage, dict):
                continue
            candidates = [usage[k] for k in names if usage.get(k) is not None]
            if not candidates or any(type(v) is not int or v < 0 for v in candidates):
                continue
            if len(set(candidates)) != 1:
                conflicts.append({"call": i, "field": field})
                continue
            values.append(candidates[0])
        subtotal = sum(values) if values or not calls else None
        return subtotal if len(values) == len(calls) else None, subtotal, len(values)
    inp, reported_inp, n_inp = total("input", ("prompt_tokens", "input_tokens"))
    out, reported_out, n_out = total("output", ("completion_tokens", "output_tokens"))
    return {"calls": len(calls), "input_tokens": inp, "output_tokens": out,
            "reported_input_tokens": reported_inp, "reported_output_tokens": reported_out,
            "n_input_reported": n_inp, "n_output_reported": n_out,
            "usage_complete": n_inp == n_out == len(calls), "alias_conflicts": conflicts}



def _content_or_retry(data):
    """Pull the assistant text out of an OpenAI-shaped response.

    Raises TransientLLMError when the content is absent or blank, so the
    caller's retry handles it. The reasoning-token count goes in the
    message because it is the useful diagnostic: a large count with empty
    content means the model thought and then said nothing.
    """
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    if content and content.strip():
        return content
    det = (data.get("usage") or {}).get("completion_tokens_details") or {}
    raise TransientLLMError(
        "empty completion (reasoning_tokens="
        f"{det.get('reasoning_tokens')}, finish_reason="
        f"{(data.get('choices') or [{}])[0].get('finish_reason')!r})")


def _is_gpt_reasoning(model):
    """True for the GPT-5/GPT-6 reasoning families (gpt-5, gpt-5.1,
    gpt-5.1-codex, gpt-5-pro, gpt-6-astra, ...), which reject temperature
    and `max_tokens` on Chat Completions. Use `max_completion_tokens`
    instead. False for non-reasoning chat variants (e.g.
    gpt-5-chat-latest), which still accept temperature/max_tokens
    normally."""
    model = model.split("/")[-1]   # OpenRouter ids carry a provider prefix, e.g. openai/gpt-5.6-sol
    return model.startswith(("gpt-5", "gpt-6")) and "chat" not in model


# --------------------------------------------------------------------
# Passive-pilot clients: one-shot, no conversation history.
# --------------------------------------------------------------------


def call_anthropic(model, messages, max_tokens, timeout):
    body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if model not in _ANTHROPIC_NO_SAMPLING:
        body["temperature"] = 0
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    text = "".join(b.get("text", "") for b in data.get("content", []))
    return text, data.get("usage", {})


def call_azure(deployment, messages, max_tokens, endpoint, api_version,
               timeout, reasoning=False):
    """`deployment` is the Azure-side deployment name,
    pass `reasoning=True` explicitly (run_pilot.py's
    --azure-reasoning-model flag) when the deployment is a GPT reasoning model."""
    url = (endpoint.rstrip("/") + "/openai/deployments/" + deployment
           + "/chat/completions?api-version=" + api_version)
    body = {"messages": messages}
    if reasoning:
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
        body["temperature"] = 0
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return _content_or_retry(data), data.get("usage", {})


def call_openai(model, messages, max_tokens, base_url, timeout, extra=None):
    """OpenAI-compatible chat endpoint. Also covers LM Studio and any other
    local server exposing /v1/chat/completions -- point --base-url at it; the
    key falls back to a placeholder, which local servers ignore.

    extra: validated reasoning-control fields (e.g. OpenRouter
    {"reasoning": {"enabled": false}}), merged into the request body."""
    body = {"model": model, "messages": messages}
    if _is_gpt_reasoning(model):
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
        body["temperature"] = 0
    if extra:
        body.update(extra)
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "authorization":
                     f"Bearer {os.environ.get('OPENAI_API_KEY', 'local')}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return _content_or_retry(data), data.get("usage", {})


# --------------------------------------------------------------------
# Active-pilot clients: multi-turn variants (system + a growing message list)
# Wrapped in with_retry by the caller
# --------------------------------------------------------------------


def call_anthropic_chat(model, system, messages, max_tokens, thinking_budget=0):
    """Calls Claude with the given system prompt and message history.
    If thinking_budget > 0, enables Extended Thinking with that token
    budget (Anthropic requires temperature 1 and max_tokens greater than
    thinking_budget in that case) and returns the thinking content
    separately from the visible answer. Ignored on models in
    _ANTHROPIC_NO_SAMPLING, they run adaptive thinking by default and
    reject both temperature and the old fixed budget_tokens format."""
    body = {"model": model, "max_tokens": max_tokens, "system": system,
            "messages": messages}
    no_sampling = model in _ANTHROPIC_NO_SAMPLING
    if thinking_budget > 0 and not no_sampling:
        body["thinking"] = {"type": "enabled",
                            "budget_tokens": thinking_budget}
        body["temperature"] = 1
    elif not no_sampling:
        body["temperature"] = 0
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                 "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    reasoning = "".join(b.get("thinking", "") for b in data.get("content", [])
                        if b.get("type") == "thinking")
    text = "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")
    if not text.strip():
        raise TransientLLMError("empty Anthropic response content")
    return text, reasoning, data.get("usage", {})


RETRIED_USAGE = []   # usage of empty replies that were retried; the agentic runner records them
_CAPS = {}   # output cap a provider accepted, per model, learned from "too large" rejections
_CAP_TOO_LARGE = re.compile(r"max_(completion_)?tokens|maximum[^.]{0,40}tokens|output tokens|token limit", re.I)
_CAP_FLOOR = 1024
# Seconds per chat request. A 16k-token reasoning answer can take minutes on a slow provider;
# 120 s timed out and was retried from scratch. Override with ECPM_HTTP_TIMEOUT.
CHAT_TIMEOUT = int(os.environ.get("ECPM_HTTP_TIMEOUT", "600"))


def _post_json(req, body=None, key=None):
    """POST and decode; a 400 keeps its type (not retried) but carries the provider's reason.
    If the provider rejects the output cap as too large, the cap drops to the largest smaller
    number its message states (e.g. "maximum allowed is 8192"), or is halved when it states none,
    not below 1024; it is remembered for that model, so later calls start at the accepted value.
    The timeout grows with the cap, since a long answer takes minutes on a slow provider."""
    field = next((f for f in ("max_completion_tokens", "max_tokens") if body and f in body), None)
    if field and key in _CAPS and body[field] > _CAPS[key]:
        body[field] = _CAPS[key]
    while True:
        if body is not None:   # a fresh request each attempt, so the length header matches the body
            req = urllib.request.Request(req.full_url, data=json.dumps(body).encode(), headers={
                k: v for k, v in req.header_items() if k.lower() != "content-length"})
        try:
            cap = body[field] if field else 0
            with urllib.request.urlopen(req, timeout=max(CHAT_TIMEOUT, 60 + cap // 20)) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as ex:
            if ex.code != 400:
                raise
            reason = ex.read().decode(errors="replace")[:500]
            stated = [int(n) for n in re.findall(r"\d+", reason) if int(n) < (body[field] if field else 0)]
            if field and body[field] > _CAP_FLOOR and _CAP_TOO_LARGE.search(reason) \
                    and not (stated and max(stated) < _CAP_FLOOR):   # a stated limit under the floor: stop
                body[field] = max(max(stated), _CAP_FLOOR) if stated else max(_CAP_FLOOR, body[field] // 2)
                _CAPS[key] = body[field]
                print(f"output cap rejected for {key}; retrying with {body[field]}: {reason[:160]}")
                continue
            raise urllib.error.HTTPError(ex.url, ex.code, f"{ex.msg}: {reason}", ex.headers, None) from None


def call_openai_chat(model, system, messages, max_tokens, base_url, extra=None):
    full_messages = [{"role": "system", "content": system}] + list(messages)
    body = {"model": model, "messages": full_messages}
    if _is_gpt_reasoning(model):
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
        body["temperature"] = 0
    body.update(extra or {})   # validated provider controls, e.g. reasoning_effort
    reasoning = (extra or {}).get("reasoning")
    if model.startswith("anthropic/") and isinstance(reasoning, dict) and reasoning.get("enabled", True):
        body.pop("temperature", None)   # Anthropic models reject temperature 0 while thinking is on
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "authorization":
                     f"Bearer {os.environ['OPENAI_API_KEY']}"})
    data = _post_json(req, body, model)
    text = data["choices"][0]["message"].get("content") or ""
    # finish_reason is kept with each call's usage, so "length" (cut off) can be told apart from "stop"
    usage = {**(data.get("usage") or {}), "finish_reason": data["choices"][0].get("finish_reason"),
             "max_tokens_used": body.get("max_completion_tokens", body.get("max_tokens"))}
    if not text.strip():
        RETRIED_USAGE.append({**usage, "retried": True})   # billed even though empty: kept for the totals
        raise TransientLLMError("empty OpenAI response content (finish_reason="
                                f"{data['choices'][0].get('finish_reason')})")
    return text, usage


def call_azure_chat(deployment, system, messages, max_tokens, endpoint,
                    api_version, reasoning=False, extra=None):
    """`deployment` is the Azure-side deployment name; pass
    `reasoning=True` explicitly (run_pilot.py's --azure-reasoning-model
    flag) when the deployment is a GPT reasoning model."""
    full_messages = [{"role": "system", "content": system}] + list(messages)
    url = (endpoint.rstrip("/") + "/openai/deployments/" + deployment
           + "/chat/completions?api-version=" + api_version)
    body = {"messages": full_messages}
    if reasoning:
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
        body["temperature"] = 0
    body.update(extra or {})   # validated provider controls, e.g. reasoning_effort
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    data = _post_json(req, body, deployment)
    text = data["choices"][0]["message"].get("content") or ""
    # finish_reason is kept with each call's usage, so "length" (cut off) can be told apart from "stop"
    usage = {**(data.get("usage") or {}), "finish_reason": data["choices"][0].get("finish_reason"),
             "max_tokens_used": body.get("max_completion_tokens", body.get("max_tokens"))}
    if not text.strip():
        RETRIED_USAGE.append({**usage, "retried": True})   # billed even though empty: kept for the totals
        raise TransientLLMError("empty Azure response content (finish_reason="
                                f"{data['choices'][0].get('finish_reason')})")
    return text, usage
