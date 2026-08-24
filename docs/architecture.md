# Architecture

`SKILL.md` orchestrates judgment-heavy work and routes to focused references. The `patent_skill` package provides secure directory/ZIP evidence snapshots, sequential advance plus audited revision, JSON Schema gates, structured questions, Chinese claim validation, independent-claim limitation checks, final-search coverage, synchronized application construction, structured final audit, export, and OOXML validation.

The four mapping types are deliberately separate. Claim and search analyses carry snapshot identifiers and hashes so a final review can detect stale conclusions.

Shannon `patent-skill` owns `patent-case/` and is the only canonical writer. Where `.json` and `.md` coexist, JSON is the fact source and Markdown is generated. yjmm10/patent-skills is an optional CNIPA search adapter. HuangXinzhe/cn-patent-drafting receives stable, read-only content only after `CONTENT_READY_FOR_ATTORNEY_REVIEW`; substantive findings return through a formal Shannon revision.
