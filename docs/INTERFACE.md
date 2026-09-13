# Routing-MDP Environment Interface (v2.2) — for prompts, parser, and evaluator

Module: `resource_mdp.py` (stdlib only, Python 3.8+). Schema version **2.1**.
Response parsing/scoring: `ecpm_parser.py` + `parser_fixtures.json` +
`test_ecpm_parser.py` (Section 7 is now FROZEN, not a proposal).
The two example files (`example_deterministic_silent_break.json`,
`example_stochastic_silent_break.json`) are instances of exactly this
schema: seed 7, condition `silent_break`, `matched=True`, `k=5`,
`evidence_seed=0` -- a properly anchored det/sto showcase pair.

v2.1 resolves the six pre-freeze review items (2026-08-19): matched
targets, strict irrelevant control, binary deterministic mode, pure
relabeling obfuscation, distinct score statuses, capped evidence with a
prompt-safe projection, and a frozen response schema. v2.1.1 resolves
the second review round: `matched=True` construction (shared start,
goal, and target across det/sto), strict duplicate-safe preservation
scoring, `0 < B <= k` budget validation, and the first-parseable-object
parser wording.

v2.2 (2026-09-08, PO review of the methodology doc) changes the
interventions and the probe delivery; the §7 answer contract is still
frozen and `single` turn mode reproduces the frozen prompts byte for
byte:

* `irrelevant` now sets U\* to p = 0 in stochastic mode too (a halved
  off-route link is found only 32–69% of the time at K=10, so a kept
  route was ambiguous between "judged irrelevant" and "did not notice").
* `degradation` degrades the shared target T\* (same link the break
  family draws for the seed) instead of its own draw, which collided
  with T\* on 7/23 seeds.
* `run_pilot.py --turn-mode two_turn`: turn 1 shows period A only and
  asks `route_pre` (scored vs the M0 optimum; the evidence-only planning
  baseline) and `belief_pre` (destination + success probability for the
  4 preservation pairs, which include T\*). Turn 2 reveals period B with
  turn 1 in context and asks the four frozen probes; `--reelicit` adds
  `belief_post` and a self-consistency preservation score. Belief
  tolerance is frozen now: destination exact, p within ±0.15
  (stochastic) / exact (deterministic). Parsers/scorers are additive in
  `ecpm_parser.py` (§7 unchanged).

## 1. Handoff table → implementation

| Handoff request | Where it lives |
| --- | --- |
| Paired worlds, exact diff, old/new p | `make_pair(seed, condition, ...)` → `PairedInstance(m0, m1, change, ...)`; M0 is never mutated |
| Deterministic + stochastic, same interface | `deterministic=True` sets `p_range=(1,1)` through the same code path; **topology is identical per seed across modes** |
| Five conditions | `condition ∈ {no_change, irrelevant, degradation, silent_break, hard_removal}` (`degradation` is stochastic-only, see §4) |
| **Matched break target (v2.1)** | `silent_break` and `hard_removal` draw from ONE shared target stream → same link per (seed, mode) |
| **Matched det/sto anchors (v2.1.1)** | `make_pair(..., matched=True)`: shared start, goal, AND intervention target across modes (eligible-set intersection; ~79% of seeds construct; ValueError otherwise) |
| Balanced per-(s,a) pre/post evidence | `paired_evidence(inst, k, evidence_seed)` — ≥ k attempts per listed pair in each world; capped episodes + deterministic resampling (§6) |
| **Prompt-safe projection (v2.1)** | `prompt_view(record, rendering, periods, budget_per_pair)` — the ONLY object a prompt may serialize (§6) |
| Oracle metadata | `PairedInstance.oracle` — pre/post solvability, optimal route/cost, tie info, alternative proper route |
| Reproducibility | all rngs seeded with explicit strings; records are self-describing (a record can be rebuilt from its `seeds`/`params`) |
| Scoring seam | `score_route` (now with status, §7), `route_from_actions`, `broken_link_usage`, `regret`; response parsing in `ecpm_parser.py` |

## 2. Core API (field names to code against)

```python
inst = make_pair(seed, condition, deterministic=False, matched=False,
                 n_nodes=8, extra_edges=6, p_range=(0.6, 0.95),
                 obfuscate=False, degradation_factor=0.5,
                 change_seed=None)
# ValueError: deterministic degradation (undefined in v2.1), or no
# eligible target for the requested condition on this seed.

ev = paired_evidence(inst, k=5, evidence_seed=0, horizon=60,
                     max_episodes=300, max_resamples=4)
record = pair_to_json(inst, ev)          # the full JSON instance (§3)
view = prompt_view(record, rendering="F2_shuffled",
                   periods=("pre", "post"), budget_per_pair=5)
# ValueError unless 0 < budget_per_pair <= k (only B <= k is EXACT);
# budget_per_pair=None returns the full evidence (evaluator-side only).
```

`RoutingMDP` internals the evaluator may touch: unchanged from v2.0
(`.nodes .goal .p .broken .changes .out_edges .optimal .optimal_route
.plan_cost .set_link_prob .break_link .copy`). New helpers:
`forward_distances(mdp, start)` and `edges_off_all_optimal_routes(mdp,
start)` (the v2.1 irrelevant eligibility set). Rollout side unchanged.
Obfuscation now draws names from a separate stream, so `obfuscate=True`
is pure relabeling (identical indexed weighted graph).

## 3. JSON instance — top level

| Field | Content |
| --- | --- |
| `schema_version` | "2.1" |
| `condition`, `deterministic` | condition name; mode flag |
| `seeds`, `params` | full provenance; sufficient to rebuild the instance |
| `nodes`, `goal`, `start` | start = farthest solvable node |
| `legal_actions_pre/post` | model-visible action menus (differ only under `hard_removal`) |
| `world_pre/post` | ground-truth graphs (evaluator-only) |
| `change` | exact diff (§4) |
| `oracle` | metadata bundle (§5) |
| `evidence` | balanced observations + counts (§6) — **evaluator-only in v2.1** |
| `model_visible` | `nodes, start, goal, legal_actions_*` — static prompt fields |
| `prompt_projection` | builder contract: prompts are built with `prompt_view` only |
| `evaluator_only` | `world_*, change, oracle, seeds, params, evidence, counts_*` |

## 4. `change` — the exact diff (localization ground truth)

Format unchanged from v2.0. Condition semantics (v2.1):

| condition | target | effect | guarantees |
| --- | --- | --- | --- |
| `no_change` | — | M1 = M0 | false-positive control |
| `irrelevant` | random edge U\* off **every** optimal route | p → 0 in **both** modes (v2.2; was p × 0.5 in stochastic) | optimal route AND `route_unique` provably unchanged; irrelevant and silent_break differ only in relevance |
| `degradation` | the shared on-route target T\* (same link as silent_break / hard_removal for the seed, v2.2) | p × `degradation_factor` (min 0.05) | **stochastic-only**; deterministic raises ValueError |
| `silent_break` | random eligible ON-route edge (shared stream) | p → 0, still listed | goal stays reachable → forces replanning |
| `hard_removal` | **same target as silent_break** per (seed, mode) | edge leaves the action set | detection trivial by menu diff — the easier control |

Eligibility for breaks = `breakable_route_links` (reachability preserved);
for `irrelevant` = `edges_off_all_optimal_routes`. `make_pair` raises
ValueError on seeds with an empty eligible set.

**Matched mode (v2.1.1).** `matched=True` anchors the det/sto
comparison: the start is chosen on the deterministic sibling world
(identical across modes, since reachability is purely topological), the
target stream drops the mode token, and the eligible set is intersected
across both sibling worlds -- det and sto instances of a seed then share
start, goal, and intervention target (`params.matched` records the
flag). Target sharing covers `irrelevant`/`silent_break`/`hard_removal`;
`degradation` is start-matched only. Yield: 794/1000 seeds construct;
among them start and target agree 100%, and 652 also share the
pre-change optimal route (the residual route difference IS the
uncertainty manipulation and is reported, not hidden).

## 5. `oracle` — evaluator ground truth

Unchanged from v2.0. Reminder: any `valid_finite` route with regret == 0
is scored optimal; exact equality with `optimal_route` is NOT required,
and `route_unique` stays diagnostic.

## 6. `evidence` and the prompt budget — what the model sees

`pre`/`post` carry the SAME event set in five renderings (`F1_log`,
`F2_ordered`, `F2_shuffled`, `F3_stats`, `F4_narrative`), plus
`counts_pre/post`, `min_attempts_pre/post`, `episodes_pre/post`,
`k_per_pair`, `evidence_seed`. New v2.1 fields: `evidence_seed_effective`,
`resamples`, `horizon`, `max_episodes`.

**Budget rule (v2.1).** Collection is capped at `max_episodes` (default
300) per world; on failure it deterministically resamples with a derived
seed up to `max_resamples` times, then raises. `k` remains a minimum-
coverage gate, NOT the prompt budget.

**Prompt contract (v2.1).** The raw `evidence` object is evaluator-only:
it contains `counts_*` keyed by true edges and all five renderings.
Prompts are built exclusively with

```python
prompt_view(record, rendering, periods, budget_per_pair=5, budget_seed=0)
```

which returns ONE rendering of the selected period(s), the matching
action menus, `nodes/start/goal`, and realized sizes (`events`,
`episodes`, `chars` per period) — never counts, worlds, change, oracle,
or seeds. `budget_per_pair` must satisfy `0 < B <= k` (ValueError
otherwise): the coverage guarantee is only a minimum of k attempts per
pair, so only `B <= k` is EXACT; `budget_per_pair=None` returns the
full, unsubsampled evidence for evaluator-side use. Events are
subsampled to an EXACT per-pair budget (uniform per pair, outcome-blind,
deterministic given `budget_seed`); the same
subsampled event set underlies every rendering choice, so the
format comparison stays matched, and the silently broken pair still
contributes exactly `budget_per_pair` all-drop observations post-change.
Original `t` values are preserved, so elisions in `F1_log`/`F4` appear as
t-jumps inside an episode. Log `realized` for every prompt.

## 7. Response schema, parser, and scoring — FROZEN

Implementation: `ecpm_parser.py` (stdlib; consumes raw model text + the
JSON record). Acceptance cases: `parser_fixtures.json` (format level) and
`test_ecpm_parser.py` (instance level). One JSON object per probe; the
FIRST balanced `{...}` block that parses as JSON is used -- earlier
non-parsing brace blocks, surrounding prose, and code fences are
skipped; unknown extra fields inside the object are ignored.

1. **Detection** — `{"changed": true|false}`. Truth:
   `condition != "no_change"` (`irrelevant` counts as changed).
2. **Localization** — `{"node": "C", "action": "a2"}`. Truth:
   `change.edge.from` + `change.action`.
3. **Preservation** — `{"pairs": [{"node", "action", "changed"}, ...]}`
   (optional numeric `"p"` per pair recorded). Truth: a pair changed iff
   it is the intervention target. **Strict scoring (v2.1.1):** the
   evaluator always supplies the queried pairs, and the response must
   answer every queried pair exactly once — any unqueried pair →
   `unknown_pair`, any repeat → `duplicate_pair`, any missing pair →
   `incomplete_response`. Accuracy (denominator = all queried pairs) is
   reported only under `ok`, so omitting hard pairs or padding the
   denominator is impossible.
4. **Adaptation** — `{"route": [{"node", "action"}, ...]}`, the canonical
   representation: explicit state-action steps, ≤ 32 steps, starting at
   `start`; step i+1's node must equal the destination implied by step i
   (destinations resolved on the PRE world, so a removed edge translates
   and then scores `illegal_action` on the POST world).

Statuses:

| Layer | Statuses |
| --- | --- |
| parse | `ok`, `malformed_json`, `invalid_object`, `too_long` |
| preservation | `unknown_pair`, `duplicate_pair`, `incomplete_response` |
| route walk | `unknown_reference`, `discontinuous_route`, `incomplete_route` |
| execution (POST world) | `valid_finite` (cost + regret), `silent_broken_edge` (legal route over a listed p = 0 link), `illegal_action` (hop not in the action set) |

`score_route` returns the same execution statuses plus `invalid_route`
for empty/mis-anchored node paths; `valid` (bool) is kept for v2.0
compatibility. A `valid_finite` route with regret == 0 → `is_optimal`.

## 8. Invariants the tests enforce

`test_resource_mdp.py` (v2.0 battery, all kept) plus v2.1: silent break
and hard removal share the target per (seed, mode); the irrelevant target
is off every optimal route, preserves `route_unique`, and keeps the
deterministic post world binary; deterministic degradation raises;
obfuscation preserves the indexed weighted graph; score statuses are
distinct; `prompt_view` leaks nothing evaluator-only, enforces the exact
per-pair budget, and reproduces the stored renderings at unbounded
budget and rejects `B > k`; matched mode shares start/goal/target
across modes and its records rebuild; the shipped seed-7 examples
(matched) regenerate exactly. `test_ecpm_parser.py` covers the frozen
Section 7 contract end to end, including the strict preservation
statuses.

Run: `python3 test_resource_mdp.py && python3 test_ecpm_parser.py`
Audit: `python3 ecpm_pre_freeze_audit.py` (Pavlos, round 1),
`python3 adversarial_review.py [seeds]` (Pavlos, round 2; committed with
v2.1.1 adaptations), and `python3 ecpm_reply_verification.py`
(regression numbers; against v2.0 it reproduced the review findings).

## 9. Additive ICL two-response protocol

`run_pilot.py --protocol icl_two_response_v1` is additive. It does not alter
the schema 2.1 single-probe parsers, scorers, prompts, or active-exploration
path.

Each run has exactly two responses in one conversation. Turn A contains only
Period A and returns `pairs` plus `route`. Turn B retains that exchange,
reveals only Period B with the statement that it may or may not differ, and
returns `changed`, nullable `changed_pair`, `pairs`, and `route`. Both `pairs`
arrays must cover the same ordered five queried pairs exactly once.

Turn A pair fields are `node`, `action`, `available`, `destination`, and
`p_success`. Turn B adds the boolean `changed`. An unavailable action requires
`available=false`, `destination=null`, and `p_success=null`; a listed silent
break remains available with probability zero. `changed_pair` is null when
`changed` is false. The prompt never identifies pair roles or states that a
change occurred.

The additive parsers `parse_icl_turn_a` and `parse_icl_turn_b` parse beliefs
and routes independently. Belief statuses include `unknown_pair`,
`duplicate_pair`, `missing_pair`, `invalid_unavailable`, and `out_of_range`.
Route truth scoring reuses `score_route_pre` and `score_adaptation` unchanged.
`route_inconsistent` and `route_unresolvable` are diagnostic comparisons with
reported beliefs and do not alter route parsing or truth-side grading.

Reported metrics include response well-formedness, correctness over all
responses, correctness conditional on well-formedness, detection, nullable
exact localization, availability accuracy, destination accuracy over truly
available pairs, probability MAE against both visible frequencies and
evaluator truth, primary self-consistency preservation for the four controls,
secondary truth-based preservation, and the existing route
validity/cost/regret/optimality fields. Period B also records
intervention-target route use and conflict with the reported target belief.

Artifacts are keyed by a stable `run_id`. Raw responses are persisted before
parsing; prompts and responses carry SHA-256 hashes, Turn B links to the Turn A
response hash, and provider usage, finish reason, truncation, sampling,
reasoning provenance, endpoint/API fingerprint, menus, queried pairs, protocol,
level, and commit are recorded. A deterministic `summary.json` reports the
accuracy-independent operational gate, including completion, response count,
hash linkage, truncation, and reasoning-control violations. Completed runs are
left unchanged on resume; inconsistent partial runs stop with an error.

Sampling seeds are sent only when the endpoint is declared to support them;
otherwise artifacts record `sampling_seed_status: unsupported` and identify
the calls as repeated outputs. Optional `top_p` and `top_k` values are sent only
when configured; both values are recorded in artifacts and run identity, with
`null` representing the provider default. A real `off` or `on` reasoning
condition requires an explicit provider-specific request object and a short
operator-supplied verification source. The exact control is recorded without
claiming that the runner verifies provider semantics. `unspecified` sends no
reasoning control, and dry runs record that no control was applied or verified.
