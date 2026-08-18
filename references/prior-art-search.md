# Documented prior-art search

Search Chinese and English problem, mechanism, feature-combination, synonym, broader/narrower, and IPC/CPC terms. Record database, date, searcher, exact query, result count, screening method, reviewed sections, and reference verification status. Absence from search results is not proof that no reference exists.

## Title and overlap protocol

1. Ask whether the user has a proposed patent title. Use it as an intent signal and query seed only.
2. Search the exact title and close variants, then search the underlying technical problem, input/output data, processing mechanism, feature combination, effects, and IPC/CPC classes in Chinese and English.
3. Review titles and abstracts for screening, but decide relevance from the description and claims.
4. Build a claim-feature matrix against each close reference. For novelty, compare the complete claim with one reference at a time. For inventive step, identify the closest prior art, distinguishing features, actual technical problem, and technical teaching.
5. If overlap is high, search code evidence for a genuine interacting feature combination that changes the technical solution or effect. Re-run the search against the revised combination.
6. Never evade prior art by changing only the title, terminology, field label, or claim category.
7. If no defensible code-supported distinction remains, mark the candidate `HIGH_OVERLAP_RISK` and do not draft it as the recommended main invention.
8. Confirm the final title only after Claims V2. The title must concisely reflect the protected subject and claim type; title uniqueness is not a patentability test.

## Coverage statement

Every search report must state that database coverage, indexing delays, language choices, unpublished applications, and search error create residual risk. Report `LOW`, `MEDIUM`, or `HIGH` overlap risk within the documented search scope; never claim that collision is impossible.

Use `synthetic-test-fixture` only in tests/demos; never present it as production prior art.
