---
name: patent-skill
description: Analyze a user-supplied target R&D project's source code, engineering documents, tests, experiments, and inventor context to mine technical inventions, assess Chinese software and AI patent workflow risks, map engineering provenance, structure prior-art analysis, develop claim strategy, and prepare traceable Chinese invention-patent drafting assets. Use when turning a separately supplied R&D project into invention candidates, disclosures, claim sets, specifications, or pre-filing review materials.
---

# Patent Skill

Turn R&D evidence into traceable, reviewable patent drafting assets. Never represent an output as legal advice or filing-ready.

## Target input gate

Run this gate before every mode:

1. Accept a target only when the user explicitly identifies a separate project attachment, repository, workspace, or path as the R&D project to analyze.
2. Treat this Skill's own directory and all bundled files—including `SKILL.md`, `README.md`, `references/`, `scripts/`, `schemas/`, `assets/`, `tests/`, and package source—as tooling, never as the patent subject.
3. Never infer a target project from files bundled inside the Skill package.
4. If no separate target is available, or the target is ambiguous, stop before `discover` and ask the user to upload or select the real project. Produce no invention analysis.
5. State the accepted target attachment, repository, workspace, or path before scanning it.

When the gate fails, reply: `未检测到独立的目标研发项目。请另行上传项目代码/文档 ZIP，或明确指定待分析的仓库、工作区或路径。patent-skill 自身文件不会被作为专利分析对象。`

## Non-negotiable rules

- Never invent technical facts, metrics, prior art, patent numbers, inventors, ownership, or disclosure dates.
- Do not move directly from source code to claims.
- Keep engineering provenance, specification support, prior-art disclosure, and priority basis separate.
- Do not combine references to conclude lack of novelty.
- Treat scores and legal-risk labels as preliminary review aids.
- Keep internal paths, customer data, secrets, and irrelevant trade secrets out of public-facing drafts.
- Never set `FILING_READY`. Stop at `READY_FOR_ATTORNEY_REVIEW`, and only when required artifacts and confirmations exist.

## Workflow

1. Pass the target input gate, then collect filing context, rights, disclosure, priority, development-location, and foreign-filing information.
2. Scan the repository safely, extract symbols, and abstract implementation into technical mechanisms.
3. Assess eligibility and excluded subject matter. Read [patent-eligibility-cn.md](references/patent-eligibility-cn.md).
4. Mine candidates, build engineering provenance, perform preliminary search, rank candidates, and assess preliminary unity.
5. Ask inventors to resolve missing facts, then create an invention brief and preliminary claim skeleton (`CS01`, not `C1`).
6. Document search queries and sources. Read [prior-art-search.md](references/prior-art-search.md), [novelty-analysis-cn.md](references/novelty-analysis-cn.md), and [inventive-step-cn.md](references/inventive-step-cn.md).
7. Analyze feature combinations, create claim strategy and Claims V1, then recheck actual claims and unity.
8. Draft the specification and embodiments, then create Claims V2.
9. Recheck Claims V2 against search, eligibility, and unity; validate specification support, priority basis, amendment basis, fallbacks, abstract, and drawings.
10. Reconfirm inventorship/ownership, redact internal evidence, and produce the pre-filing review report.

## Modes

- `discover`: context through inventor questions.
- `analyze P001`: invention brief, skeleton, documented search, feature-combination analysis.
- `draft P001`: require an analyzed search snapshot; produce Claims V1/V2 and support matrices.
- `draft P001 --pre-search`: label every output `PRE-SEARCH DRAFT`; never advance to review-ready.
- `review P001`: run final CN, search, support, priority, eligibility, unity, inventorship, and redaction checks.
- `full`: attempt all stages but stop at unresolved human or evidence gates.

## Reference routing

- Filing context, disclosure, priority, and confidentiality: [filing-context-cn.md](references/filing-context-cn.md)
- Eligibility and AI/data issues: [patent-eligibility-cn.md](references/patent-eligibility-cn.md), [ai-disclosure-cn.md](references/ai-disclosure-cn.md)
- Search, novelty, inventive step, and conflicting applications: [prior-art-search.md](references/prior-art-search.md), [novelty-analysis-cn.md](references/novelty-analysis-cn.md), [inventive-step-cn.md](references/inventive-step-cn.md), [conflicting-applications-cn.md](references/conflicting-applications-cn.md)
- Unity and priority: [portfolio-unity-cn.md](references/portfolio-unity-cn.md), [priority-basis-cn.md](references/priority-basis-cn.md)
- Claims, specification, abstract, and amendments: [claim-drafting-cn.md](references/claim-drafting-cn.md), [specification-cn.md](references/specification-cn.md), [abstract-cn.md](references/abstract-cn.md), [amendment-basis-cn.md](references/amendment-basis-cn.md)
- Final review: [review-rules.md](references/review-rules.md), [disclosure-redaction.md](references/disclosure-redaction.md)

Use scripts for deterministic checks. Run `python -m patent_skill.cli --help` for the CLI.
