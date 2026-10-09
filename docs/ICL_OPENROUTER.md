# Expanded ICL: OpenRouter and 16K readiness

This is implementation support, not live deployment admission. No successful
preflight or pilot is supplied with the code. Begin with one repeat, seed 8,
deterministic silent break, model first and `separate_reports_post_task_v1`.
The v3 preparation policy, scientific prompts and scores are unchanged.

## Request profiles

`deepseek_openrouter` uses only `deepseek/deepseek-v4.1-flash` at
`https://openrouter.ai/api/v1`. It reads `OPENROUTER_API_KEY` from the process
environment, never from a result/configuration file. Do not put keys in commands,
logs or Git. Local and Together credentials remain isolated.

OFF sends `reasoning: {enabled: false, exclude: false}`; ON sends
`reasoning: {enabled: true, exclude: false}`. Neither sends a separate reasoning
budget, temperature, top-p, top-k or provider seed. Repeat labels remain labels.
Omission is not verified greedy decoding. ON uses the provider's documented
default reasoning effort, which must be recorded in its control provenance.
The `sol` profile is unchanged: `gpt-5.6-sol`, effort `none`/`medium`, and no
sampling fields. It uses `max_completion_tokens`; DeepSeek uses `max_tokens`.
Both request 16,384 tokens per stage, including exposed reasoning.

OpenRouter requests pin one evidenced backing-provider slug with `provider.only`,
`require_parameters: true` and `allow_fallbacks: false`. Context compression is
explicitly disabled with `plugins: [{id: "context-compression", enabled: false}]`.
Do not enable response healing or structured-output enforcement in account
defaults. Check these settings and save evidence; a request payload alone does
not prove the effective deployment behavior.

Primary sources checked 2026-10-09:

- [Exact model metadata](https://openrouter.ai/api/v1/models): the model advertises
  optional reasoning. This does not prove account access or returned identity.
- [Provider endpoints](https://openrouter.ai/api/v1/models/deepseek/deepseek-v4.1-flash/endpoints):
  limits, prices and supported parameters vary by backing provider. Pin one,
  then record its returned name/version from the preflight.
- [Reasoning controls and accounting](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens):
  excluding reasoning text is not disabling computation. A length finish fails.
- [Provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
  and [context compression](https://openrouter.ai/docs/guides/features/message-transforms).
- [DeepSeek thinking semantics](https://api-docs.deepseek.com/guides/thinking_mode/):
  its native thinking mode ignores temperature; top-p has mode-dependent behavior.
  A catalogue field being accepted does not establish common greedy sampling.

## Fill a non-secret configuration

Copy [the incomplete OFF template](openrouter_deepseek.template.json) outside Git.
Nulls are intentional and fail readiness. Do not replace them with test fixtures.
Record exact-model access, expected returned model/provider from documented
identity mapping (then reconcile with the actual preflight), pinned routing, supported
fields (including gateway routing/plugins), output limit, no hidden budget,
full-history handling, and dated sources. Private runtime/template values may
remain null only with explicit unavailable-metadata provenance. Never invent hashes.
Record effective sampling restrictions/defaults in `sampling_source`; the common
greedy request remains unresolved unless supported by the chosen provider.

For ON, use a separate copy: set both reasoning modes to `on`, the evidence effect
to `enables_reasoning`, and the evidence request's `enabled` to true. Preserve all
non-reasoning controls. Keep preflight evidence separate for OFF and ON.

The context bound requires evidence for tokenizer UTF-8 behavior, per-message
template/system/generation-prefix overhead and the chosen endpoint's context
capacity. Do not infer these from a model name or reuse an unverified constant.
Every actual conversation, including complete retained final answers but not
private reasoning, is checked with 16,384 tokens reserved before generation.
Reported prompt usage is also checked afterward. No history is trimmed. A short
preflight cannot establish that all future requests fit.

Prices must cover the pinned provider's applicable tiers, time windows and long
contexts. The preflight tool reports an uncached ceiling from the input bound
plus the full output cap; it is not a spend forecast or an invoice. Saved provider
usage, cache fields and reported cost remain available separately. Set a spending
limit before executing any generation command.

## Exact preflight procedure (not executed during implementation)

After filling and independently checking non-generation provenance:

```sh
python3 -B experiments/preflight_icl_expanded.py \
  --config /path/to/deepseek-off-candidate.json --out /path/to/off-request-review
```

This prepares the fixed integer request, context check and ceiling without
generation. Review them first. With separate authorization, execute exactly once
into a different unused directory:

```sh
python3 -B experiments/preflight_icl_expanded.py --execute \
  --config /path/to/deepseek-off-candidate.json --out /path/to/off-preflight
python3 -B experiments/preflight_icl_expanded.py --execute \
  --config /path/to/deepseek-on-candidate.json --out /path/to/on-preflight
```

Stop if OFF fails; do not run the ON command or retry. Each command saves the
request and complete raw response before validation. Acceptance requires HTTP
200, nonblank content, stop finish, known prompt/completion usage within limits,
matching model/provider and verified controls. OFF uses measured zero with a
documented count source or exact-model documented disable assurance. Missing
counts remain null and direct evidence unknown; empty text alone is insufficient.
Any positive reasoning contradicts OFF. ON requires positive reasoning evidence.
No automatic retries or fallback occur. Mathematical correctness is separate.
Only an accepted response produces `validated_wrapper.json`. Sol uses the same
procedure with its own evidence, endpoint and `OPENAI_API_KEY`; do not substitute
a different Sol version or connection scheme.

## First pilot commands, after readiness and cost review

```sh
python3 -B run_pilot.py --protocol icl_expanded_v2 \
  --seed 8 --mode det --condition silent_break --k 10 --budget 10 --evidence-seed 0 \
  --model-first-condition model_first --history-policy separate_reports_post_task_v1 \
  --request-profile deepseek_openrouter --provider openai \
  --model deepseek/deepseek-v4.1-flash --base-url https://openrouter.ai/api/v1 \
  --reasoning-mode off --repeats 1 --sampling-seeds 0 --max-tokens 16384 --timeout 900 \
  --deployment-config /path/to/off-preflight/validated_wrapper.json \
  --tag expanded_seed8_deepseek_model_first_separate_off_16k_v1
python3 -B run_pilot.py --protocol icl_expanded_v2 \
  --seed 8 --mode det --condition silent_break --k 10 --budget 10 --evidence-seed 0 \
  --model-first-condition model_first --history-policy separate_reports_post_task_v1 \
  --request-profile deepseek_openrouter --provider openai \
  --model deepseek/deepseek-v4.1-flash --base-url https://openrouter.ai/api/v1 \
  --reasoning-mode on --repeats 1 --sampling-seeds 0 --max-tokens 16384 --timeout 900 \
  --deployment-config /path/to/on-preflight/validated_wrapper.json \
  --tag expanded_seed8_deepseek_model_first_separate_on_16k_v1
```

Audit OFF before launching ON. Model errors stay scored; operational failures stop
the block without recovery. Each block has one conversation and six responses.
Use unused tags. For an offline command-construction check, replace `--provider
openai` with `--provider dry-run` and omit `--deployment-config`; synthetic results
are not model performance or evidence that OFF/ON controls work.
