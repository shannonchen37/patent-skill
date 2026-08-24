# Architecture

`SKILL.md` orchestrates judgment-heavy work and routes to focused references. The `patent_skill` package provides three deterministic evidence-snapshot types, canonical case initialization, sequential `advance_stage()` enforcement, stage-specific validators, scanning, models, comparison logic, and rendering. `scripts/` contains executable wrappers; `schemas/` defines interchange formats; `assets/` contains templates.

The four mapping types are deliberately separate. Claim and search analyses carry snapshot identifiers and hashes so a final review can detect stale conclusions.

Shannon `patent-skill` owns `patent-case/` and is the only canonical writer. yjmm10/patent-skills is an optional CNIPA search adapter whose raw results remain in isolated search folders. HuangXinzhe/cn-patent-drafting receives stable, read-only content only after `CONTENT_READY_FOR_ATTORNEY_REVIEW`; independent auditing and DOCX rendering are separate later states, and substantive findings return to Shannon for reconciliation.
