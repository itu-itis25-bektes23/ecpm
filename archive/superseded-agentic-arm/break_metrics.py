"""Metrics for "test the break, not just the map".

Input: step records in the contract from agent_loop.py, from any harness
(scripted, LangGraph, or Christian's agent, once his LiveStep dumps the
same fields). All metrics are behavioral. Nothing here asks the model
what it believes. Belief records are analyzed separately.

Definitions (also in NOTES.md):
  broken-link usage   of the visits to the break node in a phase, the
                      fraction where the broken action was chosen
  replays             total attempts on the broken pair after the change
  drops before switch DROPs observed on the broken pair before the agent
                      first chooses a different action at that node after
                      the change (None if it never switches)
  adaptation latency  attempts from the first post-change DROP on the
                      broken pair until the goal is next reached (None if
                      the goal is never reached after that DROP)
  coverage            distinct (node, action) pairs attempted, out of all
                      legal pairs
"""

from __future__ import annotations

import json


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def steps_only(records):
    return [r for r in records if r.get("type") != "belief"]


def episode_costs(records, phase):
    out = {}
    for r in steps_only(records):
        if r["phase"] == phase:
            out[r["episode"]] = max(out.get(r["episode"], 0), r["cost"])
    return [out[e] for e in sorted(out)]


def reached_goal(records, phase, goal):
    done = {}
    for r in steps_only(records):
        if r["phase"] == phase:
            done[r["episode"]] = done.get(r["episode"], False) or (
                r["next_node"] == goal)
    return [done[e] for e in sorted(done)]


def broken_link_usage(records, break_pair, phase):
    u, a = break_pair
    visits = [r for r in steps_only(records)
              if r["phase"] == phase and r["node"] == u]
    if not visits:
        return None
    return sum(1 for r in visits if r["action"] == a) / len(visits)


def replays_through_break(records, break_pair):
    u, a = break_pair
    return sum(1 for r in steps_only(records)
               if r["phase"] == "post" and r["node"] == u and r["action"] == a)


def drops_before_switch(records, break_pair):
    u, a = break_pair
    drops = 0
    for r in steps_only(records):
        if r["phase"] != "post" or r["node"] != u:
            continue
        if r["action"] == a:
            if r["status"] == "DROP":
                drops += 1
        else:
            return drops
    return None


def adaptation_latency(records, break_pair, goal):
    u, a = break_pair
    first_drop_t = None
    for r in steps_only(records):
        if (r["phase"] == "post" and r["node"] == u and r["action"] == a
                and r["status"] == "DROP"):
            first_drop_t = r["t"]
            break
    if first_drop_t is None:
        return None
    for r in steps_only(records):
        if r["t"] >= first_drop_t and r["next_node"] == goal:
            return r["t"] - first_drop_t + 1
    return None


def coverage(records, legal_pairs):
    tried = {(r["node"], r["action"]) for r in steps_only(records)}
    return len(tried & set(legal_pairs)), len(legal_pairs)


def knowing_vs_doing(localized_correctly, records, break_pair,
                     usage_threshold=0.0):
    """Sruthi's 2x2. Knowing: did the probe name the right broken pair.
    Doing: is post-change broken-link usage at or below the threshold in
    the final post episode (the agent stopped using the dead link)."""
    u, a = break_pair
    post = [r for r in steps_only(records) if r["phase"] == "post"]
    last_ep = max((r["episode"] for r in post), default=None)
    final = [r for r in post if r["episode"] == last_ep and r["node"] == u]
    if final:
        usage_final = sum(1 for r in final if r["action"] == a) / len(final)
        acts = usage_final <= usage_threshold
    else:
        acts = True  # never even visits the break node in the last episode
    know = bool(localized_correctly)
    label = {(True, True): "knows and acts",
             (True, False): "knows, does not act",
             (False, True): "acts, does not know",
             (False, False): "neither"}[(know, acts)]
    return {"knows": know, "acts": acts, "box": label}


def summarize(records, break_pair, goal, oracle_pre, oracle_post,
              legal_pairs):
    pre_costs = episode_costs(records, "pre")
    post_costs = episode_costs(records, "post")
    cov = coverage(records, legal_pairs)
    return {
        "pre_episode_costs": pre_costs,
        "pre_reached_goal": reached_goal(records, "pre", goal),
        "pre_regret": [c - oracle_pre for c in pre_costs],
        "post_episode_costs": post_costs,
        "post_reached_goal": reached_goal(records, "post", goal),
        "post_regret": [c - oracle_post for c in post_costs],
        "broken_link_usage_pre": broken_link_usage(records, break_pair, "pre"),
        "broken_link_usage_post": broken_link_usage(records, break_pair, "post"),
        "replays_through_break_post": replays_through_break(records, break_pair),
        "drops_before_switch": drops_before_switch(records, break_pair),
        "adaptation_latency": adaptation_latency(records, break_pair, goal),
        "coverage": f"{cov[0]}/{cov[1]}",
    }


def print_report(name, summary):
    print(f"--- {name} ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")


def retry_profile(records, break_pair):
    """How the agent retries the broken pair after the change.

    A visit is a maximal run of consecutive post-change step records at
    the break node. Returns per-visit broken-action attempt counts,
    whether the agent switched action within a visit after a DROP on the
    broken pair, how many later visits attempted the broken pair again
    (returns after leaving), and the probability that the very next
    action after a broken-pair DROP is the broken pair again.
    """
    u, a = break_pair
    post = [r for r in records if r.get("phase") == "post" and "status" in r]
    visits, cur = [], []
    for r in post:
        if r["node"] == u:
            cur.append(r)
        elif cur:
            visits.append(cur)
            cur = []
    if cur:
        visits.append(cur)
    encounters, switched = [], 0
    for v in visits:
        broken = [r for r in v if r["action"] == a]
        if not broken:
            continue
        encounters.append(len(broken))
        dropped = False
        did_switch = False
        for r in v:
            if r["action"] == a and r["status"] == "DROP":
                dropped = True
            elif dropped and r["action"] != a:
                did_switch = True
        switched += did_switch
    retry_next, drop_next = 0, 0
    for i, r in enumerate(post[:-1]):
        nxt = post[i + 1]
        if (r["node"], r["action"], r["status"]) == (u, a, "DROP") \
                and nxt["node"] == u and nxt["episode"] == r["episode"]:
            drop_next += 1
            retry_next += (nxt["action"] == a)
    return {"encounters": encounters,
            "visits_attempting_break": len(encounters),
            "switched_within_visit": switched,
            "returned_after_leaving": max(0, len(encounters) - 1),
            "p_retry_immediately_after_drop":
                (retry_next / drop_next) if drop_next else None}
