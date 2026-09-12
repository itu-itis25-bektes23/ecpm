"""Azure budget model for the ECPM main run.

Anchored on measured usage, not guesses: the archived Azure run
(runs/2026-08-23_gpt4o_azure_mt4096/) used 5413 prompt tokens and 220
completion tokens for one four-probe single-turn conversation at K=5.
That gives ~600 tokens of fixed boilerplate per probe plus ~5 tokens per
logged event, which is what the scaling below uses.

Usage:
    python3 experiments/azure_budget.py
    python3 experiments/azure_budget.py --budget 100 --in-price 2.5 --out-price 10
"""

import argparse

# Measured anchor: 4 probes, single turn, K=5, F2_shuffled.
ANCHOR_IN, ANCHOR_OUT, ANCHOR_K, ANCHOR_PROBES = 5413, 220, 5, 4

# 75 events per period at K=5 (15 pairs x 5), two periods.
EVENTS_PER_PAIR_PERIOD = 1
N_PAIRS, N_PERIODS = 15, 2
TOKENS_PER_EVENT = 5

_anchor_events = N_PAIRS * ANCHOR_K * N_PERIODS
_anchor_evidence = _anchor_events * TOKENS_PER_EVENT
BOILERPLATE_PER_PROBE = (ANCHOR_IN - _anchor_evidence * ANCHOR_PROBES
                         ) / ANCHOR_PROBES
OUT_PER_PROBE = ANCHOR_OUT / ANCHOR_PROBES


def conv_tokens(k, probes=4, two_turn=False):
    """Input/output tokens for one instance conversation."""
    evidence = N_PAIRS * k * N_PERIODS * TOKENS_PER_EVENT
    n = probes + (2 if two_turn else 0)          # route_pre, belief_pre
    # Two-turn carries turn 1 into turn 2, and turn 1 shows one period.
    mult = 1.6 if two_turn else 1.0
    return (n * (BOILERPLATE_PER_PROBE + evidence) * mult,
            n * OUT_PER_PROBE * (1.5 if two_turn else 1.0))


def agentic_tokens(m0_eps=4, m1_eps=4, steps=25, ctx_budget=12000):
    """Agentic arm: one LLM call per step, context grows to the cap.

    Mean context is modelled as half the cap, which is generous early and
    conservative late; the probes at the end carry the full transcript.
    """
    calls = (m0_eps + m1_eps) * steps
    mean_ctx = ctx_budget * 0.5
    probes_in = 4 * ctx_budget
    return calls * mean_ctx + probes_in, calls * 15 + 4 * OUT_PER_PROBE


def cost(tin, tout, in_price, out_price):
    return tin / 1e6 * in_price + tout / 1e6 * out_price


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", type=float, default=100.0)
    ap.add_argument("--in-price", type=float, default=2.50,
                    help="USD per 1M input tokens (gpt-4o)")
    ap.add_argument("--out-price", type=float, default=10.00,
                    help="USD per 1M output tokens (gpt-4o)")
    ap.add_argument("--samples", type=int, default=3)
    a = ap.parse_args()

    print(f"derived: {BOILERPLATE_PER_PROBE:.0f} boilerplate tokens/probe, "
          f"{TOKENS_PER_EVENT} tokens/event, {OUT_PER_PROBE:.0f} out/probe")
    print(f"prices: ${a.in_price}/1M in, ${a.out_price}/1M out, "
          f"{a.samples} samples per instance\n")

    # Condition x mode cells. degradation is stochastic-only.
    cells_sto = ["no_change", "irrelevant", "silent_break", "hard_removal",
                 "degradation", "redirect"]
    cells_det = ["no_change", "irrelevant", "silent_break", "hard_removal",
                 "redirect"]
    n_cells = len(cells_sto) + len(cells_det)          # 11

    print(f"{'plan':<44}{'instances':>10}{'Mtok in':>10}{'cost':>10}")
    print("-" * 74)

    plans = []
    for label, seeds, k, two_turn in [
        ("ICL single-turn, 3 seeds, K=10", 3, 10, False),
        ("ICL single-turn, 23 seeds, K=10", 23, 10, False),
        ("ICL two-turn, 3 seeds, K=10", 3, 10, True),
        ("ICL two-turn, 3 seeds, K=20", 3, 20, True),
        ("ICL two-turn, 23 seeds, K=10", 23, 10, True),
        ("ICL two-turn, 23 seeds, K=20", 23, 20, True),
    ]:
        inst = seeds * n_cells * a.samples
        ti, to = conv_tokens(k, two_turn=two_turn)
        ti, to = ti * inst, to * inst
        c = cost(ti, to, a.in_price, a.out_price)
        plans.append((label, inst, c))
        print(f"{label:<44}{inst:>10}{ti/1e6:>10.1f}{c:>10.2f}")

    print()
    for label, seeds, eps in [
        ("Agentic, 1 seed, 3 conditions, 4+4 eps", 1, 4),
        ("Agentic, 3 seeds, 6 conditions, 4+4 eps", 3, 4),
        ("Agentic, 3 seeds, 6 conditions, 2+2 eps", 3, 2),
    ]:
        conds = 3 if seeds == 1 else 6
        inst = seeds * conds * a.samples
        ti, to = agentic_tokens(eps, eps)
        ti, to = ti * inst, to * inst
        c = cost(ti, to, a.in_price, a.out_price)
        plans.append((label, inst, c))
        print(f"{label:<44}{inst:>10}{ti/1e6:>10.1f}{c:>10.2f}")

    print()
    print(f"{'recommended package':<44}{'':>10}{'':>10}{'cost':>10}")
    print("-" * 74)
    # Single-turn is kept as a COMPARISON CONDITION on the same seeds and
    # the same K, not as a legacy arm. Run alone, two-turn shows whether a
    # model updates; run as a pair, the difference between them measures
    # how much of any apparent updating was really just planning from
    # period B. That contrast is the paper's second figure, and at ~$8 it
    # is the cheapest claim in the whole budget.
    #
    # The agentic arm gets a deliberately narrow slice: one instance is
    # ~200 LLM calls against a growing context, roughly 100x an ICL
    # conversation. Enough to show the dissociation replicates when
    # evidence is chosen; not enough to estimate a rate.
    pkg = [p for p in plans if p[0] in (
        "ICL two-turn, 23 seeds, K=10",
        "ICL single-turn, 23 seeds, K=10",
        "ICL two-turn, 3 seeds, K=20",
        "Agentic, 1 seed, 3 conditions, 4+4 eps")]
    total = sum(p[2] for p in pkg)
    for label, inst, c in pkg:
        print(f"  {label:<42}{inst:>10}{'':>10}{c:>10.2f}")
    print(f"{'  TOTAL':<44}{'':>10}{'':>10}{total:>10.2f}")
    print(f"{'  headroom against budget':<44}{'':>10}{'':>10}"
          f"{a.budget - total:>10.2f}")
    print()
    print("  Reserve the headroom: the K=5 pilot lost 4 of 4 route answers"
          "\n  to a prompt wording bug, so budget for one reruns cycle.")


if __name__ == "__main__":
    main()
