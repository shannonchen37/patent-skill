# External toolchain integration

## Authority model

- **Shannon `patent-skill`**: orchestrator and only canonical fact source. Owns evidence interpretation, candidate selection, search strategy, feature matrix, claims, specification, support map, risk conclusions, and reconciliation.
- **yjmm10/patent-skills**: optional CNIPA search adapter only. It supplies raw/verifiable search hits; it does not choose the invention or draft claims.
- **HuangXinzhe/cn-patent-drafting**: independent final drafting auditor and DOCX output layer only. It does not re-mine the project or silently replace canonical text.

Do not run the three tools as parallel generators.

## yjmm10 handoff

Repository: `https://github.com/yjmm10/patent-skills`

Use only after Shannon has produced a query plan for a user-confirmed candidate. If installed, read its current `SKILL.md` and `prompts/search.md`, then use its `search` mode or `tools/cnipa_epub_search.py`. Generate 2–8 high-signal terms and run one semantic term per CNIPA query. Preserve:

- exact term;
- execution date and database;
- raw `EPUB_HITS_JSON` result;
- public number, title, abstract and URL;
- tool failure, timeout, dependency, WAF and zero-result notes.

Write first-search material only under `03-prior-art-search/yjmm10/` and Claims-V2 material only under `09-final-search/yjmm10/`. Shannon must independently verify documents, deduplicate results, inspect claims/descriptions, and write the canonical comparison. If yjmm10 or Playwright is unavailable, fall back to current public web/Google Patents search and record the coverage limitation.

Never copy an external search conclusion into the feature matrix without Shannon verification.

## Huang handoff

Repository: `https://github.com/HuangXinzhe/cn-patent-drafting`

Invoke only after `08-claims-v2.md`, `06-specification-v1.md`, `07-claim-support-map.md`, `09-final-search/`, and Shannon's draft audit are stable. Provide read-only copies of:

- evidence map;
- confirmed candidate and feature matrix;
- prior-art reports;
- Claims V2;
- specification, abstract and drawing source;
- claim-support map;
- unresolved-item list.

Use this handoff instruction:

```text
Treat Shannon patent-skill as the canonical case source. Do not reselect the invention, add unsupported technical facts, or overwrite canonical Markdown. Independently audit claim support, antecedent basis, terminology, formulas/parameters, drawing references, enablement and scope. Write findings under filing-package/huang-audit/. Generate separate DOCX files under filing-package/docx/ only from the reconciled canonical text. Mark every proposed substantive change for Shannon reconciliation.
```

Huang findings are recommendations, not facts. Shannon accepts, rejects, or asks the user about each substantive finding, updates the audit trail, and regenerates DOCX only after reconciliation.

## Installation boundary

Do not silently install external dependencies or plugins. If a requested adapter is absent, explain what capability is unavailable and provide its official repository/install path. Continue with the documented fallback when it is safe; stop if the user explicitly requires that adapter and no equivalent result can be produced.
