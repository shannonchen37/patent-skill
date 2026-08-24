# Canonical case workspace

Use one `patent-case/` directory as the durable case record. Shannon `patent-skill` is the only writer of canonical facts and numbered Markdown artifacts.

## Evidence freeze

Before substantive analysis:

1. Identify an exact project source and choose one evidence type: `git_commit`, `uploaded_archive`, or `directory_manifest`.
2. Record the Git context when available, archive or deterministic-manifest digest, per-file SHA-256 values, exclusions, and sensitive-file warnings in `00-project-snapshot/snapshot-manifest.json`.
3. Do not copy secrets, customer data, production endpoints, third-party dependency source, generated output, virtual environments, or unrelated business material into the case.
4. Record project start, first implementation, public disclosures, and substantive contributors as filing-context questions. Do not block technical analysis on them unless known facts directly affect the present novelty, entitlement, or scope decision.
5. Do not create commits or tags without explicit authorization. Freeze a dirty worktree using a deterministic directory manifest and disclose the limitation.

The snapshot proves only what material was analyzed. It does not prove inventorship, priority, ownership, patentability, or absence of earlier disclosure.

## State discipline

- Record user answers and unresolved contradictions in `context-ledger.md`.
- Advance only with `python -m patent_skill.cli advance-stage <case> <next-stage>`; the transition must be exactly one stage.
- Stage validators inspect structured search logs, artifact content, ranking ambiguity, claim support, technical-question closure, independent audit, and DOCX completeness.
- Never advance merely because a file exists; required evidence and conditional confirmations must pass validation.
- Never allow an external search or drafting Skill to overwrite canonical artifacts.
- Preserve raw search results separately from Shannon's conclusions.

## Stage completion

The enforced sequence is:

`PROJECT_SNAPSHOT → EVIDENCE_MAP → INVENTION_CANDIDATES → FIRST_SEARCH → CANDIDATE_RANKING → FEATURE_MATRIX → CLAIMS_V1 → SPECIFICATION_V1 → SUPPORT_CANDIDATES → CLAIMS_V2 → CLAIM_SUPPORT_MAP → FINAL_SEARCH → FINAL_AUDIT → CONTENT_READY_FOR_ATTORNEY_REVIEW → INDEPENDENT_AUDIT → DOCX_PACKAGE_RENDERED`.

`CONTENT_READY_FOR_ATTORNEY_REVIEW` means the technical content is organized for professional review. The later independent-audit and rendered-DOCX states remain non-filing states. `FILING_READY` is forbidden.
