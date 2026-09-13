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


class TransientLLMError(Exception):
    """Empty/unparseable LLM response body, treated as retryable by
    run_pilot.with_retry, same spirit as a network error.

    Moved above the passive clients so they can raise it too. Reasoning
    models make empty bodies common: gpt-5-mini spent 960 reasoning
    tokens and emitted no content on 2026-09-13, which the parser scored
    as a malformed answer, indistinguishable from a wrong one.
    """



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


def call_openai(model, messages, max_tokens, base_url, timeout):
    """OpenAI-compatible chat endpoint. Also covers LM Studio and any other
    local server exposing /v1/chat/completions -- point --base-url at it; the
    key falls back to a placeholder, which local servers ignore."""
    body = {"model": model, "messages": messages}
    if _is_gpt_reasoning(model):
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


def call_openai_chat(model, system, messages, max_tokens, base_url):
    full_messages = [{"role": "system", "content": system}] + list(messages)
    body = {"model": model, "messages": full_messages}
    if _is_gpt_reasoning(model):
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
        body["temperature"] = 0
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "authorization":
                     f"Bearer {os.environ['OPENAI_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data["choices"][0]["message"]["content"]
    if not text.strip():
        raise TransientLLMError("empty OpenAI response content")
    return text, data.get("usage", {})


def call_azure_chat(deployment, system, messages, max_tokens, endpoint,
                    api_version, reasoning=False):
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
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json",
                 "api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    text = data["choices"][0]["message"]["content"]
    if not text.strip():
        raise TransientLLMError("empty Azure response content")
    return text, data.get("usage", {})
