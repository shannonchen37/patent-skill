# Canonical case workspace

Use one `patent-case/` directory as the durable case record. Shannon `patent-skill` is the only writer of canonical facts and numbered Markdown artifacts.

## Evidence freeze

Before substantive analysis:

1. Identify an exact project path and immutable Git commit or tag.
2. Record branch, remote, HEAD, exact tag, dirty status, included file hashes, exclusions, and sensitive-file warnings in `00-project-snapshot/snapshot-manifest.json`.
3. Do not copy secrets, customer data, production endpoints, third-party dependency source, generated output, virtual environments, or unrelated business material into the case.
4. Ask the user to confirm project start, first implementation of the core mechanism, every public disclosure channel/date, and people who made substantive technical contributions.
5. Do not create commits or tags without explicit authorization. A dirty worktree or missing immutable reference is a snapshot-gate issue.

The snapshot proves only what material was analyzed. It does not prove inventorship, priority, ownership, patentability, or absence of earlier disclosure.

## State discipline

- Record user answers and unresolved contradictions in `context-ledger.md`.
- Update `case-status.json` when a gate is passed.
- Never advance because a file exists; advance only after required evidence and user confirmations exist.
- Never allow an external search or drafting Skill to overwrite canonical artifacts.
- Preserve raw search results separately from Shannon's conclusions.

## Stage completion

The minimum sequence is snapshot, evidence map, candidate selection, first search, feature matrix, Claims V1, specification, support map, Claims V2, final search, final audit, independent audit/DOCX, and attorney review.

`READY_FOR_ATTORNEY_REVIEW` means the package is organized for professional review. It never means filing-ready or guaranteed patentable.
