"""Fixed deterministic graph-availability follow-up; no legacy policy changes."""

import copy
import datetime
import functools
import hashlib
import json
import math
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import ecpm_baseline
import run_pilot as pilot

PROTOCOL = "icl_graph_availability_v1"
CONDITIONS = ("graph_ab", "graph_a", "logs_only")
GRAPH_SEEDS = (8, 13, 25)
MODELS = {"gemma_e4b": "sunil-pathak/gemma-4-e4b-it",
          "gemma_31b": "google/gemma-4-31B-it", "sol": "gpt-5.6-sol",
          "gemma_31b_together": "google/gemma-4-31B-it"}
HOSTED_PROFILES = {"gemma_31b", "gemma_31b_together", "sol"}
EXPANDED_MODELS = {**MODELS, "deepseek_openrouter": "deepseek/deepseek-v4.1-flash"}
EXPANDED_HOSTED_PROFILES = HOSTED_PROFILES | {"deepseek_openrouter"}
HOSTED_READINESS_POLICY = "hosted_readiness_v1"
LOCAL_CONTEXT = "local_backend_tokenizer_v1"
PREFLIGHT = ("Find the smallest positive integer n that is divisible by 7 and "
             "leaves remainder 1 when divided by each of 2, 3, 4, 5, and 6. "
             "Return only the final integer.")
COMMON = """Each action has one destination. A successful attempt moves to that
destination. A failed attempt leaves the system at the current node.
The action can then be tried again. Each attempt costs 1.
Each log row is [current_node, action, observed_next_node].

available means the action is in the current action menu. It does not mean
the action succeeds. destination means the node reached on success, not
the node where a failed attempt leaves you.

If a graph is supplied for the current period, use its destination and
success probability. Otherwise, use the logs: an attempt succeeds exactly
when observed_next_node differs from current_node. Calculate p_success
using only this period's successes divided by this period's observations
for that action. If there are observations but no successes, p_success is 0.
Use the destination shown by a successful observation. If there is none
in this period, use the most recent earlier destination supported by the
supplied graph or logs; if none is known, use null. Carry forward only the
destination, not the earlier probability. If an action is unavailable,
use available=false, destination=null and p_success=null.

Choose a route from Start to Goal that minimizes the expected number of
attempts in the current period. A route lists actions to take, retrying
an action after a failure. The first action must be at Start; the successful
destination of the final action must be Goal. Do not add an action at Goal
after arrival."""
COMPARE = """Compare Period B with Period A, using the supplied evidence, not whether
you changed your wording. Report whether any action changed, which action
changed, and whether each queried action changed. A change means a change
in availability, destination or success probability. If nothing changed,
set changed=false and changed_pair=null. Otherwise set changed=true and
name the changed pair. Report current Period B beliefs and its best route."""
PLACEHOLDERS = ("Replace all angle-bracket placeholders with values. DESTINATION is a "
                "node string or null; PROBABILITY is a number or null; BOOLEAN is "
                "true or false. The route array must contain all required action steps.")
ENDING = "Return exactly one JSON object, with no text or code fences before or after it."
VIEW_KEYS = {"period", "nodes", "start", "goal", "menu", "rows", "graph", "queried_pairs"}
EDGE_KEYS = {"node", "action", "available", "destination", "p_success"}


def authorized_view(record, view, period, include_graph, queried):
    """Outer orchestration only: project whitelisted CURRENT period fields."""
    menu = copy.deepcopy(view[f"legal_actions_{period}"])
    for node in view["nodes"]:
        menu.setdefault(node, [])
    graph = None
    if include_graph:
        graph = sorted(({
            "node": edge["from"], "action": edge["action"], "available": True,
            "destination": edge["to"], "p_success": edge["p"],
        } for edge in record[f"world_{period}"]["edges"]
            if edge["action"] in menu.get(edge["from"], [])),
            key=lambda edge: (edge["node"], edge["action"]))
    result = {"period": "A" if period == "pre" else "B",
              "nodes": list(view["nodes"]), "start": view["start"],
              "goal": view["goal"], "menu": menu,
              "rows": pilot.raw_visible_rows(view, period), "graph": graph,
              "queried_pairs": copy.deepcopy(queried)}
    validate_view(result)
    return result


def validate_view(view):
    """Reject extra metadata, missing observations and non-pilot inputs."""
    if set(view) != VIEW_KEYS or view["period"] not in ("A", "B"):
        raise ValueError("unauthorized period-view fields")
    nodes = view["nodes"]
    if (nodes != list("ABCDEFGH") or view["start"] not in nodes
            or view["goal"] not in nodes or view["start"] == view["goal"]):
        raise ValueError("only the fixed eight-node pilot is supported")
    menu = view["menu"]
    if set(menu) != set(nodes) or any(
            not isinstance(actions, list) or len(set(actions)) != len(actions)
            or any(not re.fullmatch(r"a[1-9][0-9]*", action) for action in actions)
            for actions in menu.values()):
        raise ValueError("invalid current menu")
    queried = view["queried_pairs"]
    if (not isinstance(queried, list) or len(queried) != 5
            or any(not isinstance(q, dict) or set(q) != {"node", "action"}
                   or q["action"] not in menu.get(q["node"], []) for q in queried)):
        raise ValueError("requires five available queried pairs without role labels")
    keys = [(q["node"], q["action"]) for q in queried]
    if keys != sorted(set(keys)):
        raise ValueError("queried pairs must be distinct and sorted")
    if len(view["rows"]) != 160 or sum(map(len, menu.values())) != 16:
        raise ValueError("pilot requires 160 rows and 16 available actions")
    for row in view["rows"]:
        if not re.fullmatch(r"\[[A-H], a[1-9][0-9]*, [A-H]\]", row):
            raise ValueError("invalid observation row")
        node, action, _ = row[1:-1].split(", ")
        if action not in menu[node]:
            raise ValueError("observation action not in current menu")
    stats = pilot.visible_transition_stats(view["rows"], menu)
    if any(s["observations"] != 10 or s["p_success"] not in (0, 1)
           or len([n for n in s["next_state_counts"] if n != key[0]]) > 1
           for key, s in stats.items()):
        raise ValueError("requires ten deterministic observations per action")
    graph = view["graph"]
    if graph is not None:
        if not isinstance(graph, list) or len(graph) != 16:
            raise ValueError("incomplete graph")
        seen = []
        for edge in graph:
            if set(edge) != EDGE_KEYS:
                raise ValueError("unauthorized graph fields")
            key = (edge["node"], edge["action"])
            if (key not in stats or edge["available"] is not True
                    or edge["destination"] not in nodes
                    or edge["destination"] == key[0]
                    or type(edge["p_success"]) not in (int, float)
                    or edge["p_success"] != stats[key]["p_success"]):
                raise ValueError("graph does not agree with deterministic observations")
            movement = [n for n in stats[key]["next_state_counts"] if n != key[0]]
            if movement and movement != [edge["destination"]]:
                raise ValueError("graph destination does not agree with observations")
            seen.append(key)
        if seen != sorted(stats):
            raise ValueError("graph must cover sorted available pairs exactly")


def graph_block(view):
    if view["graph"] is None:
        return ""
    lines = [f"Complete graph, Period {view['period']}:",
             "node | action | available | destination | p_success"]
    for edge in view["graph"]:
        lines.append(f"{edge['node']} | {edge['action']} | true | "
                     f"{edge['destination']} | {float(edge['p_success']):.1f}")
    lines.extend(f"{node} has no available actions."
                 for node, actions in sorted(view["menu"].items()) if not actions)
    return "\n".join(lines) + "\n\n"


def build_prompt(view):
    """No evaluator record or condition name is accepted by this builder."""
    validate_view(view)
    period = view["period"]
    lines = []
    for pair in view["queried_pairs"]:
        fields = f'{{"node":"{pair["node"]}","action":"{pair["action"]}","available":<BOOLEAN>'
        if period == "B":
            fields += ',"changed":<BOOLEAN>'
        lines.append(fields + ',"destination":<DESTINATION>,"p_success":<PROBABILITY>}')
    extra = ('  "changed":<BOOLEAN>,\n'
             '  "changed_pair":<null or {"node":"...","action":"..."}>,\n'
             if period == "B" else "")
    schema = ('Return this structure with all placeholders replaced:\n{\n'
              + extra + '  "pairs": [\n    ' + ',\n    '.join(lines)
              + '\n  ],\n  "route": [<ALL ROUTE STEPS AS {"node":"...","action":"..."}>]\n}')
    opening = "Period A." if period == "A" else "Period B may or may not differ from Period A."
    output = (COMPARE + "\n\n" if period == "B" else "") + PLACEHOLDERS
    return (opening + "\n" + COMMON + "\n\n"
            + f"Nodes: {', '.join(view['nodes'])}\n"
            + f"Start: {view['start']}   Goal: {view['goal']}\n"
            + f"Action menu, Period {period}: {pilot._format_menu(view['menu'])}\n\n"
            + graph_block(view)
            + f"Raw shuffled observations, Period {period}:\n"
            + "\n".join(view["rows"]) + "\n\nPairs to report in this order:\n"
            + pilot._format_queried_pairs(view["queried_pairs"]) + "\n\n" + output + "\n\n"
            + schema + "\n" + ENDING + "\n")


def prepare(sc):
    required = {"condition": "silent_break", "matched": True,
                "k": 10, "budget": 10, "evidence_seed": 0, "rendering": "F2_shuffled"}
    if sc.get("seed") not in GRAPH_SEEDS or any(sc.get(k) != v for k, v in required.items()):
        raise ValueError("graph protocol supports seeds 8, 13, 25: deterministic silent break, K=budget=10, evidence seed=0")
    if not pilot.deterministic_gate(sc["seed"])["eligible"]:
        raise ValueError("graph seed fails deterministic eligibility")
    record = pilot.build_record(sc, True)
    view = pilot.prompt_view(record, rendering="F2_shuffled", periods=("pre", "post"),
                             budget_per_pair=10, budget_seed=0)
    queried = pilot.queried_pairs_for_icl(record, sc)
    variants = {}
    for condition in CONDITIONS:
        variants[condition] = [authorized_view(record, view, period,
                              condition == "graph_ab" or (condition == "graph_a" and period == "pre"), queried)
                              for period in ("pre", "post")]
    # Freeze all six before selecting a condition or making any call.
    prompts = {c: [build_prompt(v) for v in views] for c, views in variants.items()}
    for i in (0, 1):
        stripped = [prompts[c][i].replace(graph_block(variants[c][i]), "", 1)
                    if graph_block(variants[c][i]) else prompts[c][i] for c in CONDITIONS]
        if len(set(stripped)) != 1:
            raise ValueError("non-graph prompt content differs")
    return record, view, variants, prompts


def reference_answer(view, earlier=None):
    """Sequential graph/log solver; earlier contains estimates, never B truth."""
    validate_view(view)
    if view["period"] == "B" and earlier is None:
        raise ValueError("Period B requires earlier estimates")
    if view["graph"] is not None:
        estimates = {(e["node"], e["action"]): dict(e) for e in view["graph"]}
    else:
        events = [tuple(row[1:-1].split(", ")) for row in view["rows"]]
        stats, destinations = ecpm_baseline.tally(events)
        estimates = {}
        for key, row in sorted(stats.items()):
            dests = destinations.get(key, {})
            destination = (next(iter(dests)) if dests else
                           (earlier or {}).get(key, {}).get("destination"))
            estimates[key] = {"node": key[0], "action": key[1], "available": True,
                              "destination": destination, "p_success": ecpm_baseline.rate(row)}
    route_stats = {key: {"attempts": 1, "delivered": row["p_success"]}
                   for key, row in estimates.items()}
    dests = {key: {row["destination"]: 1} for key, row in estimates.items()
             if row["destination"] is not None}
    route = ecpm_baseline.plan_route(dests, route_stats, view["start"], view["goal"], view["menu"])
    pairs = [dict(estimates[(q["node"], q["action"])]) for q in view["queried_pairs"]]
    answer = {"pairs": pairs, "route": route["route"]}
    if earlier is not None:
        changed = {key for key in set(earlier) | set(estimates)
                   if earlier.get(key) != estimates.get(key)}
        if len(changed) > 1:
            raise ValueError("reference expects at most one changed action")
        for row in pairs:
            row["changed"] = (row["node"], row["action"]) in changed
        answer.update(changed=bool(changed), changed_pair=(
            {"node": next(iter(changed))[0], "action": next(iter(changed))[1]} if changed else None))
    return json.dumps(answer, separators=(",", ":")), estimates


def intended_settings(profile, mode, seed, seed_supported=False, allowed_seeds=(0, 1, 2, 999)):
    if profile not in EXPANDED_MODELS or mode not in ("off", "on") or type(seed) is not int or seed not in allowed_seeds:
        raise ValueError("unknown request profile, reasoning mode or seed")
    if profile == "deepseek_openrouter":
        if seed_supported:
            raise ValueError("OpenRouter profile omits unverified provider seeds")
        return {"max_tokens": 8192, "reasoning": {"enabled": mode == "on", "exclude": False},
                "provider": {"require_parameters": True, "allow_fallbacks": False},
                "plugins": [{"id": "context-compression", "enabled": False}]}
    if profile == "sol":
        if seed_supported:
            raise ValueError("Sol profile must omit sampling controls in both modes")
        return {"max_completion_tokens": 8192,
                "reasoning_effort": "none" if mode == "off" else "medium"}
    body = {"max_tokens": 8192, "reasoning": mode,
            "temperature": 1.0, "top_p": 0.95, "top_k": 64}
    if profile == "gemma_31b_together":
        body["reasoning"] = {"enabled": mode == "on"}
    if seed_supported:
        body["seed"] = seed
    return body


def no_secrets(value):
    """Fail rather than publish sensitive config/provider fields; never print values."""
    def visit(item, path):
        if isinstance(item, dict):
            for key, val in item.items():
                if re.fullmatch(r"(?i)(authorization|api.?key|password|secret|access.?token|cookie)", key) and val:
                    raise ValueError("sensitive field: " + path + "." + key)
                visit(val, path + "." + key)
        elif isinstance(item, list):
            for i, val in enumerate(item):
                visit(val, path + f"[{i}]")
        elif isinstance(item, str) and re.search(
                r"/Users/|/home/|(?i:Bearer\s+\S+|-----BEGIN .*PRIVATE KEY-----)|\b(?:sk-|ghp_|github_pat_)[\w-]{12,}", item):
            raise ValueError("sensitive content at " + path)
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, (dict, list)):
            visit(decoded, "root")
    visit(value, "root")


def context_bound(messages, config, reserve_answer=0, *, output_tokens=8192, allow_system=False):
    """Conservative bound, NOT an exact tokenizer count. Source must justify it."""
    context = config["context"]
    if not messages or any(set(m) != {"role", "content"}
                           or m["role"] not in (("system", "user", "assistant") if allow_system else ("user", "assistant"))
                           or not isinstance(m["content"], str) for m in messages):
        raise ValueError("context check needs complete text messages")
    if context.get("method") != "utf8_upper_bound" or not context.get("source"):
        raise ValueError("need documented UTF-8 token bound and template overhead")
    overhead = context["overhead_tokens_per_message"]
    if type(overhead) is not int or overhead < 1:
        raise ValueError("invalid template overhead bound")
    if type(context["tokens"]) is not int or context["tokens"] < 8192:
        raise ValueError("invalid context window")
    # Actual history uses its full UTF-8 size. Planning for an unseen A answer
    # needs a separately justified retokenization expansion bound.
    expansion = context.get("replay_expansion_bound", 0)
    if reserve_answer and (type(expansion) not in (int, float)
                           or not math.isfinite(expansion) or expansion < 1):
        raise ValueError("missing bound for replay of the unseen A answer")
    input_bound = sum(len(m["content"].encode()) + overhead for m in messages)
    input_bound += math.ceil(reserve_answer * expansion)
    if type(output_tokens) is not int or output_tokens not in (4096, 8192, 16384):
        raise ValueError("invalid stage output allowance")
    total = input_bound + output_tokens
    return {"method": context["method"], "input_tokens_upper_bound": input_bound,
            "requested_output_tokens": output_tokens, "total_upper_bound": total,
            "context_tokens": context["tokens"], "fits": total <= context["tokens"],
            "source": context["source"]}


OPENROUTER_CONTEXT_ESTIMATE = "openrouter_utf8_reserve_estimate_v1"


def estimated_context(config):
    return config.get("context", {}).get("method") == OPENROUTER_CONTEXT_ESTIMATE


def hosted_context_check(messages, config, *, output_tokens=8192, allow_system=False):
    """Opt-in engineering estimate, or the unchanged documented-bound method."""
    if not estimated_context(config):
        return context_bound(messages, config, output_tokens=output_tokens, allow_system=allow_system)
    c = config["context"]
    if (config.get("profile") != "deepseek_openrouter"
            or config.get("model") != EXPANDED_MODELS["deepseek_openrouter"]
            or config.get("endpoint") != "https://openrouter.ai/api/v1"
            or output_tokens != 16384 or type(output_tokens) is not int
            or c.get("overhead_tokens_per_message") is not None
            or type(c.get("engineering_reserve_per_message")) is not int
            or c["engineering_reserve_per_message"] != 4096
            or c.get("admission_fraction") != 0.25
            or type(c.get("tokens")) is not int or c["tokens"] < output_tokens
            or not isinstance(c.get("source"), str) or not c["source"].strip()):
        raise ValueError("explicit OpenRouter 16K estimate policy and fixed safety margins required")
    if not messages or any(set(m) != {"role", "content"}
            or m["role"] not in (("system", "user", "assistant") if allow_system else ("user", "assistant"))
            or not isinstance(m["content"], str) for m in messages):
        raise ValueError("context estimate needs complete actual text messages")
    content_bytes = sum(len(m["content"].encode("utf-8")) for m in messages)
    estimate = content_bytes + 4096 * len(messages)
    limit = c["tokens"] // 4
    return {"method": OPENROUTER_CONTEXT_ESTIMATE,
            "status": "engineering_estimate_not_token_bound",
            "content_utf8_bytes": content_bytes, "message_count": len(messages),
            "messages_sha256": pilot._canonical_sha256(messages),
            "engineering_reserve_per_message": 4096, "admission_fraction": 0.25,
            "hosted_overhead_tokens_per_message": None,
            "input_token_units_estimate": estimate, "requested_output_tokens": output_tokens,
            "total_token_units_estimate": estimate + output_tokens,
            "context_tokens": c["tokens"], "admission_limit_tokens": limit,
            "fits": estimate + output_tokens <= limit, "source": c["source"]}


def estimate_usage_check(count, usage):
    actual = usage.get("prompt_tokens")
    known = type(actual) is int and actual >= 0
    return {"reported_prompt_tokens": actual,
            "input_token_units_estimate": count["input_token_units_estimate"],
            "within_estimate": known and actual <= count["input_token_units_estimate"],
            "within_advertised_context": known and actual + count["requested_output_tokens"] <= count["context_tokens"]}


def local_context(config):
    return config.get("context", {}).get("method") == LOCAL_CONTEXT


def validate_local_context(config):
    context = config["context"]
    url = urllib.parse.urlsplit(context.get("backend_url", ""))
    if (config["profile"] != "gemma_e4b" or context.get("tokens") != 32768
            or url.scheme != "http" or url.hostname not in ("localhost", "127.0.0.1", "::1")
            or not url.port or url.path not in ("", "/") or url.username or url.password
            or url.query or url.fragment
            or context.get("credential_env") != "ECPM_LOCAL_BACKEND_API_KEY"
            or not context.get("source")):
        raise ValueError("invalid local tokenizer configuration")
    identity = context.get("identity", {})
    hashes = ("backend_sha256", "model_sha256", "template_sha256", "frontend_sha256",
              "app_settings_sha256", "backend_settings_sha256", "loaded_instances_sha256")
    if (any(not re.fullmatch("[0-9a-f]{64}", identity.get(k, "")) for k in hashes)
            or identity.get("template_sha256") != config["effective"]["template_sha256"]
            or not identity.get("build_info")):
        raise ValueError("unverified local deployment/tokenizer identity")
    expected = {"add_special": True, "parse_special": True, "add_generation_prompt": True,
                "chat_template_kwargs": {"enable_thinking": config["effective"]["thinking"]}}
    if context.get("counting_settings") != expected:
        raise ValueError("local tokenizer/template settings mismatch")


@functools.lru_cache(maxsize=8)
def _file_digest(path, size, mtime, ctime):
    # Cache by file identity to avoid rereading the GGUF for each turn.
    with open(path, "rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    stat = Path(path).stat()
    if (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != (size, mtime, ctime):
        raise ValueError("deployment file changed while hashing")
    return digest


def _digest_file(path):
    stat = Path(path).stat()
    return _file_digest(str(path), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def _metadata(url, body=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), headers=headers)
    with urllib.request.build_opener(NoRedirect()).open(req, timeout=30) as response:
        if response.status != 200:
            raise ValueError("local metadata status is not 200")
        return json.load(response)


def _local_snapshot(config, key):
    """Read-only identity checks; never discovers or saves authentication secrets."""
    context = config["context"]
    props = _metadata(context["backend_url"].rstrip("/") + "/props", key=key)
    native = config["endpoint"].rstrip("/").removesuffix("/v1") + "/api/v1/models"
    loaded = [m for m in _metadata(native)["models"] if m["loaded_instances"]]
    if (len(loaded) != 1 or loaded[0]["key"] != config["model"]
            or loaded[0]["quantization"]["name"] != "Q6_K" or loaded[0]["format"] != "gguf"
            or props.get("is_sleeping") is not False or props.get("model_ftype") != "Q6_K"
            or props.get("total_slots") != 1
            or props.get("default_generation_settings", {}).get("n_ctx") != 32768
            or len(loaded[0]["loaded_instances"]) != 1
            or loaded[0]["loaded_instances"][0]["config"].get("context_length") != 32768):
        raise ValueError("local deployment mismatch")
    # comm contains executable paths, not command arguments or backend credentials.
    executables = [Path(row.strip()) for row in subprocess.check_output(
        ["ps", "-axo", "comm="], text=True).splitlines() if Path(row.strip()).name == "llama-server"]
    if len(executables) != 1:
        raise ValueError("ambiguous local backend")
    model = Path(props["model_path"])
    if model.name != "gemma-4-E4B-it-Q6_K.gguf":
        raise ValueError("local model file mismatch")
    defaults = Path.home() / (".lmstudio/apps/bionic/.internal/user-concrete-model-default-config/"
                             "sunil-pathak/gemma-4-E4B-it-Q6_K/gemma-4-E4B-it-Q6_K.gguf.json")
    identity = {"build_info": props["build_info"], "backend_sha256": _digest_file(executables[0]),
        "model_sha256": _digest_file(model), "template_sha256": pilot.sha256_text(props["chat_template"]),
        "frontend_sha256": _digest_file("/Applications/Bionic.app/Contents/Resources/app/.webpack-bionic/main/index.js"),
        "app_settings_sha256": _digest_file(defaults),
        "backend_settings_sha256": pilot._canonical_sha256(props["default_generation_settings"]),
        "loaded_instances_sha256": pilot._canonical_sha256(loaded[0]["loaded_instances"])}
    return identity


def local_count_record(body, config, rendered, tokens, identity, *, output_tokens=8192):
    if type(output_tokens) is not int or output_tokens not in (4096, 8192, 16384):
        raise ValueError("invalid stage output allowance")
    if (not isinstance(rendered, str) or not rendered or not isinstance(tokens, list)
            or not tokens or any(type(t) is not int or t < 0 for t in tokens)):
        raise ValueError("invalid tokenizer result")
    return {"method": LOCAL_CONTEXT, "request_sha256": pilot._canonical_sha256(body),
        "messages_sha256": pilot._canonical_sha256(body["messages"]),
        "identity": identity, "counting_settings": config["context"]["counting_settings"],
        "rendered_prompt": rendered, "rendered_sha256": pilot.sha256_text(rendered),
        "token_ids": tokens, "token_ids_sha256": pilot._canonical_sha256(tokens),
        "input_tokens": len(tokens), "requested_output_tokens": output_tokens,
        "context_tokens": 32768, "fits": len(tokens) + output_tokens <= 32768}


def count_local_request(body, config, *, output_tokens=8192, allow_system=False):
    """Only metadata, template rendering and tokenization; never generation."""
    validate_local_context(config)
    if (body.get("model") != config["model"] or body.get("max_tokens") != output_tokens
            or type(output_tokens) is not int or output_tokens not in (4096, 8192, 16384)
            or body.get("reasoning") != config["effective"]["reasoning_mode"]
            or not body.get("messages") or any(set(m) != {"role", "content"}
                or m["role"] not in (("system", "user", "assistant") if allow_system else ("user", "assistant"))
                or not isinstance(m["content"], str)
                for m in body["messages"])):
        raise ValueError("local count request mismatch")
    key = os.environ.get(config["context"]["credential_env"])
    if not key or not key.strip():
        raise ValueError("local backend credential not configured")
    identity = _local_snapshot(config, key)
    if identity != config["context"]["identity"]:
        raise ValueError("local deployment identity changed")
    settings = config["context"]["counting_settings"]
    base = config["context"]["backend_url"].rstrip("/")
    rendered = _metadata(base + "/apply-template", {"messages": body["messages"],
        "add_generation_prompt": settings["add_generation_prompt"],
        "chat_template_kwargs": settings["chat_template_kwargs"]}, key)["prompt"]
    tokens = _metadata(base + "/tokenize", {"content": rendered,
        "add_special": settings["add_special"], "parse_special": settings["parse_special"]}, key)["tokens"]
    if _local_snapshot(config, key) != identity:
        raise ValueError("local deployment identity changed during counting")
    return local_count_record(body, config, rendered, tokens, identity, output_tokens=output_tokens)


def audit_local_count(record, body, config, *, output_tokens=8192):
    """Offline evidence consistency, not a claim of independently rerunning the tokenizer."""
    validate_local_context(config)
    expected = local_count_record(body, config, record["rendered_prompt"], record["token_ids"],
                                  config["context"]["identity"], output_tokens=output_tokens)
    return record == expected and expected["fits"]


def prompt_usage_check(count, usage):
    actual = usage.get("prompt_tokens")
    valid = type(actual) is int and actual >= 0
    return {"counted_input_tokens": count["input_tokens"], "reported_prompt_tokens": actual,
            "difference": actual - count["input_tokens"] if valid else None,
            "matches": valid and actual == count["input_tokens"]}


def context_planning(config, prompts):
    if local_context(config):
        validate_local_context(config)
        return  # Conditional admission: count each actual request inside GraphRun.call.
    for a, b in prompts:
        messages = [{"role": "user", "content": a}, {"role": "assistant", "content": ""},
                    {"role": "user", "content": b}]
        if not context_bound(messages, config, reserve_answer=8192)["fits"]:
            raise ValueError("planning bound exceeds context; stop before generation")


def provider_reasoning(data, profile=None):
    """Together can return either alias; never silently discard a conflicting one."""
    message = data.get("choices", [{}])[0].get("message", {})
    text = message.get("reasoning_content")
    if profile in ("gemma_31b_together", "deepseek_openrouter"):
        other = message.get("reasoning")
        if any(v is not None and not isinstance(v, str) for v in (text, other)):
            raise ValueError("unsupported Together reasoning channel type")
        if text is not None and other is not None and text != other:
            raise ValueError("conflicting Together reasoning channels")
        return text if text is not None else other
    return text


def hosted_semantics(config, mode):
    """Validate operator-supplied exact-model provenance, not its truth remotely."""
    evidence = config["effective"].get("hosted_evidence", {})
    fields = {k: v for k, v in intended_settings(config["profile"], mode, 0).items()
              if k in ("reasoning", "reasoning_effort")}
    if (evidence.get("policy") != HOSTED_READINESS_POLICY
            or evidence.get("model") != config["model"]
            or evidence.get("endpoint") != config["endpoint"]
            or evidence.get("scope") != "exact_model"
            or evidence.get("request_fields") != fields
            or evidence.get("effect") != ("disables_reasoning_computation" if mode == "off" else "enables_reasoning")
            or not isinstance(evidence.get("source"), str) or not evidence["source"].strip()):
        raise ValueError("exact-model hosted reasoning semantics/provenance required")
    try:
        datetime.date.fromisoformat(evidence["date"])
    except (ValueError, TypeError, KeyError):
        raise ValueError("dated hosted reasoning source required") from None
    return evidence


def reasoning_check(data, mode, effective, profile=None, config=None):
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    recorded = provider_reasoning(data, profile)
    text = recorded or ""
    if not isinstance(text, str):
        raise ValueError("unsupported reasoning channel type")
    # Empty template delimiters are not substantive thought text.
    substantive = re.sub(r"^\s*<\|channel>thought\s*<channel\|>\s*$", "", text)
    substantive = re.sub(r"</?think>|\[/?THINK\]", "", substantive).strip()
    details = data.get("usage", {}).get("completion_tokens_details")
    if details is not None and not isinstance(details, dict):
        raise ValueError("invalid completion token details")
    tokens = (details or {}).get("reasoning_tokens")
    count_known = type(tokens) is int and tokens >= 0
    positive = bool(substantive) or (count_known and tokens > 0)
    if profile in EXPANDED_HOSTED_PROFILES:
        evidence = hosted_semantics(config, mode) if config else {}
        # Check both documented reasoning channels, even outside Together.
        other = message.get("reasoning")
        if other is not None and not isinstance(other, str):
            raise ValueError("unsupported hosted reasoning channel type")
        if isinstance(other, str):
            other = re.sub(r"^\s*<\|channel>thought\s*<channel\|>\s*$", "", other)
            positive |= bool(re.sub(r"</?think>|\[/?THINK\]", "", other).strip())
        contradictory = False
        if profile == "deepseek_openrouter":
            details = message.get("reasoning_details")
            if details is not None and not isinstance(details, list):
                raise ValueError("unsupported OpenRouter reasoning details")
            for item in details or []:
                field = {'reasoning.text': 'text', 'reasoning.summary': 'summary',
                         'reasoning.encrypted': 'data'}.get(item.get('type')) if isinstance(item, dict) else None
                if field is None or not isinstance(item.get(field), str):
                    raise ValueError('unsupported OpenRouter reasoning detail entry')
                positive |= bool(item[field].strip())
        expected = {**evidence.get("request_fields", {}), "reasoning_enabled": mode == "on"}
        for box in (data, data.get("metadata", {})):
            if isinstance(box, dict):
                contradictory |= any(k in box and box[k] != v for k, v in expected.items())
        echo = evidence.get("control_echo")
        if echo is not None:
            if (not isinstance(echo, dict) or not isinstance(echo.get("path"), list)
                    or not echo["path"] or not all(isinstance(k, str) for k in echo["path"])
                    or "expected" not in echo or not echo.get("source")):
                raise ValueError("invalid documented provider control echo")
            value = data
            for key in echo["path"]:
                if not isinstance(value, dict) or key not in value:
                    break
                value = value[key]
            else:
                contradictory |= value != echo["expected"]
        invalid_count = tokens is not None and not count_known
        count_source = evidence.get("reasoning_tokens_source")
        measured = (count_known and tokens == 0 and isinstance(count_source, str)
                    and bool(count_source.strip()))
        accepted = bool(evidence) and not contradictory and not invalid_count and (
            (not positive and (measured or tokens is None)) if mode == "off" else positive)
        basis = (("measured_zero" if measured else "provider_documented_disable")
                 if accepted and mode == "off" else "positive_reasoning" if accepted else None)
        return {"mode_verified": accepted, "reasoning_tokens": tokens,
                "evidence": "true" if positive else "false" if measured else "unknown",
                "control_violation": contradictory or (mode == "off" and positive),
                "verification_basis": basis, "readiness_policy": HOSTED_READINESS_POLICY}
    fallback = (not count_known and "reasoning_content" in message and not substantive
                and effective.get("off_empty_channel_source")
                and effective.get("off_template_verified") is True)
    verified = ((count_known and tokens == 0 and not substantive) or bool(fallback)
                if mode == "off" else positive)
    return {"mode_verified": bool(verified), "reasoning_tokens": tokens,
            "evidence": "true" if positive else "false" if verified else "unknown",
            "control_violation": mode == "off" and positive}


def has_final_content(content):
    """Validate without changing the saved answer text."""
    return isinstance(content, str) and bool(content.strip())


def readiness_identity(config, mode):
    return {"policy": HOSTED_READINESS_POLICY,
            "verification_basis": reasoning_check(config["preflight"]["response"], mode,
                config["effective"], config["profile"], config)["verification_basis"]}


def openrouter_routing(config):
    """A single evidenced backing provider, not a catalogue-wide capability union."""
    effective = config['effective']
    for field in ('provider_slug', 'response_provider', 'routing_source', 'sampling_source'):
        if not isinstance(effective.get(field), str) or not effective[field].strip():
            raise ValueError('OpenRouter requires verified ' + field)
    return {'only': [effective['provider_slug']], 'require_parameters': True, 'allow_fallbacks': False}


def deployment_preflight_request(config, profile, mode, *, preflight_output_tokens=8192):
    """Check non-generation prerequisites; this is NOT preflight acceptance."""
    no_secrets(config)
    required = {"profile", "model_id", "model", "response_model", "model_source", "endpoint",
                "api_version", "supported_request_fields", "seed_supported",
                "effective", "context", "preflight", "pricing"}
    if (set(config) != required or config["profile"] != profile
            or config["model_id"] != EXPANDED_MODELS[profile]):
        raise ValueError("deployment config fields/profile mismatch")
    url = urllib.parse.urlsplit(config["endpoint"])
    if (url.scheme not in ("http", "https") or not url.hostname or url.username
            or url.password or url.query or url.fragment
            or (url.scheme == "http" and url.hostname not in ("localhost", "127.0.0.1", "::1"))):
        raise ValueError("unsafe endpoint; use HTTPS or loopback without credentials")
    if profile == "gemma_e4b" and (config["model"] != MODELS[profile]
                                   or url.hostname not in ("localhost", "127.0.0.1", "::1")):
        raise ValueError("E4B requires the specified local model")
    if profile == "gemma_31b_together" and (
            url.scheme != "https" or url.hostname not in ("api.together.ai", "api.together.xyz")
            or url.path.rstrip("/") != "/v1" or config["model"] != MODELS[profile]
            or config["response_model"] != MODELS[profile]):
        raise ValueError("Together requires its documented endpoint and exact Gemma 31B model")
    if profile == 'deepseek_openrouter' and (
            config['endpoint'].rstrip('/') != 'https://openrouter.ai/api/v1'
            or config['model'] != EXPANDED_MODELS[profile]):
        raise ValueError('OpenRouter requires its exact endpoint and DeepSeek model')
    if type(preflight_output_tokens) is not int or preflight_output_tokens not in (8192, 16384):
        raise ValueError('unsupported preflight allowance')
    if not all(config[k] and isinstance(config[k], str) for k in
               ("model", "response_model", "model_source", "api_version")):
        raise ValueError("exact endpoint model and verification source required")
    if type(config["seed_supported"]) is not bool:
        raise ValueError("seed capability must be verified explicitly")
    settings = intended_settings(profile, mode, 0, config["seed_supported"])
    if not set(settings).issubset(config["supported_request_fields"]):
        raise ValueError("unverified request fields; no silent dropping")
    effective = config["effective"]
    hosted = profile in EXPANDED_HOSTED_PROFILES
    if hosted:
        hosted_semantics(config, mode)
        for key in ("runtime", "template_sha256"):
            source = effective.get("runtime_source" if key == "runtime" else "template_source")
            if effective.get(key) is None and (not isinstance(source, str) or not source.strip()):
                raise ValueError("unavailable hosted " + key + " requires explicit provenance")
        if effective.get("runtime") is not None and (not isinstance(effective["runtime"], str)
                                                       or not effective["runtime"].strip()):
            raise ValueError("invalid hosted runtime metadata")
    if (effective.get("reasoning_mode") != mode or not effective.get("source")
            or (not hosted and not effective.get("runtime"))
            or type(effective.get("max_output_tokens")) is not int
            or effective.get("max_output_tokens", 0) < preflight_output_tokens
            or effective.get("history_truncation") is not False):
        raise ValueError("effective reasoning/output/template/history controls unverified")
    if not (hosted and effective.get("template_sha256") is None) and not re.fullmatch(
            r"[0-9a-f]{64}", effective.get("template_sha256") or ""):
        raise ValueError("template hash must identify the actual effective template")
    for rate in (config["pricing"].get("input_per_million"), config["pricing"].get("output_per_million")):
        if rate is not None and (type(rate) not in (int, float) or not math.isfinite(rate) or rate < 0):
            raise ValueError("invalid price")
    if profile.startswith("gemma"):
        for key, value in {"reasoning_budget": None, "response_length_limit": False,
                           "thinking": mode == "on", "temperature": 1.0,
                           "top_p": 0.95, "top_k": 64, "repeat_penalty": 1.0}.items():
            inapplicable = (hosted and key in ("thinking", "reasoning_budget", "response_length_limit")
                            and key in effective and effective[key] is None)
            if inapplicable:
                reasons = effective.get("app_settings_inapplicable", {})
                if not isinstance(reasons.get(key), str) or not reasons[key].strip():
                    raise ValueError("hosted app-setting applicability reason required: " + key)
            elif key not in effective or effective[key] != value:
                raise ValueError("Gemma effective setting mismatch: " + key)
        if effective.get("min_p_supported") is True:
            if effective.get("min_p") != 0.05:
                raise ValueError("effective Min P must remain .05")
        elif effective.get("min_p_supported") is not False:
            raise ValueError("Min P capability unverified")
        if not effective.get("quantization"):
            raise ValueError("record quantization or explicit unquantized description")
    if profile == "gemma_e4b":
        for key, value in {"quantization": "Q6_K", "eval_batch_size": 512,
                           "physical_batch_size": 256, "parallel": 1,
                           "flash_attention": True, "offload_kv_cache_to_gpu": True,
                           "speculative_decoding": False}.items():
            if effective.get(key) != value:
                raise ValueError("local effective setting mismatch: " + key)
        if config["context"]["tokens"] != 32768:
            raise ValueError("local context target is 32768")
    expected = {"model": config["model"], "messages": [{"role": "user", "content": PREFLIGHT}],
                **intended_settings(profile, mode, 999, config["seed_supported"])}
    expected['max_completion_tokens' if profile == 'sol' else 'max_tokens'] = preflight_output_tokens
    if profile == 'deepseek_openrouter':
        expected['provider'] = openrouter_routing(config)
    return expected


def validate_deployment(config, profile, mode, *, preflight_output_tokens=8192):
    """Require explicit operator evidence; this cannot prove server semantics."""
    expected = deployment_preflight_request(config, profile, mode,
                                           preflight_output_tokens=preflight_output_tokens)
    effective = config['effective']
    hosted = profile in EXPANDED_HOSTED_PROFILES
    pre = config["preflight"]
    if (pre.get("request") != expected or pre.get("http_status") != 200
            or pre.get("network_retries") != [] or not pre.get("source")):
        raise ValueError("fixed preflight request/transport not verified")
    response = pre.get("response", {})
    if preflight_output_tokens == 16384:
        raw = pre.get('response_raw')
        if (not isinstance(raw, str) or json.loads(raw) != response
                or pilot.sha256_text(raw) != pre.get('response_raw_sha256')):
            raise ValueError('16K preflight raw envelope/hash mismatch')
        if (len(response.get('choices', [])) != 1 or response.get('error')
                or response['choices'][0].get('error')
                or response['choices'][0].get('native_finish_reason') in ('length', 'max_tokens')):
            raise ValueError('16K preflight provider failure or truncation')
    if profile == 'deepseek_openrouter' and response.get('provider') != effective['response_provider']:
        raise ValueError('OpenRouter preflight backing provider mismatch')
    choice = response.get("choices", [{}])[0]
    if (response.get("model") != config["response_model"]
            or choice.get("finish_reason") != "stop"
            or not has_final_content(choice.get("message", {}).get("content"))
            or not reasoning_check(response, mode, effective, profile, config)["mode_verified"]):
        raise ValueError("preflight control not verified; answer correctness is not checked")
    if "I have to answer now." in (provider_reasoning(response, profile) or ""):
        raise ValueError("preflight contains a known forced budget-ending message")
    if local_context(config):
        validation = config["context"].get("path_verification", {})
        count = validation.get("preflight_count", {})
        if (not validation.get("source")
                or not isinstance(count, dict)
                or not all(k in count for k in ("rendered_prompt", "token_ids", "input_tokens"))
                or validation.get("preflight_response_sha256") != pilot._canonical_sha256(response)
                or not audit_local_count(count, expected, config, output_tokens=preflight_output_tokens)
                or type(response.get("usage", {}).get("prompt_tokens")) is not int
                or response.get("usage", {}).get("prompt_tokens") != count["input_tokens"]):
            raise ValueError("local counting/generation path not verified against saved preflight")
        bound = count
    else:
        bound = hosted_context_check(expected["messages"], config, output_tokens=preflight_output_tokens)
        if estimated_context(config) and not all(estimate_usage_check(
                bound, response.get("usage", {}))[k] for k in ("within_estimate", "within_advertised_context")):
            raise ValueError("preflight reported usage exceeds context estimate or advertised capacity")
    if hosted:
        usage = response.get("usage", {})
        if (any(not isinstance(effective.get(k), str) or not effective[k].strip()
                for k in ("output_context_source", "no_reasoning_budget_source"))
                or not bound["fits"] or type(usage.get("prompt_tokens")) is not int
                or not 0 <= usage["prompt_tokens"] <= config["context"]["tokens"] - preflight_output_tokens
                or type(usage.get("completion_tokens")) is not int
                or not 0 <= usage["completion_tokens"] <= preflight_output_tokens):
            raise ValueError("hosted output/context/budget evidence required")
    return config


def audit_artifact(artifact):
    """Strict operational checks, separate from unchanged task scores."""
    turns = artifact.get("turns", {})
    identity = artifact.get("identity", {})
    checks = {"identity": artifact.get("identity_sha256") == pilot._canonical_sha256(identity),
              "prompts": True, "responses": True, "links": True,
              "raw_before_parse": True, "transport": True, "controls": True,
              "context": True, "request_match": True}
    checks["identity"] &= (identity.get("protocol") == artifact.get("protocol") == PROTOCOL
                           and identity.get("graph_condition") == artifact.get("level")
                           and identity.get("graph_view_sha256") == [
                               pilot._canonical_sha256(v) for v in artifact.get("graph_views", [])]
                           and identity.get("deployment_sha256") == pilot._canonical_sha256(artifact.get("deployment")))
    checks["identity"] = checks["identity"] and (
        artifact.get("run_id") == pilot._icl_run_id(identity)
        and identity.get("repeat") == artifact.get("repeat")
        and identity.get("git_commit") == artifact.get("env", {}).get("git_commit")
        and identity.get("model") == artifact.get("model", {}).get("model")
        and identity.get("request_settings") == artifact.get("request_settings"))
    for name, other in (("A", "a"), ("B", "b")):
        turn = turns.get(name, {})
        prompt = turn.get("prompt", "")
        raw = turn.get("raw_response")
        checks["prompts"] &= bool(prompt) and pilot.sha256_text(prompt) == turn.get("prompt_sha256") == identity.get(f"prompt_{other}_sha256")
        checks["responses"] &= has_final_content(raw) and pilot.sha256_text(raw) == turn.get("response_sha256")
        events = [e["event"] for e in artifact.get("persistence_events", [])]
        raw_event, parsed_event = f"turn_{other}_raw_saved", "turn_a_complete" if name == "A" else "completed"
        checks["raw_before_parse"] &= raw_event in events and parsed_event in events and events.index(raw_event) < events.index(parsed_event)
        dry = artifact.get("model", {}).get("provider") == "dry-run"
        checks["transport"] &= (turn.get("provider_finish_reason") == ("dry_run" if dry else "stop")
                                 and turn.get("network_retries") == [] and not turn.get("truncated")
                                 and not artifact.get("failure"))
        checks["controls"] &= dry or turn.get("control_check", {}).get("mode_verified") is True
        checks["context"] &= dry or turn.get("context_check", {}).get("fits") is True
        request = turn.get("request_body", {})
        checks["request_match"] &= turn.get("request_sha256") == pilot._canonical_sha256(request)
        expected_messages = [{"role": "user", "content": turns.get("A", {}).get("prompt")}]
        if name == "B":
            expected_messages += [{"role": "assistant", "content": turns.get("A", {}).get("raw_response")},
                                  {"role": "user", "content": prompt}]
        expected = {"model": artifact.get("model", {}).get("model"), "messages": expected_messages,
                    **artifact.get("request_settings", {})}
        checks["request_match"] &= request == expected
        if not dry:
            try:
                # Original provider bytes, not convenience copies, determine operations.
                envelope = json.loads(turn["provider_response_raw"])
                checks["responses"] &= pilot.sha256_text(turn["provider_response_raw"]) == turn.get("provider_response_raw_sha256")
                checks["responses"] &= (envelope == turn.get("provider_response")
                                        and pilot._canonical_sha256(envelope) == turn.get("provider_response_sha256"))
                choice = envelope["choices"][0]
                message = choice["message"]
                usage = envelope.get("usage", {})
                config = artifact["deployment"]
                profile = artifact["model"]["request_profile"]
                reasoning = provider_reasoning(envelope, profile)
                mode = artifact["model"]["reasoning_provenance"]["mode"]
                if profile in HOSTED_PROFILES or local_context(config):
                    validate_deployment(config, profile, mode)
                if profile in HOSTED_PROFILES:
                    checks["identity"] &= identity.get("hosted_readiness") == readiness_identity(config, mode)
                control = reasoning_check(envelope, mode, config["effective"], profile, config)
                copied = {"raw_response": message.get("content"),
                          "provider_finish_reason": choice.get("finish_reason"),
                          "provider_usage": usage, "provider_reasoning": reasoning,
                          "actual_response_model": envelope.get("model"),
                          "system_fingerprint": envelope.get("system_fingerprint"),
                          "truncated": choice.get("finish_reason") == "length",
                          "control_check": control, "reasoning_evidence": control["evidence"],
                          "reasoning_control_violation": control["control_violation"]}
                checks["responses"] &= all(key in turn and turn[key] == value for key, value in copied.items())
                checks["transport"] &= (turn.get("http_status") == 200
                                        and has_final_content(message.get("content"))
                                        and choice.get("finish_reason") == "stop"
                                        and type(usage.get("completion_tokens")) is int
                                        and 0 <= usage["completion_tokens"] <= 8192
                                        and type(usage.get("prompt_tokens")) is int
                                        and usage["prompt_tokens"] >= 0
                                        and "I have to answer now." not in (reasoning or ""))
                checks["controls"] &= (control["mode_verified"]
                                       and envelope.get("model") == config["response_model"])
                if local_context(config):
                    count = turn["context_check"]
                    expected_usage = prompt_usage_check(count, usage)
                    checks["context"] &= (audit_local_count(count, request, config)
                                          and turn.get("prompt_usage_check") == expected_usage
                                          and expected_usage["matches"])
                else:
                    checks["context"] &= context_bound(expected_messages, config)["fits"]
                checks["context"] &= (type(usage.get("prompt_tokens")) is int
                                      and 0 <= usage["prompt_tokens"] <= config["context"]["tokens"] - 8192)
                checks["request_match"] &= artifact["request_settings"] == intended_settings(
                    artifact["model"]["request_profile"], artifact["model"]["reasoning_provenance"]["mode"],
                    artifact["model"]["sampling_seed"], config["seed_supported"])
            except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                checks["responses"] = False
    checks["links"] = bool(turns.get("A", {}).get("response_sha256")) and turns.get("B", {}).get("previous_response_sha256") == turns.get("A", {}).get("response_sha256")
    return checks


def on_repeats(off_artifacts):
    """Use all three OFF repeats; never select just failed answers for ON."""
    if len(off_artifacts) != 3 or {a.get("repeat") for a in off_artifacts} != {1, 2, 3}:
        raise ValueError("need all three distinct OFF repeats")
    signatures = {(a["level"], a["model"]["model"], a["protocol"]) for a in off_artifacts}
    if len(signatures) != 1 or any(a["model"]["reasoning_provenance"]["mode"] != "off"
                                 or not all(audit_artifact(a).values()) for a in off_artifacts):
        raise ValueError("OFF operational/matching checks must pass before selecting ON")
    return [1, 2, 3] if any(a["turns"][t]["scored"]["correct"] is not True
                            for a in off_artifacts for t in ("A", "B")) else []


def matched_off(reference, config, condition, prompts):
    artifacts = [json.loads(p.read_text()) for p in sorted(Path(reference).glob("*.json"))
                 if p.name != "summary.json"]
    selected = on_repeats(artifacts)
    treatment_fields = {"reasoning_mode", "thinking", "template_sha256", "template_source",
                        "off_template_verified", "off_empty_channel_source", "source", "hosted_evidence"}
    for artifact in artifacts:
        old = artifact.get("deployment") or {}
        if (artifact["model"]["provider"] != "openai" or artifact["level"] != condition
                or artifact["env"]["git_commit"] != pilot.git_head()
                or any(old.get(k) != config[k] for k in ("profile", "model_id", "model", "response_model",
                                                       "endpoint", "api_version", "seed_supported"))
                or [artifact["turns"][t]["prompt"] for t in ("A", "B")] != prompts
                or old.get("context", {}).get("tokens") != config["context"]["tokens"]
                or {k: v for k, v in old.get("effective", {}).items() if k not in treatment_fields}
                != {k: v for k, v in config["effective"].items() if k not in treatment_fields}):
            raise ValueError("ON must match OFF commit, model, task and all non-reasoning controls")
    return selected


class GraphRun:
    """New-protocol adapter for the existing two-turn persistence and scorer."""

    def __init__(self, args, views, prompts, seed, config, all_prompts):
        self.args, self.config = args, config
        self.prompts = prompts
        supported = config["seed_supported"] if config else False
        self.settings = intended_settings(args.request_profile, args.reasoning_mode, seed, supported)
        self.sampling = {"sampling_seed": seed, "sampling_seed_status":
                         "not_applied_dry_run" if args.provider == "dry-run" else
                         "supported" if supported else "unsupported",
                         "sampling_seed_status_source": "deployment_profile"}
        self.reasoning = {"mode": args.reasoning_mode, "request_fields": {
            k: v for k, v in self.settings.items() if k in ("reasoning", "reasoning_effort")},
            "status": "not_applied_dry_run" if config is None else "operator_evidence_checked",
            "semantics_verified_by_runner": False}
        self.identity_fields = {"protocol": PROTOCOL, "graph_condition": args.graph_condition,
            "graph_view_sha256": [pilot._canonical_sha256(v["graph"]) for v in views],
            "all_prompt_sha256": {c: [pilot.sha256_text(p) for p in ps] for c, ps in all_prompts.items()},
            "deployment_sha256": pilot._canonical_sha256(config), "request_profile": args.request_profile,
            "request_settings": self.settings,
            "temperature": self.settings.get("temperature"), "max_tokens": 8192}
        if config is not None and args.request_profile in HOSTED_PROFILES:
            self.identity_fields["hosted_readiness"] = readiness_identity(config, args.reasoning_mode)
        model = {"provider": args.provider, "model": args.model, **self.sampling,
                 "request_profile": args.request_profile, "max_tokens": 8192,
                 "reasoning_provenance": self.reasoning,
                 "sampling_defaults": "unspecified" if args.request_profile == "sol" else None}
        self.artifact_fields = {"model": model, "request_settings": self.settings,
                               "deployment": config, "graph_views": [v["graph"] for v in views]}
        a, estimates = reference_answer(views[0])
        b, _ = reference_answer(views[1], estimates)
        self.dry_answers = {"A": a, "B": b}

    def call(self, messages, name, artifact, path):
        body = {"model": self.args.model, "messages": messages, **self.settings}
        turn = artifact["turns"][name]
        turn["request_body"] = body
        turn["request_sha256"] = pilot._canonical_sha256(body)
        if self.config is not None:
            if local_context(self.config):
                try:
                    turn["context_check"] = count_local_request(body, self.config)
                except Exception as exc:
                    artifact["failure"] = {"type": "ContextCounting", "turn": name,
                                           "cause": type(exc).__name__, "network_retries": []}
                    artifact["state"] = "incomplete"
                    pilot._write_json_atomic(path, artifact)
                    raise RuntimeError("local context counting failed; saved without generation or retry") from None
            else:
                turn["context_check"] = context_bound(messages, self.config)
            if not turn["context_check"]["fits"]:
                artifact["failure"] = {"type": "ContextBound", "turn": name, "network_retries": []}
                artifact["state"] = "incomplete"
                pilot._write_json_atomic(path, artifact)
                raise RuntimeError("actual full history does not fit; no truncation or call")
        pilot._write_json_atomic(path, artifact)
        if self.args.provider == "dry-run":
            return pilot.dispatch_icl(self.args, messages, self.sampling, self.reasoning,
                                      dry_text=self.dry_answers[name])
        endpoint = self.config["endpoint"].rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        key = os.environ.get("OPENAI_API_KEY")
        if key:
            headers["Authorization"] = "Bearer " + key
        elif urllib.parse.urlsplit(endpoint).hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("OPENAI_API_KEY required for hosted endpoint")
        request = urllib.request.Request(endpoint, data=json.dumps(body).encode(), headers=headers)
        start = time.monotonic()
        try:
            # No retry loop and no redirects/fallback to another deployment.
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=self.args.timeout) as response:
                raw = response.read().decode("utf-8")
                status = response.status
            no_secrets(raw)
            turn.update(http_status=status, provider_response_raw=raw,
                        provider_response_raw_sha256=pilot.sha256_text(raw),
                        elapsed_s=time.monotonic() - start)
            pilot._write_json_atomic(path, artifact)
            data = json.loads(raw)
            no_secrets(data)
            turn.update(provider_response=data, provider_response_sha256=pilot._canonical_sha256(data))
            pilot._write_json_atomic(path, artifact)
            choice = data["choices"][0]
            message = choice["message"]
            control = reasoning_check(data, self.args.reasoning_mode, self.config["effective"], self.args.request_profile, self.config)
            turn["control_check"] = control
            turn["actual_response_model"] = data.get("model")
            if data.get("model") != self.config["response_model"]:
                control["mode_verified"] = False
                turn["deployment_mismatch"] = True
            usage = data.get("usage", {})
            pricing = self.config["pricing"]
            if pricing.get("input_per_million") is not None and pricing.get("output_per_million") is not None:
                if all(type(usage.get(k)) is int for k in ("prompt_tokens", "completion_tokens")):
                    turn["cost"] = {"status": "estimated", "currency": "USD", "source": pricing.get("source"),
                                    "amount": (usage["prompt_tokens"] * pricing["input_per_million"]
                                               + usage["completion_tokens"] * pricing["output_per_million"]) / 1e6,
                                    "assumption": "uncached input and all completion tokens at supplied rates"}
            prompt_tokens = usage.get("prompt_tokens")
            if local_context(self.config):
                turn["prompt_usage_check"] = prompt_usage_check(turn["context_check"], usage)
            if type(prompt_tokens) is int and prompt_tokens + 8192 > self.config["context"]["tokens"]:
                if not local_context(self.config):
                    turn["context_check"]["fits"] = False
            pilot._write_json_atomic(path, artifact)
            return {"text": message.get("content") or "", "usage": usage,
                    "finish_reason": choice.get("finish_reason"),
                    "truncated": choice.get("finish_reason") == "length",
                    "reasoning": provider_reasoning(data, self.args.request_profile),
                    "reasoning_evidence": control["evidence"],
                    "reasoning_control_violation": control["control_violation"],
                    "system_fingerprint": data.get("system_fingerprint"), "network_retries": []}
        except Exception as exc:
            # Exception text/headers may contain credentials or private URLs.
            artifact["failure"] = {"type": type(exc).__name__, "turn": name,
                                   "http_status": getattr(exc, "code", None),
                                   "network_retries": [], "elapsed_s": time.monotonic() - start}
            if isinstance(exc, urllib.error.HTTPError):
                error_body = exc.read().decode("utf-8", errors="replace")
                try:
                    no_secrets(error_body)
                    turn.update(http_status=exc.code, provider_response_raw=error_body)
                    turn["provider_response_raw_sha256"] = pilot.sha256_text(error_body)
                except ValueError:
                    artifact["failure"]["sensitive_response_withheld"] = True
            pilot._write_json_atomic(path, artifact)
            raise RuntimeError("provider failure saved; no retry; " + type(exc).__name__) from None

    def check_saved_turn(self, artifact, path, name):
        turn = artifact["turns"][name]
        invalid_final = not has_final_content(turn.get("raw_response"))
        if self.args.provider == "dry-run" and not invalid_final:
            return
        if self.args.request_profile in HOSTED_PROFILES:
            envelope = json.loads(turn["provider_response_raw"])
            checked = reasoning_check(envelope, self.args.reasoning_mode, self.config["effective"],
                                      self.args.request_profile, self.config)
            invalid_final |= checked != turn["control_check"] or not checked["mode_verified"]
        usage = turn["provider_usage"]
        if (invalid_final or turn["http_status"] != 200 or turn["provider_finish_reason"] != "stop"
                or not turn["control_check"]["mode_verified"]
                or not turn["context_check"]["fits"]
                or (local_context(self.config) and not turn.get("prompt_usage_check", {}).get("matches"))
                or type(usage.get("completion_tokens")) is not int
                or not 0 <= usage["completion_tokens"] <= 8192
                or type(usage.get("prompt_tokens")) is not int
                or usage["prompt_tokens"] < 0
                or "I have to answer now." in (turn.get("provider_reasoning") or "")):
            artifact["failure"] = {"type": "OperationalCheck", "turn": name, "network_retries": []}
            pilot._write_json_atomic(path, artifact)
            raise RuntimeError("returned response saved; operational failure pauses execution without retry")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def run_suite(sc, args, outdir):
    if args.graph_condition not in CONDITIONS or args.request_profile not in MODELS:
        raise ValueError("explicit --graph-condition and --request-profile are required")
    if args.mode != "det" or args.pilot_type != "passive" or args.repeats != 3 or args.sampling_seeds != [0, 1, 2]:
        raise ValueError("requires passive det mode, three repeats and seeds 0 1 2")
    if args.max_tokens != 8192 or args.reasoning_mode not in ("off", "on"):
        raise ValueError("requires max-tokens 8192 and explicit off/on")
    if args.reasoning_control_json or args.reasoning_control_source:
        raise ValueError("graph protocol uses reviewed profile controls, not arbitrary request overrides")
    if args.provider not in ("dry-run", "openai"):
        raise ValueError("graph profiles use explicit OpenAI-compatible endpoints only")
    if (args.temperature != 0 or args.top_p is not None or args.top_k is not None
            or args.sampling_seed_support != "auto"):
        raise ValueError("sampling is fixed by --request-profile; omit legacy sampling flags")
    if getattr(args, "off_reference", None) and args.reasoning_mode != "on":
        raise ValueError("--off-reference is only for conditional ON")
    if Path(outdir).exists():
        raise ValueError("output directory already exists; no automatic resume or overwrite")
    record, view, variants, prompts = prepare(sc)
    config = None
    if args.provider != "dry-run":
        if pilot._git_dirty():
            raise ValueError("real runs require a clean, frozen implementation commit")
        if not args.deployment_config:
            raise ValueError("missing --deployment-config with verified endpoint/context/preflight evidence")
        config = json.loads(Path(args.deployment_config).read_text())
        if args.request_profile == "gemma_e4b" and not local_context(config):
            raise ValueError("local E4B requires actual-request tokenizer counting")
        validate_deployment(config, args.request_profile, args.reasoning_mode)
        if args.model != config["model"] or args.base_url.rstrip("/") != config["endpoint"].rstrip("/"):
            raise ValueError("CLI endpoint/model must exactly match deployment config")
        context_planning(config, prompts.values())
        if args.reasoning_mode == "on":
            if not getattr(args, "off_reference", None):
                raise ValueError("conditional ON requires --off-reference")
            if not matched_off(args.off_reference, config, args.graph_condition, prompts[args.graph_condition]):
                print("OFF was completely correct in all three repeats; ON skipped, no calls")
                return []
    elif args.deployment_config:
        raise ValueError("dry-run must not pretend deployment controls were applied")
    Path(outdir).mkdir(parents=True, exist_ok=False)
    results = []
    try:
        for repeat, seed in enumerate(args.sampling_seeds, 1):
            extension = GraphRun(args, variants[args.graph_condition], prompts[args.graph_condition], seed, config, prompts)
            artifact, path, _ = pilot.run_icl_two_response_once(
                record, view, sc, True, args, args.graph_condition, repeat, seed, outdir, extension)
            results.append({"path": path, "run_id": artifact["run_id"]})
            print(artifact["run_id"] + ": " + artifact["state"])
            if not all(audit_artifact(artifact).values()):
                raise RuntimeError("operational check failed; attempt preserved, no retry")
    finally:
        # Include an initialized/partial attempt in the failure summary.
        results = [{"path": str(path)} for path in sorted(Path(outdir).glob("*.json"))
                   if path.name != "summary.json"]
        summary, _ = pilot.write_icl_summary(outdir, results, PROTOCOL, (args.graph_condition,), audit_artifact)
    print("operational gate: " + ("PASS" if summary["operational_gate_pass"] else "FAIL"))
    return results
