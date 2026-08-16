# patent-skill

> Turn R&D evidence into traceable, reviewable patent drafting assets.

Repository: [shannonchen37/patent-skill](https://github.com/shannonchen37/patent-skill)

Patent-Skill is an open-source Agent Skill and deterministic validation toolkit for Chinese software, algorithm, AI, and computer-implemented invention workflows.

```text
R&D Evidence
  → Filing Context / Rights / Disclosure
  → Repository Understanding
  → Technical Abstraction
  → Patent Eligibility & Excluded Subject Matter
  → Invention Mining
  → Engineering Provenance
  → Preliminary Search and Portfolio / Unity
  → Inventor Interview and Invention Brief
  → Preliminary Claim Skeleton (CS01)
  → Documented Prior-Art Search
  → Feature-Combination Novelty / Inventive Step
  → Claim Strategy and Claims V1
  → Claim-by-Claim Recheck and Claims V1 Unity Review
  → Specification / Embodiments and Claims V2
  → Specification / Priority / Amendment Basis
  → Abstract / Drawing Review
  → Final Claims V2 Search / Eligibility / Unity Recheck
  → Inventorship / Ownership and Redaction Review
  → Pre-Filing Freeze
  → READY_FOR_ATTORNEY_REVIEW
```

There are multiple review passes because search initially needs a stable feature combination, while legal-risk analysis ultimately concerns the actual claim text. Claims V2 may change after the specification is drafted, so the final claim set is checked again.

## What it does

- Safely scans repositories and extracts symbols.
- Separates engineering provenance, specification support, prior-art disclosure, and priority basis.
- Guides technical-solution, excluded-subject-matter, novelty, inventive-step, unity, AI-disclosure, and amendment-basis reviews.
- Versions claim and search snapshots with content hashes.
- Validates Chinese claim dependencies, abstract length, workspace state, support matrices, and redaction.
- Renders an `attorney-review-draft.docx` when the optional DOCX dependency is installed.

## Why it exists

Ordinary AI patent writing loses the connection between an asserted feature and its engineering source. This project makes that relationship explicit without confusing internal evidence with legal support or prior-art disclosure.

## Installation

Python 3.11 or later is required.

```bash
python -m pip install -e .
python -m pip install -e '.[dev,docx]'
```

## Quick start

```bash
patent-skill init-context
patent-skill scan ./examples/adaptive-compute-scheduler --output ./patent-workspace
patent-skill status ./patent-workspace
patent-skill validate ./examples/adaptive-compute-scheduler/patent-workspace
```

Invoke `$patent-skill discover`, `analyze P001`, `draft P001`, or `review P001` in an Agent Skill-compatible environment. A pre-search draft must remain visibly marked and cannot advance to review-ready.

## Four separate mappings

| Mapping | Question answered |
|---|---|
| Engineering provenance | Where did the feature come from in R&D materials? |
| Specification support | Where does the filed draft support the claim feature? |
| Prior-art disclosure | Where does a reviewed reference disclose the feature? |
| Priority basis | Does the priority document support the claim solution? |

One mapping never proves another.

## Current scope

Implemented: Skill routing, repository scanning, secret exclusion, Python AST and safe symbol fallback, core schemas, claim/search snapshots, novelty non-mosaicing logic, final claim feature-diff checks, workspace state guard, CN claim/abstract/background/support/amendment/redaction validators, demo artifacts, tests, and optional DOCX rendering.

Agent-guided rather than provider-automated: invention mining, search-query generation, documented search import, inventive-step reasoning, specification drafting, priority and unity analysis, and final professional-review preparation.

Not implemented: Google Patents, Espacenet, or CNIPA provider APIs; automatic legal determinations; CNIPA electronic filing; office-action management.

## Ruleset metadata

The demo manifest uses jurisdiction `CN`, ruleset date `2026-01-01`, and links to the PRC Patent Law, Implementing Regulations, and the 2026 Patent Examination Guidelines amendment. Rules can change; review the sources before relying on a workflow.

## Privacy

The scanner excludes common secret files and oversized/binary files. Source paths and evidence annotations default to internal-only and are stripped from DOCX exports. This does not replace organizational security, confidentiality, employee-IP, data-protection, or model-use policies. Do not upload confidential code to a third-party model without authorization.

## Legal and professional disclaimer

Patent-Skill is an engineering analysis and patent drafting assistant. It does not provide legal advice and does not make final determinations regarding patentability, novelty, inventive step, inventorship, ownership, priority entitlement, filing strategy, confidentiality obligations, regulatory compliance, or legal validity. Patent applications and filing decisions should be reviewed by qualified patent professionals.

Patent-Skill 是研发分析和专利撰写辅助工具。本项目不提供法律意见，也不对专利性、新颖性、创造性、发明人身份、权属、优先权、申请策略、保密审查义务、数据合规或专利法律效力作最终判断。在提交专利申请或据此作出法律决策前，应由具备相应专业能力的专利专业人员进行审查。

## Development

```bash
pytest
ruff check .
python /path/to/skill-creator/scripts/quick_validate.py .
```

See [architecture](docs/architecture.md), [workflow](docs/workflow.md), [contributing](CONTRIBUTING.md), and [security](SECURITY.md).
