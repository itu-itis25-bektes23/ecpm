# Agentic arm working notes, sessions of 25/08/26 and 26/08/26

Update 26/08. The frozen repo zip was uploaded and the local
reconstruction was verified against it. All checks pass. Details in the
new verification section below.

## What this package is

Five small files that move three of this week's tasks forward. First, a
tested agent loop and a tested metrics module for the question "does the
model stop using the dead link", which is the break test. Second, a
LangGraph adapter that replaces the Inspect idea for real model runs.
Third, a Colab notebook for experiment E1, in-context learning (ICL)
against finetuning (FT) on matched evidence. Everything runs offline with
zero API calls except the parts that by definition need a model, and
those are clearly flagged.

## Where this fits

The design in the doc's Method flow section (Vocabulary, run_explore_instance,
LiveStep, EpisodeOutcome) came out of the previous working session.
Christian has since implemented a first version on his branch
feature/agentic_exploration and is testing it. Nothing here competes with
that. The metrics module reads step records from any harness, so his
agent can emit the same fields and reuse it unchanged. The LangGraph file
is the reference for the framework switch we agreed on after the 24/08
meeting, since Sruthi noted Inspect is niche and I have used LangChain
and LangGraph before. This package lives in its own repository for now.
The frozen repo is treated as an external dependency reached through
one connector module, frozen.py, and no frozen file is ever copied
here. Whether the two repositories merge later is a team decision that
stays open. Because everything goes through the one connector, a later
merge is a folder move plus one default path.

## Words used

Agent. The language model acting inside a loop, one action per step.
Environment. The eight-node packet-routing world. MDP means Markov
decision process. M0 is the world before the change, M1 after.
Episode. One run from the start node E to the goal node F, or until the
step budget runs out.
DROP. The only failure signal. The packet stays where it was. The model
never sees a broken-link label.
Silent break. The pair (D, a2) stays listed but never succeeds again.
Redirect. Sruthi's change type 6. The pair keeps its success rate but
now leads to a different node.
ICL. In-context learning. The evidence sits in the prompt, weights frozen.
FT. Finetuning. The evidence is trained into the weights with QLoRA,
which means low-rank adapters on a 4-bit quantized model.
Probes. The four frozen questions, detection, localization, preservation,
adaptation, with the frozen answer schemas.

## The loop in one picture

```
            what the model sees              what stays hidden
        +--------------------------+     +------------------------+
        | node: D                  |     | full adjacency         |
        | actions: [a1, a2]        |     | success probabilities  |
        | cost so far: 2, goal: F  |     | the break itself       |
        +--------------------------+     +------------------------+
                    |
                    v
        model replies {"reason": "...", "action": "a2"}
                    |
                    v
        environment answers "OK, arrive B"  or  "DROP, stay D"
                    |
                    v
        one step record is logged, loop repeats until F or budget
```

After a fixed number of M0 episodes the world silently switches to M1.
The same transcript continues, so the model's memory of M0 carries over.

## The files

seed7_world.py. A local reconstruction of the seed-7 deterministic
instance for offline testing. The adjacency, start E, goal F, break on
(D, a2), and both oracle routes were verified against the frozen repo in
the previous session, and self_check() re-verifies them on every run.
Verified on 26/08 against the uploaded frozen repo, all entries and
oracle facts match, see the verification section. Real runs still build
the instance with resource_mdp.make_pair on the frozen commit. This
file is a test harness, not the environment.

agent_loop.py. The framework-free loop plus three scripted policies. All
three are handed the perfect pre-change map on purpose. That is the whole
point of "test the break, not just the map". The map is given, and we
watch whether behavior updates once the map silently stops being true.
The stale planner never updates. The adaptive planner masks a pair after
k DROPs on it. The epsilon-greedy explorer adds randomness for coverage.

break_metrics.py. Reads step records from any harness and computes the
break metrics defined below, plus Sruthi's knowing versus doing table.

langgraph_loop.py. The real-model runner. One shared transcript, one
observation per step, a JSON reply with a short stated reason, retries
on unparseable replies, belief probes and the four frozen probes asked
on a fork of the transcript so probing never contaminates the run.
⚠️ Written but not executed, the machine used today has no package
access. Install langgraph, langchain, langchain-openai, langchain-ollama
and expect one or two small first-run fixes. The dry backend wraps the
tested adaptive policy, so the whole app can be exercised with zero API
calls before any key is used.

icl_vs_ft_matched_evidence.ipynb. Experiment E1 for Colab, described in
its own section below.

smoke_test.py. Runs everything testable end to end. The next section is
its output.

verify_against_frozen.py. Checks seed7_world.py against a checkout of
the frozen repo, entry by entry, plus regeneration and both oracles.
Run it as python3 verify_against_frozen.py /path/to/ecpm-main.

frozen.py. The connector between this repository and the frozen repo.
It finds the checkout through an explicit path, the ECPM_REPO variable,
or a sibling folder, refuses to run unless the frozen code regenerates
the shipped seed-7 example exactly, and wraps the frozen environment in
the same interface the agent loop already uses. Ran on 26/08, the
adaptive policy stepping the actual frozen resource_mdp code reproduced
the smoke numbers exactly, pre costs 4 and 4, post costs 10 and 5,
drops before switch 3, coverage 9 of 15. langgraph_loop.py accepts a
repo path with the new flag, python3 langgraph_loop.py --repo
/path/to/ecpm-main, and then every environment step executes the frozen
code.

official_det_payload.json and official_sto_payload.json. The shared
evidence context, exact frozen question wording, and queried pair set
extracted from the archived official run artifacts.

## What the smoke run showed

The world self check passed. 15 legal state-action pairs. Oracle before
the change, cost 4, route E, A, D, B, F, with the known tie through C.
Oracle after the change, cost 5, unique route E, A, G, H, B, F.

Stale planner, 2 pre episodes and 1 post episode, budget 20 steps per
episode. Pre costs 4 and 4, regret 0. Post, it never reaches the goal.
It sits at D and replays the dead link 18 times. Broken-link usage after
the change is 1.00, which matches the documented stale-planner value.

Adaptive planner with k equal to 3, 2 pre and 2 post episodes. Pre costs
4 and 4. First post episode costs 10, which decomposes as 2 attempts to
reach D, then exactly 3 DROPs, then a 5-step reroute through G and H.
Regret 5. Second post episode costs 5, regret 0, because the mask is
remembered. Drops before switch reads exactly 3, replays 3, adaptation
latency 8 attempts, coverage 9 of 15 pairs. The belief hook logged four
reports and the stated probability for D a2 moved from 1.0 to 0.0.

Epsilon-greedy explorer, same budget. Coverage rises to 13 of 15 pairs
but neither post episode reaches the goal within 20 steps. Exploration
buys coverage and pays for it in regret. This is the tension behind the
open Phase A question, free exploration against task-driven episodes.

Redirect variant, stale planner. Every attempt on (D, a2) returns OK but
arrives at C instead of B, and the planner loops between C and D forever.
Success counting can never catch this change. Only the arrival node gives
it away, which is exactly why the redirect condition earns its place.

## Verification against the frozen repo, 26/08

The uploaded ecpm-main zip was checked with the new script
verify_against_frozen.py. Every check passed. What was checked. All 15
adjacency entries in seed7_world.py against world_pre.edges in the
shipped example_deterministic_silent_break.json, entry by entry. Start
E, goal F, and the full change record, break on (D, a2) toward B, old_p
1.0 to new_p 0.0, mode silent, on the optimal route. The frozen oracle
facts, pre cost 4 with the tie at E and the alternative through C, post
cost 5 with the unique route through G and H. Regeneration,
resource_mdp.make_pair(7, "silent_break", deterministic=True,
matched=True) on the frozen code reproduces the shipped example. The
stochastic sibling, same graph, same break pair, old_p 0.62, oracle
expected costs 6.1326 and 7.4594. And the local World reproduces the
frozen stochastic oracle cost to four decimal places when given the
frozen probability table. To rerun the check yourself, one command,
python3 verify_against_frozen.py /path/to/ecpm-main. One limit, a zip
export carries no git history, so the commit pin 5318c3e must be
confirmed on the actual git checkout, the content check above is
complete either way.

A second result from the zip. The archived official runs store the
complete prompt payload. The rendered evidence is byte identical across
all four archived run directories, deterministic and stochastic alike.
The four probe prompts share one 2233 character context, and each adds
its own question after one blank line. The shared context, the exact
frozen question wording, and the real preservation pair set (H a2, D
a2, D a1, C a1) were extracted into official_det_payload.json and
official_sto_payload.json.

## The break metrics, defined

Broken-link usage. Of the visits to node D in a phase, the fraction where
a2 was chosen. The stale planner scores 1.00 after the change, a perfect
adapter scores 0.00.
Replays through the break. Total attempts on (D, a2) after the change.
Drops before switch. DROPs observed on (D, a2) before the agent first
chooses a different action at D after the change. None means it never
switched.
Adaptation latency. Attempts from the first post-change DROP on (D, a2)
until the goal is next reached.
Coverage. Distinct pairs attempted out of 15.
Per-episode cost and regret. Cost is attempts in the episode. Regret is
cost minus the oracle cost, 4 before and 5 after in the deterministic
instance.

## Knowing versus doing

Sruthi's 2 by 2 from the check-in. Knowing means the localization probe
named (D, a2). Doing means broken-link usage in the final post episode is
zero. The pilot already produced both mismatch boxes with real models,
GPT-4o knew and did not act, Gemma acted and did not know. The metrics
module computes the box label directly, so the agentic runs will fill the
same table with no extra collection. The smoke run demonstrates both
mismatch boxes with scripted policies.

## Framework decision

LangGraph replaces the Inspect idea. Reasons. Sruthi flagged Inspect as
mainly an AI-safety evaluation tool, LangChain and LangGraph are what I
already know, and the one thing Sruthi actually requires, a full
transcript with the model's stated reason for every step, does not come
from the framework at all. It comes from the reply format
{"reason": "...", "action": "aK"} and from logging every raw reply,
which langgraph_loop.py does. If LangGraph fights us, the same loop runs
without any framework, agent_loop.py is the proof.

## Belief reports and surprise

Every N steps the runner forks the transcript and asks the model to state
a success probability for every pair it has tried. The fork means the
probe never enters the model's own working context. This gives the
transition-probability elicitation Sruthi asked for on 24/08, and it is
the same shape as the probability task in the direct-interface pilot, so
the analysis can reuse the mean-absolute-error framing. Surprise in the
AutumnBench sense would need token log probabilities of the observation,
which closed APIs do not return for prompt tokens. ⚠️ The self-report is
therefore a stand-in for surprise, not a measurement of it. Worth one
line in the limitations.

## Experiment E1, ICL against finetuning on matched evidence

The notebook holds one evidence string and feeds it to both arms. The ICL
arm reads it in the prompt with base weights. The FT arm trains on it as
plain text with QLoRA, 1.5B Qwen in 4-bit on a Colab T4, then answers
the probes with an empty context. A third arm combines both. All four
probes use the frozen answer schemas, and the adaptation route is scored
by executing it in the post-change world. The notebook prints the
evidence dose in tokens and in transitions, which is the number the team
needs for the open evidence-matching question.

Draft preregistered predictions, ⚠️ to be locked with the team before the
real run. Detection, FT at or above ICL at 1.5B. Localization, near floor
on the stochastic instance for both. Preservation, high for both.
Adaptation, exploratory, no confident prediction, since finetuning on new
facts can be slow and can encourage guessing.

Resolved on 26/08. The official frozen payload is embedded in the
notebook and used by default, USE_OFFICIAL is True. A hash assert
guards the string. Every probe prompt the notebook sends now reproduces
the frozen pilot prompts byte for byte, checked offline against the
archived sonnet artifact. The stand-in generator stays available for
other seeds by setting USE_OFFICIAL to False. ⚠️ Two caveats remain.
The scorers mirror the frozen contract but official numbers come from
ecpm_parser.run_probe on commit 5318c3e. And the model cells were still
not executed here, no GPU in this machine.

## Assumptions and open questions

⚠️ Cost of an unparseable reply, Note D. The runner retries three times,
then falls back to the first listed action and logs malformed_fallback.
This keeps runs alive without deciding the cost rule. E to sign off.
⚠️ Preservation on unvisited pairs, Note E. Task-driven episodes covered
9 of 15 pairs in the smoke run, so roughly half the pairs would get
preservation questions the agent has no evidence about. Still open.
⚠️ Phase A shape, free exploration against task-driven episodes. The
smoke run gives the first concrete numbers for the trade, coverage 13 of
15 against 9 of 15, at the price of never finishing episodes. Team call.
⚠️ Evidence matching between arms, by transitions, tokens, or episodes.
The notebook and the runner both now report tokens and transitions, so
the decision can be made with numbers on the table.
Stochastic probabilities, resolved on 26/08. The full probability
table is in the shipped example_stochastic_silent_break.json, and the
local oracle reproduces the frozen expected costs from it to four
decimal places. Real stochastic runs still use the frozen instance.
C, the step record contract in agent_loop.py is my proposal for the merge
with your LiveStep, one dict per attempt, fields listed at the top of the
file. If your dataclass dumps those fields, break_metrics works as is.
P, the redirect variant is implemented in the local world as change type
6, one line in with_redirect(), in case it helps the generator addition.
S, nothing here touches the frozen environment or the official numbers.

## Runner upgrades, 26/08 evening

The runner grew from a seed-7 demo into the instrument the main run
needs. New flags on langgraph_loop.py, all requiring --repo. --seed N
runs any eligible graph seed, ineligible seeds are rejected by the
frozen generator's own check with its own message. --stochastic runs
the matched stochastic sibling. --condition picks any frozen change
condition, default silent_break. The break pair and both oracle costs
now come from the frozen instance metadata instead of hardcoded seed-7
values. Every run now persists its probe answers, a summary record with
config, facts, and metrics, and the token usage into the out file, so
no result lives only in terminal scrollback. The knowing versus doing
box is computed from the model's actual localization answer instead of
an assumption. analyze_runs.py reads any number of run files and
reports the metrics, the well-formed rate, belief calibration against
the success rates the agent actually experienced, which queried
preservation pairs were never attempted, and the box.

Two findings from testing these upgrades. First, the adaptive mask
policy that adapts perfectly in the deterministic world cripples itself
in the stochastic world. Healthy links drop too, three drops in a row
happen about five percent of the time at p 0.6, so the policy slowly
masks healthy links until its map is unusable. The deterministic
control is the wrong control for the stochastic arm, and the right
scripted stochastic baseline is an open design point. Second, seed 0 is
eligible and its break has cost delta zero, the detour costs the same
as the broken route, a structurally different test case where
adaptation is free and only detection is hard.

## Suggested order before Thursday

1. Sync with Christian, agree the step record fields, and point his agent
   at break_metrics.py. The repository question stays open as a team
   decision. For now this package is its own repository and frozen.py
   is the bridge to the frozen environment.
2. Install LangGraph, run langgraph_loop.py with the dry backend, fix the
   small first-run issues, then one cheap real run, GPT-4o on the Azure
   credit or local Gemma through Ollama, 10 plus 10 episodes.
3. Run the E1 notebook end to end on Colab. The official payload is
   already embedded and active, so the first clean run already produces
   real numbers. Then re-score the saved answers with
   ecpm_parser.run_probe on the frozen commit for the official figures.
4. Paste the smoke-run numbers and the open questions above into the doc
   by Monday so Sruthi has them before the meeting, per her feedback.
