---
name: patent-skill
description: Guide the user to upload or select target R&D project code, ask for an optional proposed patent title, then perform evidence extraction, invention mining, mandatory prior-art overlap analysis, claim strategy, and traceable Chinese invention-patent drafting. Use when a user wants to turn a real software, algorithm, AI, or engineering project into a Chinese patent draft, including when project files or a proposed title have not yet been supplied; never analyze the Skill package as the invention.
---

# Patent Skill

Turn R&D evidence into traceable, reviewable patent drafting assets. Never represent an output as legal advice or filing-ready.

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

## Non-negotiable rules

- Never invent technical facts, metrics, prior art, patent numbers, inventors, ownership, or disclosure dates.
- Do not move directly from source code to claims.
- Do not block technical drafting on applicant, inventor, address, ownership, or filing-form data. Use `【待填写】` and collect them after the patent-content package exists.
- Keep engineering provenance, specification support, prior-art disclosure, and priority basis separate.
- Do not combine references to conclude lack of novelty.
- Never promise zero collision. Record searched databases, dates, queries, reviewed documents, coverage limits, and the residual risk of unpublished or missed prior art.
- Treat scores and legal-risk labels as preliminary review aids.
- Keep internal paths, customer data, secrets, and irrelevant trade secrets out of public-facing drafts.
- Never set `FILING_READY`. Stop at `READY_FOR_ATTORNEY_REVIEW`, and only when required artifacts and confirmations exist.

## Workflow

1. Complete project and title intake. Applicant and inventor information is not a content gate.
2. Scan source code, documents, configuration, tests, and history; build a `code evidence -> processing step -> data/state change -> technical effect` map.
3. Abstract complete technical mechanisms and candidate feature combinations. Exclude generic UI, library use, and isolated known components unless they functionally cooperate in the claimed solution.
4. Perform mandatory prior-art searching before choosing the main invention. Read [prior-art-search.md](references/prior-art-search.md), [novelty-analysis-cn.md](references/novelty-analysis-cn.md), and [inventive-step-cn.md](references/inventive-step-cn.md).
5. Compare each candidate against the closest references, identify genuine distinguishing features and technical effects, rank candidates, and split unrelated inventive concepts for unity.
6. Select the strongest defensible combination and create Claims V1 with an independent method claim, layered dependent fallbacks, and appropriate device, storage-medium, and computer-program-product categories.
7. Draft the specification around Claims V1: technical field, background, problem, solution, effects, drawings, embodiments, alternatives, parameters, failure paths, and implementation details. Read [patent-eligibility-cn.md](references/patent-eligibility-cn.md), [claim-drafting-cn.md](references/claim-drafting-cn.md), and [specification-cn.md](references/specification-cn.md).
8. Create Claims V2 from the completed specification and verify every limitation against code evidence and specification support.
9. Re-search Claims V2 and review novelty, inventive step, eligibility, clarity, support, enablement, unity, fallbacks, abstract, drawings, amendment basis, and disclosure redaction.
10. Produce the complete content package first. Put applicant, inventor, ownership, address, disclosure, priority, and foreign-filing items in a separate `【待填写】` checklist for later filing review.

## User experience and internal stages

Run evidence extraction, mining, search, Claims V1, specification, Claims V2, and review as internal stages. Do not require the user to operate `discover`, `analyze`, `draft`, candidate IDs, or state labels. Ask only for a proposed title and for technical facts that are genuinely absent and material to the content; continue with clearly marked assumptions or `【待补充】` fields when safe.

## Required output package

Create a `patent-output/` package containing:

- `01-技术证据地图.md`
- `02-现有技术检索报告.md`
- `03-区别特征矩阵.md`
- `04-权利要求书.md`
- `05-说明书.md`
- `06-说明书摘要.md`
- `07-附图说明.md`
- `08-专利性与支持性复核.md`
- `09-待补充信息.md`

Never call the package filing-ready. Missing applicant or inventor data does not prevent generation of files 01 through 08.

## Reference routing

- Filing context, disclosure, priority, and confidentiality: [filing-context-cn.md](references/filing-context-cn.md)
- Eligibility and AI/data issues: [patent-eligibility-cn.md](references/patent-eligibility-cn.md), [ai-disclosure-cn.md](references/ai-disclosure-cn.md)
- Search, novelty, inventive step, and conflicting applications: [prior-art-search.md](references/prior-art-search.md), [novelty-analysis-cn.md](references/novelty-analysis-cn.md), [inventive-step-cn.md](references/inventive-step-cn.md), [conflicting-applications-cn.md](references/conflicting-applications-cn.md)
- Unity and priority: [portfolio-unity-cn.md](references/portfolio-unity-cn.md), [priority-basis-cn.md](references/priority-basis-cn.md)
- Claims, specification, abstract, and amendments: [claim-drafting-cn.md](references/claim-drafting-cn.md), [specification-cn.md](references/specification-cn.md), [abstract-cn.md](references/abstract-cn.md), [amendment-basis-cn.md](references/amendment-basis-cn.md)
- Final review: [review-rules.md](references/review-rules.md), [disclosure-redaction.md](references/disclosure-redaction.md)

Use scripts for deterministic checks. Run `python -m patent_skill.cli --help` for the CLI.
