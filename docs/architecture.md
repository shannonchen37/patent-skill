# Architecture

`SKILL.md` owns judgment-heavy orchestration. The Python package supplies deterministic snapshots, schemas, state transitions, revisions, claim/search/audit gates, clean filing rendering, export, and OOXML validation.

## Canonical provenance

```text
S### = immutable project snapshot
E### = engineering evidence bound to one current-snapshot file hash
TD### = user-confirmed, enablement-sufficient technical disclosure
F### = searchable feature derived from E/approved TD
SP### = searched Patent Engineering reference proposal; never evidence itself
Prior Art = external disclosure, not project provenance
Specification Support = application-text basis, not engineering proof
```

Candidate Completion is a parameter-light question hypothesis. `PROPOSED_DEFAULT` exists only inside SP proposals. Neither can enter claims, figures, or support maps.

## Data flow

```text
S snapshot
  ├─ E evidence ───────────────┐
  └─ confirmed TD ─────────────┤
                               ↓
                    Project Technical Model
                               ↓
                         F Search Features
                               ↓
                        Landscape Search
                               ↓
          Candidates → Targeted Search → Ranking
                               ↓
              optional SP → screening → user decision
                  ├─ TD-only drafting path
                  └─ authorized code implementation
                         ↓
                 new S + new E + formal revision
                               ↓
                   repeat understanding and search
                               ↓
                  Claims → Specification → Audits
```

## Staleness boundary

`record_engineering_iteration()` accepts only a screened, adopted/modified proposal with separate implementation authority and real changed files. It freezes the next snapshot even when validation fails, binds each new E to snapshot/iteration/proposal, records `passed` or `failed`, archives downstream artifacts, and returns to `EVIDENCE_MAP`. Failed evidence is factual but cannot pass the validated-implementation Gate. Later sufficient validation may promote the same frozen iteration. Old snapshots remain immutable.

Adoption, code-change authority, and Git commit authority are stored separately. High-overlap proposals set `patent_distinction_eligible = false`; implementation is permitted only under explicit real-engineering-value authority and cannot support a distinguishing limitation. One searched, substantive-mechanism redesign is permitted; terminology/parameter/form changes are not.

SP, TD, and Engineering Iteration each carry origin and human-contribution records. Final Audit lists all such source IDs and sets inventorship to `NOT_DETERMINED`; the Skill never converts those records into an inventorship conclusion.

Claims-V2 search sessions bind to claim/structure hashes. Application drafts and final/independent audits bind to exact source hashes. A changed upstream object therefore cannot silently reuse downstream conclusions.

## Canonical ownership

Shannon `patent-skill` is the only canonical writer. JSON is authoritative where JSON/Markdown pairs coexist. yjmm10/patent-skills is an optional search adapter. HuangXinzhe/cn-patent-drafting receives stable read-only content after content readiness and returns independent findings/DOCX; it does not reselect the invention or overwrite case facts.
