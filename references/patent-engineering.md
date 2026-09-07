# Patent Engineering

Patent Engineering is an optional bridge between understanding a real project and drafting claims. It may improve an incomplete candidate, but it must never manufacture evidence or silently rewrite the user's project.

## Gap classification

Classify a material uncertainty before acting:

- **Fact Gap**: an existing-project fact is unknown. Inspect the frozen code, documents, tests, configuration, benchmark material, and relevant history first. If unresolved, ask one factual question and record its source. A narrow candidate completion may help the user understand the question, but it cannot add parameters or become provenance.
- **Design Gap**: the existing implementation is understood, but the candidate lacks a complete, differentiating, robust, or readily claimable mechanism. Search the relevant landscape and candidate first. Then give one parameter-light Candidate Completion followed by a complete reference proposal, rather than asking the user to invent the missing design.

Do not label a weak search result as a Design Gap merely to justify adding features. If current engineering evidence already supports a defensible candidate, proceed without ceremonial Patent Engineering.

## SP proposal contract

Use stable IDs `SP001`, `SP002`, and so on. Each proposal must bind to one candidate, one Design Gap question, source `F###` features, existing `E###` anchors, and proposal-level prior-art search records. It must state:

1. problem and concise mechanism summary;
2. inputs and data representation;
3. ordered processing steps and decision rules;
4. data/state changes and outputs;
5. boundary, conflict, and exception behavior;
6. integration points with the frozen project;
7. direct technical effect and its basis;
8. parameters with provenance;
9. search conclusion and overlap risk.

Parameter provenance is strict:

- `EVIDENCE_BACKED`: already supported by frozen engineering evidence;
- `USER_CONFIRMED`: explicitly supplied or modified by the user;
- `PROPOSED_DEFAULT`: a reference value chosen to make the proposal concrete enough to evaluate.

`PROPOSED_DEFAULT` is allowed only inside `patent-engineering/proposals.json`. It is not a project fact, TD, claim-support source, measured result, or permission to implement. Candidate Completion must remain parameter-light and cannot use proposed defaults.

## Search and decision gate

Before asking for a decision, run a quick but recorded search on the proposal's core combination. Use `search_scope = engineering_proposal`, bind the record to `proposal_id`, and record reviewed references, verified URLs, database/date/query, and limitations.

- Pending or missing search: do not ask for adoption and do not implement.
- High overlap: set `patent_distinction_eligible = false`. Do not use the proposal or resulting TD/E as the novelty or inventive-step distinction. The user may still adopt it and explicitly authorize implementation for real engineering value.
- Low/medium overlap: explain the closest disclosure and residual risk, then ask the user to adopt, modify, reject, or mark uncertain.

Decision consequences:

- **adopt**: create a sufficiently disclosed `TD###`, linked to the Design Gap question and SP;
- **modify**: record every user-changed value as `USER_CONFIRMED`, then create the TD from the modified mechanism;
- **reject** or **uncertain**: create no TD and no claim support;
- silence: remains pending and is never confirmation.

Adoption authorizes patent-case use only. It does not authorize a code change. Code implementation authorization does not authorize a Git commit. Record all three decisions separately with their own source.

A high-overlap proposal may receive one substantive redesign for the same real unresolved problem. The redesign must change the causal technical mechanism, integrate naturally, and receive a new search. Terminology substitution, parameter tuning, claim-category changes, or formal wrapper features do not qualify and must not be used to evade prior art.

## Optional implementation loop

Implementation requires a separate, explicit user instruction. Before editing:

1. confirm the exact adopted/modified SP and authorized scope;
2. create or use an isolated branch/worktree where practical;
3. preserve the original project and existing patent snapshots;
4. implement only the authorized mechanism;
5. run relevant tests, static checks, and domain validation;
6. record validation results accurately, whether they pass or fail.

After validation:

1. create the next immutable snapshot under `00-project-snapshot/snapshots/Snnn/`, even if the implemented code currently fails validation;
2. keep `S001` and every prior snapshot unchanged;
3. create new `E###` records whose paths and SHA-256 values bind simultaneously to `snapshot_id`, `engineering_iteration_id`, and `proposal_id`;
4. record the SP, changed files, authorization source, tests, and new evidence in `patent-engineering/iterations.json`;
5. formally revise to project understanding;
6. archive and invalidate old candidate, search, claim, support, application, and audit artifacts;
7. mark failed E/iterations `validation_status=failed` and block the validated-implementation Gate; after tests pass or another sufficient validation is recorded, promote them to validated;
8. rebuild the technical model and repeat landscape/candidate search before drafting.

Never patch code solely to make an unsupported claim appear implemented. An implementation is valuable only if it is a genuine, user-authorized engineering improvement. Failed validation does not erase the fact that code exists, but it prevents reliance on that implementation as validated Patent Engineering.

Record origin and human-contribution provenance for the proposal, resulting TD, and implementation iteration. These records are inputs to a later inventorship review, not a Skill determination of who is or is not an inventor.

## Final provenance disclosure

The final audit distinguishes:

- limitations supported by the current frozen implementation;
- limitations supported only by active, enablement-sufficient TDs;
- limitations supported by new evidence produced through a validated Patent Engineering iteration.

An SP by itself never appears in the claim-support map. The output remains `CONTENT_READY_FOR_ATTORNEY_REVIEW`, never filing-ready.
