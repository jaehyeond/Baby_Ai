# Conventions

- Evidence over assumptions; separate pipeline bugs, model limitations, data coverage, and experimental-design limits.
- Preserve sealed artifacts. Create a successor artifact that explicitly binds and supersedes a prior next step instead of overwriting history.
- Exploratory results must remain `not_for_claim`; public exploratory questions cannot be recycled as confirmatory fresh/held-out samples.
- Public-knowledge answers route to `external_teacher`; do not make the user repeatedly answer generic questions.
- Freeze answers/targets before reading predictor output. Post-hoc semantic review must never mutate the original exact-name audit.
- Keep DB writes, learning, calibration, held-out, performance claims, and production promotion as independent false-by-default gates.
- Tests belong under `tests/`; research scripts under `scripts/research/`; research reports under `claudedocs/research/`.
- Do not commit or push unless the user explicitly asks.