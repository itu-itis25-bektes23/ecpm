# archive

Tooling that did its job and is kept for provenance, not maintained.

- `adversarial_review.py` and `ecpm_reply_verification.py` were the review
  scripts used for the schema 2.1 freeze sign-off on 19 August 2026. Nothing
  imports them and they are not part of any test suite.

They are kept because they are the evidence that the freeze was checked
rather than asserted. Deleting them would remove that record.

Both open the shipped example records by relative path, so if you ever need
to run one, run it from the repository root:

    python3 archive/ecpm_reply_verification.py
