#!/usr/bin/env python3
"""Provider-specific model-calling functions for run_pilot.py.

All three take a full `messages` list, so the same call works for a
one-shot probe and for a later turn that carries history.
"""

from __future__ import annotations

import json
import os
import urllib.request

# Claude models that run with thinking on by default and reject explicit
# sampling params (temperature/top_p/top_k).
_ANTHROPIC_NO_SAMPLING = {
    "claude-opus-5", "claude-sonnet-5", "claude-fable-5", "claude-mythos-5",
    "claude-opus-4-8", "claude-opus-4-7",
}


def _is_gpt5_reasoning(model):
    """True for the GPT-5 reasoning family (gpt-5, gpt-5.1, gpt-5.1-codex,
    gpt-5-pro, ...), which reject temperature and `max_tokens` on Chat
    Completions. Use `max_completion_tokens` instead. False for the
    non-reasoning gpt-5-chat-latest variant, which still accepts
    temperature/max_tokens normally."""
    return model.startswith("gpt-5") and "chat" not in model


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
    --azure-reasoning-model flag) when the deployment is a GPT-5-family
    reasoning model."""
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
    return data["choices"][0]["message"]["content"], data.get("usage", {})


def call_openai(model, messages, max_tokens, base_url, timeout):
    """OpenAI-compatible chat endpoint. Also covers LM Studio and any other
    local server exposing /v1/chat/completions -- point --base-url at it; the
    key falls back to a placeholder, which local servers ignore."""
    body = {"model": model, "messages": messages}
    if _is_gpt5_reasoning(model):
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
        body["temperature"] = 0
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "authorization":
                     f"Bearer {os.environ.get('OPENAI_API_KEY', 'local')}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"], data.get("usage", {})
