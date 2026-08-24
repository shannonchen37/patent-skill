# Workflow

The canonical workflow is defined in `SKILL.md`. Key invariants:

1. A user must identify a target project separate from the Skill package; without one, guide upload or workspace selection.
2. Ask for an optional proposed patent title. If none exists, mine and propose one after selecting a searched feature combination.
3. The Skill's own files are tooling and never the patent subject.
4. Freeze an evidence snapshot and keep one canonical `patent-case/` before analysis.
5. Build the code-evidence map and 3–5 candidate feature combinations before claims.
6. Search all viable candidates before ranking and selecting the main invention. Require user confirmation only when the ranking is strategically ambiguous.
7. A renamed title never cures technical overlap; compare claims and technical solutions.
8. Multiple references are not mosaiced to reject novelty.
9. Claims V1 drive the specification; a support-candidate pool precedes Claims V2; the definitive claim-support map follows Claims V2 and precedes the final search.
10. Shannon is the only canonical writer. yjmm10 supplies optional CNIPA search evidence; Huang supplies final independent audit and DOCX only.
11. Applicant and inventor form data are deferred placeholders, not early content-generation gates.
12. The software never promises zero collision or emits `FILING_READY`.
13. The workflow is progressive, not end to end: pause at evidence, strategic-direction, overlap, claim-scope, and completion gates whenever a material technical uncertainty exists.
14. Ask one focused question by default and no more than three per turn; explain the evidence, uncertainty, and patent impact.
15. Never treat silence as confirmation or convert a material inference into a claim limitation.
16. Record confirmations and unresolved conflicts in `context-ledger.md`, then end every delivery with the next highest-priority question.
17. Separate technical-content readiness, independent audit, and DOCX rendering. Never emit `FILING_READY`.
