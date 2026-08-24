# Canonical case workspace

Use one `patent-case/` directory as the durable case record. Shannon `patent-skill` is the only writer of canonical facts. JSON is authoritative where a JSON/Markdown pair exists; Markdown is regenerated.

## Evidence freeze

Before substantive analysis:

1. Identify an exact project source and choose one evidence type: `git_commit`, `uploaded_archive`, or `directory_manifest`.
2. Record the Git context when available, archive or deterministic-manifest digest, per-file SHA-256 values, exclusions, and sensitive-file warnings in `00-project-snapshot/snapshot-manifest.json`.
3. Do not copy secrets, customer data, production endpoints, third-party dependency source, generated output, virtual environments, or unrelated business material into the case.
4. Record project start, first implementation, public disclosures, and substantive contributors as filing-context questions. Do not block technical analysis on them unless known facts directly affect the present novelty, entitlement, or scope decision.
5. Do not create commits or tags without explicit authorization. Freeze a dirty worktree using a deterministic directory manifest and disclose the limitation.

The snapshot proves only what material was analyzed. It does not prove inventorship, priority, ownership, patentability, or absence of earlier disclosure.

## State discipline

- Record questions and sourced answers in `context-questions.json`; `context-ledger.md` is its generated view.
- Advance only with `python -m patent_skill.cli case advance <case> <next-stage>`; the transition must be exactly one stage.
- Reopen earlier substantive work only with `case revise <case> <stage> --reason ...`. Archive target and downstream artifacts under `revisions/Rnnn/`, increment the revision, and regenerate the reopened-stage template.
- Stage validators inspect Chinese claim syntax, structured search logs, ranking ambiguity, exact limitation/support equality, Claims-V2 search coverage, technical-question closure, independent audit, and OOXML validity.
- Never advance merely because a file exists; required evidence and conditional confirmations must pass validation.
- Never allow an external search or drafting Skill to overwrite canonical artifacts.
- Preserve raw search results separately from Shannon's conclusions.

## Stage completion

The enforced sequence is:

`PROJECT_SNAPSHOT → EVIDENCE_MAP → INVENTION_CANDIDATES → FIRST_SEARCH → CANDIDATE_RANKING → FEATURE_MATRIX → CLAIMS_V1 → SPECIFICATION_V1 → SUPPORT_CANDIDATES → CLAIMS_V2 → CLAIM_SUPPORT_MAP → FINAL_SEARCH → APPLICATION_DRAFT → FINAL_AUDIT → CONTENT_READY_FOR_ATTORNEY_REVIEW → INDEPENDENT_AUDIT → DOCX_PACKAGE_RENDERED`.

`EVIDENCE_MAP`, `INVENTION_CANDIDATES`, and `FEATURE_MATRIX` validate their canonical JSON against schemas, require unique IDs and valid cross-references, and regenerate Markdown. Two-line placeholder tables cannot pass.

`CLAIMS_V2` requires both `08-claims-v2.md` and `08-claims-v2-structure.json`. Put the preamble of each independent claim on its own colon-terminated line, then put exactly one consecutive `[I<n>-L<n>]` limitation on each following substantive line. The structure file must identify every independent claim, all limitation IDs, and the nonempty subset of distinguishing limitation IDs.

`CLAIM_SUPPORT_MAP` requires exactly one supported row per structured limitation. `FINAL_SEARCH` requires `claim_id`, `limitation_ids`, and `search_scope` in every search record, one `claim_combination` record covering the full limitation set of each independent claim, and coverage of every distinguishing limitation.

`APPLICATION_DRAFT` requires label-stripped Claims V2, substantive final specification/abstract/drawings, exact file hashes, and one complete synchronization record for every independent-claim limitation. `FINAL_AUDIT` requires structured novelty analysis for every independent claim and evidence/risk/action fields for every review topic.

`DOCX_PACKAGE_RENDERED` requires a distinct DOCX for every required subject. Each file must exceed the minimum size threshold, be a readable OOXML ZIP, contain `[Content_Types].xml` and valid `word/document.xml`, and include nonempty document text.

`CONTENT_READY_FOR_ATTORNEY_REVIEW` is computed from the structured question ledger: any open blocking technical question prevents entry. The later independent-audit and rendered-DOCX states remain non-filing states. `FILING_READY` is forbidden.
