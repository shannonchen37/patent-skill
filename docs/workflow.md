# Workflow

The canonical workflow is defined in `SKILL.md`. Key invariants:

1. A user must identify a target project separate from the Skill package; without one, guide upload or workspace selection.
2. Ask for an optional proposed patent title. If none exists, mine and propose one after selecting a searched feature combination.
3. The Skill's own files are tooling and never the patent subject.
4. Freeze an evidence snapshot and keep one canonical `patent-case/` before analysis.
5. Build schema-validated canonical JSON for the code-evidence map and 3–5 candidate feature combinations; generate Markdown views rather than maintaining two sources.
6. Search all viable candidates before ranking and selecting the main invention. Require user confirmation only when the ranking is strategically ambiguous.
7. A renamed title never cures technical overlap; compare claims and technical solutions.
8. Multiple references are not mosaiced to reject novelty.
9. Validate Claims V1 and Claims V2 with the Chinese claim validator. Claims V1 drive the specification; a support-candidate pool precedes Claims V2.
10. Mirror every independent Claims-V2 limitation in `08-claims-v2-structure.json`; require exact equality with the definitive support-map rows.
11. Require a Claims-V2 combination search for every independent claim and coverage for every distinguishing limitation.
12. Build a synchronized final application draft after the second search: deterministic final claims, final specification, abstract, drawings description, hashes, and per-limitation sync records.
13. Require structured final-audit conclusions with evidence, residual risk, and recommended action; prose placeholders cannot pass.
14. Shannon is the only canonical writer. yjmm10 supplies optional CNIPA search evidence; Huang supplies final independent audit and DOCX only.
15. Applicant and inventor form data are deferred placeholders, not early content-generation gates.
16. The software never promises zero collision or emits `FILING_READY`.
17. The workflow is progressive, not end to end: pause whenever a material technical uncertainty exists.
18. Store questions as structured objects. Only an answer plus provenance resolves a question; an unresolved blocking technical question prevents content readiness.
19. Use formal revision to archive stale downstream artifacts when later search or review changes an earlier stage.
20. Separate technical-content readiness, independent audit, and valid OOXML rendering.
