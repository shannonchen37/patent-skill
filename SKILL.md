---
name: patent-skill
description: Progressively guide the user from real R&D project code to a Chinese invention-patent draft by identifying material uncertainties, asking focused context questions, confirming code evidence and invention scope, performing mandatory prior-art overlap analysis, and drafting traceable patent assets only after confirmation gates. Use when a user wants to mine or draft a Chinese patent from a software, algorithm, AI, or engineering project, including when the project, title, or technical context is incomplete; never analyze the Skill package as the invention.
---

# Patent Skill

Turn R&D evidence into traceable, reviewable patent drafting assets through progressive user confirmation. Never represent an output as legal advice or filing-ready.

## Progressive interaction contract

Do not run the workflow end to end in one uninterrupted pass. Code is evidence, not a complete invention disclosure. After each material analysis stage, expose the important uncertainty and wait for the user to confirm or add context before advancing.

Maintain a context ledger with four states:

- `CONFIRMED_BY_USER`: explicitly confirmed by the user;
- `SUPPORTED_BY_CODE`: directly supported by identified project evidence;
- `INFERRED_NEEDS_CONFIRMATION`: plausible but capable of changing the protected scope;
- `CONTRADICTED_OR_MISSING`: contradicted by the supplied title/materials or absent from the evidence.

Ask one focused question by default and never more than three questions in one turn. For each question, briefly state:

1. what the evidence currently shows;
2. what is uncertain or contradictory;
3. why the answer affects the patent content.

Do not ask the user to understand internal stages, candidate IDs, legal jargon, or state names. Translate each uncertainty into a concrete technical question with examples where useful.

Pause instead of assuming when an answer could materially change the technical problem, necessary technical features, feature interaction, technical effect, claim scope, novelty position, enablement, or choice among multiple inventions. Record disclosure history and contributor questions separately; they do not block technical-content work unless the known facts directly affect novelty, entitlement, or the present decision.

## Project intake and upload guidance

Run this intake before every mode:

1. Accept a target only when the user explicitly identifies a separate project attachment, repository, workspace, or path as the R&D project to analyze.
2. Treat this Skill's own directory and all bundled files—including `SKILL.md`, `README.md`, `references/`, `scripts/`, `schemas/`, `assets/`, `tests/`, and package source—as tooling, never as the patent subject.
3. Never infer a target project from files bundled inside the Skill package.
4. If no separate target is available, do not merely report an error. Start the upload guidance below and wait for the user's project. Produce no invention analysis yet.
5. If multiple possible targets exist, list their names and ask the user to choose one.
6. State the accepted target attachment, repository, workspace, or path before scanning it.
7. After a valid target arrives, ask the patent-title question below. Do not require the user to select an internal workflow mode.

When no target project is available, reply in Chinese with this actionable guidance:

```text
好的，我会先从你的真实研发项目中挖掘可申请专利的技术方案。

请在当前对话中上传“待分析项目的代码 ZIP”（不是 patent-skill 安装包）。建议 ZIP 中包含：
- 项目源代码；
- README、架构或设计文档；
- 测试代码、实验记录或性能数据（如有）；
- 能说明技术问题、技术手段和技术效果的其他材料（如有）。

上传前请删除密钥、客户数据、账号凭据以及无权披露的内容。你只需上传文件；收到后我会确认项目名称和材料范围，并询问你是否已有拟申请的专利名称。
```

Adapt the first instruction to the environment:

- In ChatGPT or another attachment-capable chat, explicitly ask the user to use the attachment/upload button and upload the target code ZIP in the current conversation.
- In Codex with an open repository, ask the user to open the target repository as the current workspace or provide its exact path. If an attachment is supported, also offer ZIP upload.
- Never claim that an upload button exists when the current interface clearly does not support attachments.

When a target arrives, acknowledge it before analysis: `已收到目标项目：<attachment/repository/path>。我将仅分析该项目，不会分析 patent-skill 自身文件。`

## Patent-title intake

Ask one content question before mining: `你是否已有拟申请的专利名称？有则直接提供；没有请回复“无”，我将根据代码挖掘核心发明并生成候选名称。`

- If the user supplies a title, treat it as intent and a search seed, not as the final title or proof of novelty.
- If the user supplies no title, derive the protected subject from code evidence, search it, and propose a title only after selecting the strongest feature combination.
- Search the exact title, synonyms, broader/narrower expressions, technical problem, mechanism, feature combination, and relevant IPC/CPC classes.
- Do not judge overlap from titles alone. Compare technical solutions and claim features.
- If close prior art is found, do not merely rename the invention. Identify a genuine, code-supported distinguishing feature combination and search again.
- If no defensible distinction exists, report high overlap risk instead of inventing a difference.
- Confirm the final title after Claims V2. Use clear, concise technical terminology that reflects the protected subject and type.

## Canonical case workspace

Make Shannon `patent-skill` the orchestrator and only canonical source of case facts. Create or resume one user-visible `patent-case/` directory before substantive analysis. For a new case, prefer:

```bash
python -m patent_skill.cli init-case patent-case --project <project-path> --title "<optional-title>"
```

Read [case-workspace.md](references/case-workspace.md) before creating or advancing a case. Do not scatter authoritative artifacts across chat attachments, temporary directories, or external Skill output folders.

Freeze the evidence basis before invention drafting using exactly one declared `snapshot_type`: `git_commit`, `uploaded_archive`, or `directory_manifest`. Record the Git context when available, archive/manifest digest, and per-file SHA-256 values under `00-project-snapshot/`. Do not create a commit or tag without user authorization. A dirty worktree can be frozen as a deterministic directory manifest; disclose that limitation instead of blocking technical analysis.

External tools are reviewers or search adapters, never co-authors of the canonical case. Read [toolchain-integration.md](references/toolchain-integration.md) before using yjmm10 or Huang.

## Non-negotiable rules

- Never invent technical facts, metrics, prior art, patent numbers, inventors, ownership, or disclosure dates.
- Do not move directly from source code to claims.
- Do not block technical drafting on applicant, inventor, address, ownership, or filing-form data. Use `【待填写】` and collect them after the patent-content package exists.
- Keep engineering provenance, specification support, prior-art disclosure, and priority basis separate.
- Do not combine references to conclude lack of novelty.
- Never promise zero collision. Record searched databases, dates, queries, reviewed documents, coverage limits, and the residual risk of unpublished or missed prior art.
- Treat scores and legal-risk labels as preliminary review aids.
- Keep internal paths, customer data, secrets, and irrelevant trade secrets out of public-facing drafts.
- Never set `FILING_READY`. Distinguish `CONTENT_READY_FOR_ATTORNEY_REVIEW`, `INDEPENDENT_AUDIT`, and `DOCX_PACKAGE_RENDERED`; none means filing-ready.

## Workflow

1. Complete project/title intake and initialize the canonical case.
2. **Snapshot gate:** inspect code, docs, configuration, tests, benchmarks, issues/decisions, and necessary Git history. Record the accepted snapshot type and hashes without drafting. Detect and exclude secrets, customer data, production addresses, unrelated trade secrets, third-party source, dependencies, and build artifacts. Record project dates, disclosure history, and contributors as filing-context questions that may remain pending unless they change the current technical or novelty judgment.
3. Build `01-code-evidence-map.md` as `code evidence -> processing step -> data/state change -> technical effect`. Reconstruct end-to-end runtime chains, not class/API inventories. Exclude ordinary UI, simple library calls, and known components without technical cooperation.
4. **Evidence gate:** report proven, inferred, missing, and contradicted facts. Ask the highest-impact technical question and wait. Write no claims.
5. Mine 3–5 candidates into `02-invention-candidates.md`. For each record technical problem, mechanism, distinguishing feature combination, effect, evidence, design-around exposure, support strength, and main weakness.
6. Run the first prior-art search for all viable candidates before selecting the main invention. Search each problem, mechanism, feature combination, synonyms, broad/narrow expressions, and IPC/CPC. Write structured `search-records.jsonl` entries containing database, date, query, candidate ID, result count, reviewed references, verified URLs, and coverage limitations. Shannon owns the conclusions; yjmm10 is only an optional search adapter.
7. Rank the candidates after search and record `02-candidate-ranking.json`. If one candidate is clearly superior, select it and continue without a ceremonial confirmation. If scores are close, several applications are justified, or the choice depends on business strategy, explain the alternatives and wait for explicit user confirmation. Check unity and propose separate applications where candidates lack one common special technical feature.
8. Compare 3–10 closest references and create `04-feature-matrix.md`. Do not mosaic references for novelty. For inventive step, identify the closest reference, differences, actual problem, effect, and technical teaching.
9. **Overlap gate:** show the closest overlap and proposed code-supported distinction. Ask the user only about an implementation/effect that remains materially uncertain. If no defensible distinction remains, mark `HIGH_OVERLAP_RISK` and return to another candidate or stop.
10. Draft `05-claims-v1.md`: method independent claim first, layered dependent fallbacks, then supported system/device/medium/program-product categories. Every limitation must trace to the evidence map. Before advancing, run the Chinese claim validator for consecutive numbering, backward-only dependency, alternative multiple dependency, prohibited multiple-to-multiple dependency, and terminal punctuation.
11. **Claim-scope gate:** show the independent-claim feature chain in plain language and wait for approval.
12. Draft `06-specification-v1.md` around Claims V1, including alternatives, parameter ranges, data structures, module interaction, failure paths, deployment variants, and AI model input/output/training details where necessary. Read [patent-eligibility-cn.md](references/patent-eligibility-cn.md), [claim-drafting-cn.md](references/claim-drafting-cn.md), and [specification-cn.md](references/specification-cn.md).
13. Build `07-support-candidates.md` as a pre-Claims-V2 pool of possible limitations, engineering sources, specification passages, effects, and risks. Draft `08-claims-v2.md` from that pool; narrow or remove unsupported limitations. Put every independent-claim limitation on its own line with a consecutive trace label such as `[I1-L1]`, and mirror the exact hierarchy in `08-claims-v2-structure.json`. Validate Claims V2 with the same Chinese claim rules as Claims V1. Remove trace labels only in rendered filing documents.
14. After Claims V2 is fixed, build the definitive `09-claim-support-map.md`. Require exact equality among parsed independent-claim limitation labels, structured limitation IDs, and support-map rows. Each row must map exactly one limitation to engineering provenance, explicit specification support, and a technical effect, with no duplicate, unknown, `unsupported`, or unresolved status.
15. Run the second feature-level search against Claims V2 under `10-final-search/`, again using Shannon analysis plus optional yjmm10 CNIPA results. For each record add `claim_id`, `limitation_ids`, and `search_scope`. Require at least one full-combination query for every independent claim and query coverage for every distinguishing limitation. Recheck novelty, inventive step, conflicting applications, eligibility, support, enablement, unity, fallbacks, and amendment basis.
16. Write Shannon's canonical `11-final-audit.md`. When all technical questions are closed, mark only `CONTENT_READY_FOR_ATTORNEY_REVIEW`; filing-context questions may remain pending.
17. Hand read-only copies to Huang `cn-patent-drafting` for `INDEPENDENT_AUDIT`. Huang must not select a new invention, rewrite canonical facts, or silently change claims. Reconcile every substantive finding in Shannon, then render the separate DOCX package. Mark `DOCX_PACKAGE_RENDERED` only after every required file is a nontrivial OOXML ZIP containing `[Content_Types].xml`, a valid nonempty `word/document.xml`, and a distinct required document subject. A Chinese patent attorney still performs the filing review.

## User experience and internal stages

Run evidence extraction, mining, search, Claims V1, specification, Claims V2, and review as internal stages. Do not require the user to operate `discover`, `analyze`, `draft`, candidate IDs, or state labels.

At every user-facing pause, state four things concisely:

1. current stage;
2. confirmed findings;
3. the single most important unresolved point;
4. what will happen after the user answers.

Never silently convert an uncertainty into a claim limitation. Never treat user silence as confirmation. If the user explicitly requests a complete draft in one turn, still stop at any material uncertainty gate; speed does not authorize fabrication. If no material uncertainty exists at a gate, state that briefly and advance without asking a ceremonial question.

After delivering a draft package, guide the user through technical confirmation, disclosure-history verification, evidence supplementation, drawing preparation, and professional review. Ask the next highest-priority question in the same response.

## Canonical case structure

Create and maintain:

```text
patent-case/
├── case-status.json
├── context-ledger.md
├── 00-project-snapshot/
├── 01-code-evidence-map.md
├── 02-invention-candidates.md
├── 02-candidate-ranking.json
├── 03-prior-art-search/
│   ├── shannon/
│   ├── yjmm10/
│   └── search-records.jsonl
├── 04-feature-matrix.md
├── 05-claims-v1.md
├── 06-specification-v1.md
├── 07-support-candidates.md
├── 08-claims-v2.md
├── 08-claims-v2-structure.json
├── 09-claim-support-map.md
├── 10-final-search/
│   ├── shannon/
│   ├── yjmm10/
│   └── search-records.jsonl
├── 11-final-audit.md
└── filing-package/
    ├── huang-audit/
    └── docx/
```

Keep `case-status.json`, the context ledger, and canonical numbered artifacts under Shannon control. Use `python -m patent_skill.cli advance-stage ...` so validators enforce the ordered stage history; do not edit the current stage by hand. Never call the package filing-ready. Missing applicant/address/form data may remain placeholders; unresolved technical or support facts must respect the content gates.

## Reference routing

- Filing context, disclosure, priority, and confidentiality: [filing-context-cn.md](references/filing-context-cn.md)
- Eligibility and AI/data issues: [patent-eligibility-cn.md](references/patent-eligibility-cn.md), [ai-disclosure-cn.md](references/ai-disclosure-cn.md)
- Search, novelty, inventive step, and conflicting applications: [prior-art-search.md](references/prior-art-search.md), [novelty-analysis-cn.md](references/novelty-analysis-cn.md), [inventive-step-cn.md](references/inventive-step-cn.md), [conflicting-applications-cn.md](references/conflicting-applications-cn.md)
- Unity and priority: [portfolio-unity-cn.md](references/portfolio-unity-cn.md), [priority-basis-cn.md](references/priority-basis-cn.md)
- Claims, specification, abstract, and amendments: [claim-drafting-cn.md](references/claim-drafting-cn.md), [specification-cn.md](references/specification-cn.md), [abstract-cn.md](references/abstract-cn.md), [amendment-basis-cn.md](references/amendment-basis-cn.md)
- Final review: [review-rules.md](references/review-rules.md), [disclosure-redaction.md](references/disclosure-redaction.md)
- Canonical workspace and evidence freeze: [case-workspace.md](references/case-workspace.md)
- yjmm10/Huang handoffs: [toolchain-integration.md](references/toolchain-integration.md)

Use scripts for deterministic checks. Run `python -m patent_skill.cli --help` for the CLI.
