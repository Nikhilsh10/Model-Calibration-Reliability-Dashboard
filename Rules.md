# Rules.md — Model Calibration & Reliability Dashboard

Non-negotiable constraints for this project. Read before writing code, and re-check before writing anything that touches metrics or claims.

## 1. Metrics integrity (highest priority — this is the recurring failure mode across your prior projects)

- **No metric appears anywhere — code comments, dashboard copy, README, resume, portfolio — until it has been produced by an actual run against real held-out data.** Not estimated, not "expected," not a placeholder later forgotten and left in.
- If a number is a target/threshold rather than a measured result, label it explicitly as such in the code and never let it leak into user-facing copy unlabeled. This is exactly the MediTune/StreamSentinel mistake — don't repeat it in a new project.
- ECE/MCE/Brier values must be computed from the same held-out set used to evaluate the original model, not from training data or a set you calibrated on (that's circular and will not survive scrutiny).
- Any AI coding agent's claim of "calibration improved" must be verified by printing and reading the actual before/after numbers yourself — same protocol as `git log`/`ls`/raw GitHub URL verification you already use elsewhere.

## 2. Scope discipline

- This is an analysis + dashboard addendum, not a new pipeline. No new data ingestion, no new streaming component, no retraining of the underlying model.
- If you find yourself adding drift detection, multi-model comparison, or auth — stop. That's a different project. Write it down for later instead of building it now.
- Two calibration methods only (Platt, isotonic). Do not add a third "just in case" — more methods without more insight is noise, not depth.

## 3. Statistical validity

- Reliability diagram bins must have a minimum sample count (check before building — see PRD section 0). If a bin is too sparse to be meaningful, the dashboard must show that (bin-count overlay), not hide it.
- Isotonic regression's overfitting risk on small held-out sets must be stated as a limitation in the writeup — not silently accepted, not silently avoided by switching to only-Platt without saying why.
- Calibration corrector must be fit on data distinct from whatever set is used to report final ECE — no fitting and evaluating on the same rows.

## 4. Engineering rules

- Offline analysis and serving are separate processes (see Architecture.md). Do not compute calibration curves inside the FastAPI request handler.
- The `/score` endpoint must use the actual pickled corrector object, not a hardcoded approximation — the whole point is that this is a deployable artifact.
- No secrets, API keys, or credentials committed — this is a portfolio repo, assume it's public.

## 5. Presentation rules

- Every chart must have a legend, and color must not be the only signal distinguishing raw vs. corrected curves (add line style or markers too — accessibility, not decoration).
- No claim in the README stronger than what the numbers support. If ECE improves by a small margin, say the actual margin — don't round up or use vague superlatives.
- Position this project explicitly as an addendum to StreamSentinel in any external-facing text, not a standalone flagship — oversell here would be its own credibility risk.

## 6. When something looks fabricated or too clean
Stop and check it manually before it goes further — a suspiciously smooth calibration curve, a suspiciously perfect ECE, or a coding agent claiming "verified" without showing output are all reasons to re-run and inspect raw numbers yourself.
