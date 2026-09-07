# Workflow

The canonical state machine remains stable, but methodology version 2 changes what the early gates prove:

```text
Understand first
  snapshot → E/TD provenance → technical model → F features
Search second
  landscape search → candidates → targeted search → ranking
Invent or improve third
  feature matrix → optional screened SP proposal → user decision → optional implementation
Draft last
  Claims V1 → specification → Claims V2 → support → final search → audits → DOCX
```

## Invariants

1. A user identifies a real target project separate from the Skill package.
2. Freeze immutable `S001` before analysis; every `E###` binds to a path/hash in the current snapshot.
3. Build a complete Project Technical Model before formal candidates. It must separate core mechanisms, ordinary components, business/UI elements, dependencies, and uncertainties.
4. Build `F###` Search Features from that model. Every feature retains E/approved-TD provenance and search terminology.
5. Landscape search covers every `F###` and material combination before provisional patent opportunities. Candidate-targeted search covers every viable opportunity before it can be formally ranked or selected.
6. A renamed title never cures overlap; compare technical features and solutions. Multiple references are not mosaiced to reject novelty.
7. Classify uncertainty as Fact Gap or Design Gap. A Fact Gap asks what the project already does. A Design Gap may receive an `SP###` proposal only after relevant search.
8. Candidate Completion remains parameter-light. `PROPOSED_DEFAULT` is allowed only in an SP reference proposal and is never fact or claim support.
9. An SP must be searched before user decision. Rejected, uncertain, or pending proposals create no usable TD. High overlap makes an SP ineligible as a novelty/inventive-step distinction, but explicit `real_engineering_value` authority may still permit implementation.
10. Proposal adoption, code implementation authorization, and Git commit authorization are independent. Adoption/modification may create an active, enablement-sufficient TD; it authorizes neither code changes nor commits.
11. Any real implementation creates `S002+` and new E bound to `snapshot_id + engineering_iteration_id + proposal_id`. Failed validation is recorded on both E and iteration and blocks the validated Gate; later sufficient validation may promote it. All older snapshots remain, and downstream analysis is archived and invalidated.
12. Claims remain last. Claims V1 drive the specification; Claims V2 and every dependent added limitation receive exact support mapping.
13. Every candidate and independent claim retains at least one E anchor. An SP alone can never support a limitation.
14. Final search is bound to Claims V2 hashes and covers each independent combination and distinguishing limitation.
15. SP, TD, and Engineering Iteration record origin and human contributions. Final audit distinguishes frozen-implementation, TD-only, and validated Patent Engineering provenance and always requires separate inventorship review without deciding inventorship.
16. Shannon is the only canonical writer. yjmm10 supplies optional search evidence; Huang supplies independent audit and DOCX only.
17. Applicant/form data are deferred. The software never promises zero collision or emits `FILING_READY`.

## State mapping

The enforced sequence is unchanged for compatibility:

`PROJECT_SNAPSHOT → EVIDENCE_MAP → INVENTION_CANDIDATES → FIRST_SEARCH → CANDIDATE_RANKING → FEATURE_MATRIX → CLAIMS_V1 → SPECIFICATION_V1 → SUPPORT_CANDIDATES → CLAIMS_V2 → CLAIM_SUPPORT_MAP → FINAL_SEARCH → APPLICATION_DRAFT → FINAL_AUDIT → CONTENT_READY_FOR_ATTORNEY_REVIEW → INDEPENDENT_AUDIT → DOCX_PACKAGE_RENDERED`

- `EVIDENCE_MAP` now also gates the Project Technical Model, Search Feature Model, landscape search, and landscape feature matrix.
- `INVENTION_CANDIDATES` stores provisional, stable-ID patent opportunities so targeted searches can bind to them; it does not select the formal main invention.
- `FIRST_SEARCH` is candidate-targeted search, not the first time searching the field.
- `CANDIDATE_RANKING` formally ranks/selects only after targeted search and requires explicit search bindings plus engineering-completeness analysis.
- `FEATURE_MATRIX` gates optional Patent Engineering proposals and implementation iterations before Claims V1.
- Later states retain the existing claim, support, hash, audit, revision, and OOXML gates.

Legacy cases without `methodology_version: 2` retain their prior validation behavior. New cases use version 2.
