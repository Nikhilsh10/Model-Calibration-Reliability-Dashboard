# Memory.md — Model Calibration & Reliability Dashboard

Running context file for this project. Update as decisions get made; don't let this drift from what's actually true in the repo.

## Project identity
- Name: Model Calibration & Reliability Dashboard
- Relationship to existing work: addendum to StreamSentinel (real-time anomaly detection system), not a standalone flagship. Positioned this way explicitly in Rules.md and Design.md to avoid overclaiming.
- Base model(s) used: StreamSentinel sensor/financial ensemble (Isolation Forest + Autoencoder). Verified metrics already on record: Sensor ROC-AUC 0.9952 / F1 0.8392, Financial ROC-AUC 0.9893 / F1 0.7407, anomaly rate 5.5%, p95 inference latency < 10ms.

## Status (update this section as phases complete)
- [ ] Phase 0 — kill-criteria check (bin sample counts) — **not yet run**
- [ ] Phase 1 — offline analysis (real ECE/MCE/Brier, raw + Platt + isotonic)
- [ ] Phase 2 — serialized JSON + pickled correctors
- [ ] Phase 3 — FastAPI serving layer
- [ ] Phase 4 — React dashboard
- [ ] Phase 5 — writeup/integration into portfolio

## Verified facts (only add here once actually run and inspected — see Rules.md §1)
- (empty — nothing computed yet as of this file's creation)

## Known unresolved risks
- Anomaly rate is 5.5% — decile bins on the minority class may be sparse. This is the first thing to check, before any other work (see PRD §0, Phases.md Phase 0).
- Isotonic regression may overfit if the calibration split is small — flag as a stated limitation once the actual split size is known, don't decide the answer in advance.

## Standing protocol carried over from prior projects
- Never accept an AI coding agent's claim of a metric, a "verified" state, or a completed computation without independently inspecting raw output (console prints, file contents, or a manual re-check in a Python shell).
- No number goes into README/portfolio/resume copy until it exists in this file's "Verified facts" section first, with the actual run that produced it identifiable.
- If a fabrication or placeholder value is caught, log it here as a "caught issue" rather than silently correcting it and moving on — keeps the pattern visible across projects.

## Caught issues log
- (empty so far)

## Open questions for next session
- Which StreamSentinel model (sensor vs. financial) to lead with — decide after Phase 0's bin-count check, whichever has better-supported bins.
- Whether dark mode is worth the extra verification pass given portfolio scope — currently marked optional in Design.md.
