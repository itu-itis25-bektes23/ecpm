# Security policy

## What this repository is

Research code for a paper. There is no deployed service, no user data, and no
released package. It is pure-stdlib Python that generates graphs, builds
prompts, calls model APIs when given credentials, and scores the replies.

The realistic risks are narrow, so this policy is narrow.

## Reporting a vulnerability

Email bektes23@itu.edu.tr rather than opening a public issue. Expect a reply
within a week. There is no bounty and no formal disclosure timeline.

## What is worth reporting

**A credential leak.** The harness reads `AZURE_OPENAI_API_KEY` and
`ANTHROPIC_API_KEY` from the environment and must never write them into an
artifact. Every run artifact records the endpoint and model, deliberately, but
never the key. If you find a key, an endpoint with embedded credentials, or
anything that looks like one in `runs/`, in a notebook, or in git history,
report it privately and do not open an issue quoting it.

**An evaluator leak.** `prompt_view()` is the boundary between what a model may
see and what only the scorer may see. `assert_prompt_safe()` in
`ecpm_baseline.py` enforces the same boundary for the null model. A path that
puts `counts_*`, `world_*`, `change`, `oracle` or `seeds` into a prompt is a
correctness failure serious enough to invalidate results, so treat it like a
vulnerability: report it, and expect affected artifacts to be regenerated.

**Anything that executes untrusted input.** The tree is stdlib only and does
not evaluate model output as code. If that changes, it is worth a look.

## What is not a vulnerability

A model answering badly. A scorer disagreeing with your expectation. A run
costing more than expected. Those are issues or pull requests.

## Scanning

None. Code scanning, Scorecard and bandit were all removed on 2026-09-13.

They were switched on, produced about 2,600 alerts, and none of those were
defects in this code. The two that were real, a substring URL match in a test
stub and a handful of empty except blocks, were found and fixed by reading the
code rather than by the tools. The rest was a linter suite reporting `assert`
statements in an assert-driven test suite, scanners for languages this
repository does not contain, and supply-chain criteria written for widely
depended-upon open source.

The cost was not the alerts. It was thousands of Actions minutes, a flooded
inbox for everyone watching the repository, and a Security tab nobody could
read, which is worse than no Security tab because it hides anything real.

Secret scanning stays on, because it is free, silent until it fires, and
guards the one thing here that genuinely matters: an API key reaching an
artifact or a commit.

The six test suites remain the real check on correctness, and
`test_ecpm_parser.py` keeps the parser fuzz test, which was the one genuinely
useful thing to come out of the exercise.

## Supported versions

Only `main`. Tagged snapshots such as `v2.1-prefreeze` exist for provenance and
are not maintained.
