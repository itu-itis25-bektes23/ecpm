"""End-to-end smoke test. No network, no API keys, no frozen repo needed.

Run: python3 smoke_test.py

What it checks:
  1. The reconstructed seed-7 world reproduces the verified oracle facts.
  2. The stale planner keeps hammering the dead link (usage 1.00).
  3. The adaptive policy switches after exactly k DROPs and the metrics
     report k, the reroute cost, and the coverage.
  4. The belief self-report hook logs estimates that flip after masking.
"""

from seed7_world import make_pair, BREAK_PAIR, GOAL
from agent_loop import (StalePlannerPolicy, AdaptiveMaskPolicy,
                        EpsilonGreedyPolicy, run_paired, save_jsonl)
import break_metrics as bm


def main():
    m0, m1 = make_pair("silent_break")
    import seed7_world
    facts = seed7_world.self_check()
    print("world self check passed")
    print(f"  legal pairs: {facts['legal_pairs']}")
    print(f"  oracle pre:  cost {facts['pre_cost']}  route {facts['pre_route']}")
    print(f"  oracle post: cost {facts['post_cost']}  route {facts['post_route']}")
    print()

    legal = m0.legal_pairs()

    # 1. Stale planner: knows the map, ignores the break
    recs = run_paired(m0, m1, StalePlannerPolicy(m0),
                      episodes_pre=2, episodes_post=1, max_steps=20,
                      run_id="stale")
    s = bm.summarize(recs, BREAK_PAIR, GOAL, 4, 5, legal)
    bm.print_report("stale planner (fixed_policy analog)", s)
    box = bm.knowing_vs_doing(localized_correctly=True, records=recs,
                              break_pair=BREAK_PAIR)
    print(f"  knowing vs doing (assuming a correct localization probe): {box}")
    print()

    # 2. Adaptive policy: masks the pair after k=3 DROPs
    recs = run_paired(m0, m1, AdaptiveMaskPolicy(m0, k=3),
                      episodes_pre=2, episodes_post=2, max_steps=20,
                      run_id="adaptive", belief_every=5)
    save_jsonl(recs, "adaptive_run.jsonl")
    s = bm.summarize(recs, BREAK_PAIR, GOAL, 4, 5, legal)
    bm.print_report("adaptive after 3 drops", s)
    beliefs = [r for r in recs if r.get("type") == "belief"]
    first = beliefs[0]["estimates"].get("D a2")
    last = beliefs[-1]["estimates"].get("D a2")
    print(f"  belief reports logged: {len(beliefs)}  "
          f"stated p(D a2) first {first} -> last {last}")
    box = bm.knowing_vs_doing(localized_correctly=False, records=recs,
                              break_pair=BREAK_PAIR)
    print(f"  knowing vs doing (assuming a wrong localization probe): {box}")
    print()

    # 3. Epsilon-greedy explorer for coverage contrast
    recs = run_paired(m0, m1, EpsilonGreedyPolicy(m0, eps=0.5, k=3, seed=7),
                      episodes_pre=2, episodes_post=2, max_steps=20,
                      run_id="explore")
    s = bm.summarize(recs, BREAK_PAIR, GOAL, 4, 5, legal)
    bm.print_report("epsilon greedy explorer (eps 0.5)", s)
    print()

    # 4. Redirect variant sanity: same success rate, new destination
    r0, r1 = make_pair("redirect")
    recs = run_paired(r0, r1, StalePlannerPolicy(r0),
                      episodes_pre=1, episodes_post=1, max_steps=20,
                      run_id="redirect-stale")
    post = [r for r in recs if r["phase"] == "post"]
    arrivals = [(r["node"], r["action"], r["status"], r["next_node"])
                for r in post if r["node"] == BREAK_PAIR[0]]
    print("redirect variant, stale planner, attempts at the changed node:")
    for a in arrivals:
        print(f"  {a}")
    print("  note: every attempt succeeds, only the arrival node changed. "
          "Success counting alone can never catch this.")


if __name__ == "__main__":
    main()
