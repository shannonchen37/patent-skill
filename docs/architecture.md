# Architecture

`SKILL.md` orchestrates judgment-heavy work and routes to focused references. The `patent_skill` package provides deterministic evidence snapshots, canonical case initialization, scanning, models, state validation, comparison logic, validators, and rendering. `scripts/` contains executable wrappers; `schemas/` defines interchange formats; `assets/` contains templates.

The four mapping types are deliberately separate. Claim and search analyses carry snapshot identifiers and hashes so a final review can detect stale conclusions.

Shannon `patent-skill` owns `patent-case/` and is the only canonical writer. yjmm10/patent-skills is an optional CNIPA search adapter whose raw results remain in isolated search folders. HuangXinzhe/cn-patent-drafting receives stable, read-only Claims V2 and specification materials for independent auditing and DOCX rendering; substantive findings return to Shannon for reconciliation.
