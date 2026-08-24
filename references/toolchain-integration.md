# External toolchain integration

## Authority model

- **Shannon `patent-skill`**: orchestrator and only canonical fact source. Owns evidence interpretation, candidate selection, search strategy, feature matrix, claims, specification, support map, risk conclusions, and reconciliation.
- **yjmm10/patent-skills**: optional CNIPA search adapter only. It supplies raw/verifiable search hits; it does not choose the invention or draft claims.
- **HuangXinzhe/cn-patent-drafting**: independent final drafting auditor and DOCX output layer only. It does not re-mine the project or silently replace canonical text.

Do not run the three tools as parallel generators.

## yjmm10 handoff

Repository: `https://github.com/yjmm10/patent-skills`

Use after Shannon has produced query plans for viable candidates. Candidate selection follows the first search: auto-select an obvious winner, but require human confirmation when rankings are close or multiple filings are strategically reasonable. If installed, read its current `SKILL.md` and `prompts/search.md`, then use its `search` mode or `tools/cnipa_epub_search.py`. Generate 2–8 high-signal terms and run one semantic term per CNIPA query. Preserve:

- exact term;
- execution date and database;
- raw `EPUB_HITS_JSON` result;
- public number, title, abstract and URL;
- tool failure, timeout, dependency, WAF and zero-result notes.

Write first-search material only under `03-prior-art-search/yjmm10/` and Claims-V2 material only under `10-final-search/yjmm10/`. Also write the required canonical fields to the enclosing `search-records.jsonl`. Final-search records must add `claim_id`, `limitation_ids`, and `search_scope`; cover every complete independent-claim combination and every distinguishing limitation declared in `08-claims-v2-structure.json`. Shannon must independently verify documents, deduplicate results, inspect claims/descriptions, and write the canonical comparison. If yjmm10 or Playwright is unavailable, fall back to current public web/Google Patents search and record the coverage limitation.

Never copy an external search conclusion into the feature matrix without Shannon verification.

## Huang handoff

Repository: `https://github.com/HuangXinzhe/cn-patent-drafting`

Invoke only after `12-application/`, `09-claim-support-map.md`, `10-final-search/`, and `13-final-audit.json` are validated and Shannon has reached `CONTENT_READY_FOR_ATTORNEY_REVIEW`. Provide read-only copies of:

- evidence map;
- confirmed candidate and feature matrix;
- prior-art reports;
- final claims generated from Claims V2;
- Claims V2 independent-claim structure;
- final specification, abstract and drawing description;
- application synchronization metadata;
- claim-support map;
- unresolved-item list.

Use this handoff instruction:

```text
Treat Shannon patent-skill as the canonical case source. Do not reselect the invention, add unsupported technical facts, or overwrite canonical Markdown. Independently audit claim support, antecedent basis, terminology, formulas/parameters, drawing references, enablement and scope. Write findings under filing-package/huang-audit/. Generate separate DOCX files under filing-package/docx/ only from the reconciled canonical text. Mark every proposed substantive change for Shannon reconciliation.
```

Huang findings are recommendations, not facts. Shannon accepts, rejects, or asks the user about each substantive finding, updates the audit trail, and regenerates DOCX only after reconciliation. Before entering `DOCX_PACKAGE_RENDERED`, Shannon independently validates every required file as a distinct, nonempty OOXML document; filename presence alone is insufficient.

## Installation boundary

Do not silently install external dependencies or plugins. If a requested adapter is absent, explain what capability is unavailable and provide its official repository/install path. Continue with the documented fallback when it is safe; stop if the user explicitly requires that adapter and no equivalent result can be produced.
