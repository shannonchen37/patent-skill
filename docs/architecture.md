# Architecture

`SKILL.md` orchestrates judgment-heavy work and routes to focused references. The `patent_skill` package provides deterministic scanning, models, snapshots, comparison logic, state transitions, validators, and rendering. `scripts/` contains executable wrappers; `schemas/` defines interchange formats; `assets/` contains templates.

The four mapping types are deliberately separate. Claim and search analyses carry snapshot identifiers and hashes so a final review can detect stale conclusions.
