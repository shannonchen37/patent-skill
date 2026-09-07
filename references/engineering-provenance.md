# Engineering provenance

Engineering provenance answers where an asserted feature came from. It is not specification support, prior-art disclosure, proof of patentability, or proof of inventorship. Classify each evidence item as `internal-only`, `drafting-usable`, `filing-disclosable`, or `redaction-required`.

Canonical `E###` records always point to a frozen project file and SHA-256 and use only `code-supported`, `document-supported`, or `experiment-supported`. A developer or inventor statement is never engineering evidence. Record a confirmed design as `TD###` in `01-technical-disclosures.json`, link it to the source question, and require sufficient implementation detail before downstream use.

Patent Engineering E additionally binds `snapshot_id + engineering_iteration_id + proposal_id`. Validation is a separate axis: real frozen code may be `validation_status=failed` and remain truthful E, but it cannot satisfy the validated-implementation Gate until later sufficient validation. `novelty_distinction_eligible=false` prevents high-overlap SP-derived TD/E from serving as a novelty or inventive-step distinction.

SP, TD, and Engineering Iteration origin records describe known human and Agent contributions only. They are not proof of inventorship. Carry them into Final Audit and require a separate professional inventorship review.

Candidate completions are Agent hypotheses. They remain in `context-questions.json` and cannot support candidates, feature matrices, claims, figures, specifications, or audits unless the user confirms/modifies the mechanism and it is promoted into an enablement-sufficient TD.

Record the technical-effect basis as `measured`, `observed`, or `mechanism-derived`. Quantified gains require measured project evidence; do not convert an expected or aspirational effect into a case fact.
