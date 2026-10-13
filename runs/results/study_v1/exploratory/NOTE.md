# Study v1, exploratory round

**Status: exploratory.** Ten seeds (8, 13, 25, 0, 1, 4, 5, 7, 9, 10), both modes, all six changes, all three models. The instruction "When an action keeps failing, consider trying actions or routes you have not tried yet." is either off or placed **in the system prompt for whole episodes**. These numbers guide the confirmatory design and test nothing. `report.md` is the launcher's full report. Acting runs are complete: 1,980 runs.

## Main findings

**1. Repetition holds over whole episodes.** Among task-only runs, in stochastic silent break and degradation, that reach six consecutive failures of the changed link, every run without the instruction chooses the link again: Claude Haiku 5.5 8 of 8, DeepSeek V4.1 Flash 7 of 7, GPT-5.6 Sol 2 of 2. Few runs qualify on ten seeds.

**2. The instruction in the system prompt has no visible effect.**
- **Reaching six failures:** 8, 7 and 2 runs reach six failures both with and without the instruction. The runs that differ are 2, 1 and 1 in each direction.
- **After six failures:** runs with the instruction still choose the link again in 7 of 8, 7 of 7 and 2 of 2 (16 of 17, against 17 of 17 without). These counts were computed from `analysis/acting_runs.csv` with the command below.

In the reuse pilot (`runs/results/pilots/reuse_pilot/`), the same sentence added at the moment of failure lowered re-choosing from 52–80% to 6–29%. Together these suggest that the instruction changes the decision when it arrives with the failure, not when it is given in advance. The two setups differ (single resumed decisions against whole episodes), so this is a contrast between two exploratory results, not a controlled comparison.

**3. The instruction's cost when nothing changes is small.** M1 goal success is unchanged for every model. DeepSeek takes about half a step more in no change (+0.48 steps, 95% interval +0.13 to +0.84); Haiku and Sol show no reliable change.

**4. A complete log reduces retrying (bridge).** At the qualifying decisions, re-choosing with the complete log against with the agent's own log:
- **Claude Haiku 5.5:** 68 against 102 of 154 decisions (17 and 51 decisions change in each direction);
- **GPT-5.6 Sol:** 9 of 9 both ways;
- **DeepSeek V4.1 Flash:** no valid decisions (68 decisions without a valid action in either probe).

**5. Reference agent.** It never chooses the changed link again after six failures, in any cell.

## Open issues

- **Reading-family export:** the three reading processes ended with errors at the final restart, so the reading table in `report.md` is empty. The conversations from 12 October exist. The likely cause is that Sol's reading configuration is pinned to the `openai` provider, which was removed from the account's allowed providers while Sol ran through Azure BYOK. The export can be redone without API calls.
- **Provenance:** the remaining Sol acting runs (13 October, after 10:40) were served through the account owner's Azure deployment (gpt-5.6-sol 2026-07-09, Global Standard) via OpenRouter BYOK. Earlier Sol runs were served by OpenAI. Each run records its provider.

## Implication for the confirmatory design

Testing the instruction in the system prompt would most likely confirm a null. The informative confirmatory test delivers the instruction with the failure, over whole episodes, and measures its cost when nothing changes. The plan (`docs/STUDY_PLAN_v1.md`) is not yet tagged, so this change can be made before the confirmatory round, with this note as its reason.

## Reproducing the counts in finding 2

```
python -c "import csv; R=list(csv.DictReader(open('analysis/acting_runs.csv',encoding='utf-8')))
for m in sorted({r['model'] for r in R}):
  for n in ('False','True'):
    q=[r for r in R if r['model']==m and r['nudge']==n and r['arm']=='task_only' and r['mode']=='sto' and r['scenario'] in ('silent_break','degradation') and r['h4_reached']=='True']
    print(m,'nudge' if n=='True' else 'off', sum(r['h4_chose_again']=='True' for r in q),'/',len(q))"
```
