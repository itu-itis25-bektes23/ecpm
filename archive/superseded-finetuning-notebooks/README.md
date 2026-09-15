# Superseded finetuning notebooks

The August 2026 in-context versus finetuning notebooks. Kept because the
replies they produced are still in `runs/2026-08-27_e1_qwen2.5-1.5b/`.

Two defects, both fixed in `experiments/notebooks/`:

- the route scorer hard-coded `START, GOAL = "E", "F"`. Only seed 7 has that
  start and goal; across the 32 graded seeds there are 19 distinct pairs, so
  the walk began at the wrong node on 31 of them. Every route number they
  produced is void.
- they carried their own JSON extractor, stricter than the frozen contract
  in `docs/INTERFACE.md` section 7, which accepts prose around the object.
  The two disagree on 16 of 64 preservation replies, all of them valid JSON
  followed by one stray quote character.

Their anchor generator, `anchors.py`, is not archived here: it is the one
that reproduces, and condition A of
`runs/2026-09-14_e1_phase1_replicate/` still uses it. It lives with the
notebooks that call it.
