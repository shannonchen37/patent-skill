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

`CLAIMS_V2` requires both files. Independents use consecutive `[I<n>-L<n>]`; each dependent claim uses consecutive `[D<n>-L<n>]` for newly added limitations. The structure records dependencies and fallback priority. Markdown metadata is forbidden after formal claims begin.

`CLAIM_SUPPORT_MAP` uses canonical JSON and requires exactly one supported record for every independent and dependent limitation. `FINAL_SEARCH` binds its session to Claims V2 hashes and requires structured combination/distinguishing coverage for independent claims.

`APPLICATION_DRAFT` requires a clean filing rendering, substantive final specification/abstract, conditional evidence-bound figures, exact hashes, and synchronization for every limitation. `FINAL_AUDIT` binds to those hashes. `INDEPENDENT_AUDIT` binds to both application and final audit and requires every finding to be reconciled.

`DOCX_PACKAGE_RENDERED` requires a distinct DOCX for every required subject. Each file must exceed the minimum size threshold, be a readable OOXML ZIP, contain `[Content_Types].xml` and valid `word/document.xml`, and include nonempty document text.

`CONTENT_READY_FOR_ATTORNEY_REVIEW` is computed from the structured question ledger: any open blocking technical question prevents entry. The later independent-audit and rendered-DOCX states remain non-filing states. `FILING_READY` is forbidden.
