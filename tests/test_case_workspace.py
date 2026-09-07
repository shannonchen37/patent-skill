import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from patent_skill.case_workspace import (
    BASE_REQUIRED_DOCX_SUBJECTS,
    CASE_STAGE_ORDER,
    _application_hash_snapshot,
    _validate_claims_stage,
    _validate_docx_file,
    _validate_evidence_map,
    _validate_figures,
    _validate_final_audit,
    _validate_final_search,
    _validate_independent_audit,
    _validate_patent_engineering,
    _validate_support_map,
    advance_stage,
    authorize_engineering_commit,
    authorize_engineering_implementation,
    export_case_package,
    init_case_workspace,
    record_engineering_iteration,
    required_docx_subjects,
    resolve_case_question,
    resolve_engineering_proposal,
    revise_case_stage,
    validate_case_workspace,
    validate_engineering_iteration,
)
from patent_skill.schema_validation import validate_schema


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _search_record(candidate: str = "P001", scope: str = "candidate_targeted") -> str:
    return (
        json.dumps(
            {
                "record_id": candidate.replace("P", "S"),
                "database": "CNIPA",
                "search_date": "2026-08-24",
                "query": "状态反馈 调度",
                "candidate_id": candidate,
                "search_scope": scope,
                "result_count": 3,
                "reviewed_reference_ids": ["CN123"],
                "verified_urls": ["https://example.test/CN123"],
                "coverage_limitations": "公开网页覆盖有限",
            },
            ensure_ascii=False,
        )
        + "\n"
    )


def _final_search_record(
    claim_id: str = "I1",
    limitation_ids: tuple[str, ...] = ("I1-L1",),
    scope: str = "claim_combination",
) -> str:
    record = json.loads(_search_record().strip())
    record.update(
        {
            "claim_id": claim_id,
            "limitation_ids": list(limitation_ids),
            "search_scope": scope,
        }
    )
    return json.dumps(record, ensure_ascii=False) + "\n"


def _write_valid_docx(path: Path, body: str = "有效专利文档正文") -> None:
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{body}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", document)
        archive.writestr("docProps/validation-padding.bin", bytes(range(256)) * 8)


def _complete_application(case: Path) -> None:
    application = case / "12-application"
    claims_v2 = (case / "08-claims-v2.md").read_text(encoding="utf-8")
    claims_final = (application / "claims-final.md").read_text(encoding="utf-8")
    specification = "# 最终说明书\n\n本实施例执行步骤A，实现降低时延的技术效果。\n"
    abstract = "# 说明书摘要\n\n本发明公开一种执行步骤A以降低处理时延的方法。\n"
    drawings = "# 附图说明\n\n图1为本发明方法的流程图。\n"
    _write(application / "specification-final.md", specification)
    _write(application / "abstract.md", abstract)
    _write(application / "drawings-description.md", drawings)

    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    _write(
        application / "application-metadata.json",
        json.dumps(
            {
                "source_claims_v2_sha256": digest(claims_v2),
                "claims_final_sha256": digest(claims_final),
                "specification_final_sha256": digest(specification),
                "abstract_sha256": digest(abstract),
                "drawings_description_sha256": digest(drawings),
                "drawings": {
                    "required": False,
                    "reason": "文字足以清楚完整说明本测试技术方案",
                    "abstract_figure_required": False,
                    "abstract_figure_id": None,
                },
                "limitation_sync": [
                    {
                        "limitation_id": "I1-L1",
                        "specification_sections": ["实施例"],
                        "terminology_synced": True,
                        "protected_subject_synced": True,
                        "embodiment_supported": True,
                        "technical_effect_supported": True,
                        "drawing_reference_status": "checked",
                        "status": "synced",
                    }
                ],
            },
            ensure_ascii=False,
        ),
    )


def _complete_evidence(case: Path) -> None:
    snapshot = json.loads(
        (case / "00-project-snapshot" / "snapshot-manifest.json").read_text(encoding="utf-8")
    )
    source = snapshot["files"][0]
    _write(
        case / "01-code-evidence-map.json",
        json.dumps(
            {
                "evidence": [
                    {
                        "evidence_id": "E001",
                        "source": {"path": source["path"], "sha256": source["sha256"]},
                        "processing_step": "计算任务处理状态",
                        "state_change": "将等待状态更新为完成状态",
                        "technical_effect": "降低任务处理等待时延",
                        "effect_basis": "mechanism-derived",
                        "status": "code-supported",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )
    technical_model = {
        "technical_problem": {
            "statement": "降低任务处理等待时延",
            "engineering_evidence_ids": ["E001"],
        },
        "system_boundary": {
            "statement": "任务状态处理与资源分配模块",
            "engineering_evidence_ids": ["E001"],
        },
        "inputs": [{"statement": "待处理任务状态", "engineering_evidence_ids": ["E001"]}],
        "outputs": [{"statement": "完成状态与资源分配结果", "engineering_evidence_ids": ["E001"]}],
        "core_modules": [{"statement": "状态反馈模块", "engineering_evidence_ids": ["E001"]}],
        "processing_chains": [
            {"statement": "任务状态到反馈式资源分配", "engineering_evidence_ids": ["E001"]}
        ],
        "data_state_transitions": [
            {"statement": "等待状态更新为完成状态", "engineering_evidence_ids": ["E001"]}
        ],
        "technical_effects": [
            {"statement": "降低任务处理等待时延", "engineering_evidence_ids": ["E001"]}
        ],
        "core_mechanisms": [
            {
                "statement": "基于状态反馈动态调整资源",
                "reason": "直接改变任务分配状态",
                "engineering_evidence_ids": ["E001"],
            }
        ],
        "ordinary_components": [
            {
                "statement": "Python 函数调用",
                "reason": "属于通用语言机制",
                "engineering_evidence_ids": ["E001"],
            }
        ],
        "business_ui_components": [],
        "third_party_dependencies": [],
        "uncertainties": [],
    }
    _write(
        case / "project-understanding" / "technical-model.json",
        json.dumps(technical_model, ensure_ascii=False),
    )
    feature_model = {
        "features": [
            {
                "feature_id": "F001",
                "statement": "基于状态反馈动态调整资源",
                "technical_role": "连接任务状态与资源分配",
                "engineering_evidence_ids": ["E001"],
                "technical_disclosure_ids": [],
                "search_terms": {
                    "problem": ["任务等待时延"],
                    "mechanism": ["状态反馈资源分配"],
                    "synonyms": ["反馈调度"],
                    "broader": ["资源调度"],
                    "narrower": ["任务状态反馈调度"],
                    "ipc_cpc": ["G06F9/50"],
                },
            }
        ],
        "combination_hypotheses": [],
    }
    _write(
        case / "project-understanding" / "search-feature-model.json",
        json.dumps(feature_model, ensure_ascii=False),
    )
    landscape_record = json.loads(_search_record("LANDSCAPE", "landscape_feature"))
    landscape_record.update({"record_id": "S900", "feature_ids": ["F001"]})
    landscape_record.pop("candidate_id")
    _write(
        case / "landscape-search" / "search-records.jsonl",
        json.dumps(landscape_record, ensure_ascii=False) + "\n",
    )
    _write(
        case / "landscape-search" / "prior-art-feature-matrix.json",
        json.dumps(
            {
                "features": [
                    {
                        "feature_id": "F001",
                        "search_record_ids": ["S900"],
                        "references": {"CN123": "partial"},
                        "crowding": "medium",
                        "opportunity_note": "反馈组合仍需进行候选级检索",
                    }
                ],
                "landscape_conclusion": "单一反馈机制较常见，应检索具体组合",
            },
            ensure_ascii=False,
        ),
    )


def _complete_candidates(case: Path) -> None:
    candidates = []
    for index in range(1, 4):
        candidates.append(
            {
                "candidate_id": f"P{index:03d}",
                "title": f"候选技术方案{index}",
                "technical_problem": "现有任务处理存在较高等待时延",
                "mechanism": "依据任务状态执行反馈式资源分配",
                "distinguishing_features": ["基于状态反馈动态调整资源"],
                "technical_effects": ["降低任务排队等待时延"],
                "effect_basis": "mechanism-derived",
                "engineering_evidence_ids": ["E001"],
                "technical_disclosure_ids": [],
                "source_feature_ids": ["F001"],
                "landscape_search_record_ids": ["S900"],
                "implementation_gap": None,
                "risk": "medium",
            }
        )
    _write(
        case / "02-invention-candidates.json",
        json.dumps({"candidates": candidates}, ensure_ascii=False),
    )


def _complete_matrix(case: Path) -> None:
    _write(
        case / "04-feature-matrix.json",
        json.dumps(
            {
                "features": [
                    {
                        "feature_id": "F001",
                        "feature": "基于状态反馈动态调整资源",
                        "engineering_evidence_ids": ["E001"],
                        "technical_disclosure_ids": [],
                        "references": {"CN123": "partial"},
                        "distinguishing_effect": "降低任务排队等待时延",
                        "effect_basis": "mechanism-derived",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )


def _ranking_item(candidate_id: str, disposition: str = "reserve") -> dict:
    return {
        "candidate_id": candidate_id,
        "prior_art_crowding": "medium",
        "distinguishing_combination": "状态反馈与动态资源分配组合",
        "technical_effect": "降低任务排队等待时延",
        "engineering_support": "strong",
        "td_support": "none",
        "implementation_completeness": "complete",
        "design_around_risk": "medium",
        "protection_breadth": "moderate",
        "requires_patent_engineering": False,
        "implementation_gap": None,
        "split_application_recommended": False,
        "targeted_search_record_ids": [candidate_id.replace("P", "S")],
        "disposition": disposition,
    }


def _engineering_disclosure() -> dict:
    return {
        "disclosure_id": "TD001",
        "question_id": "Q003",
        "statement": "在状态反馈后应用用户确认的阈值再执行资源分配",
        "source_role": "developer",
        "implementation_status": "designed_not_implemented",
        "mechanism": {
            "input": "任务状态",
            "processing": ["计算状态指标", "按阈值选择资源分配路径"],
            "state_change": "待分配状态变为带有资源路径的状态",
            "output": "资源分配结果",
            "integration": "在现有状态反馈模块与资源分配模块之间执行",
            "conflict_and_exception_handling": "阈值冲突时采用保守路径并记录原因",
        },
        "technical_effect": {
            "statement": "减少不适配资源分配造成的等待",
            "effect_basis": "mechanism-derived",
            "evidence_refs": [],
        },
        "enablement": {"status": "sufficient", "missing_details": []},
        "confirmed_via": "user_response",
        "confirmed_at": "2026-09-07T00:00:00+00:00",
        "lifecycle_status": "active",
        "superseded_by": None,
        "origin_provenance": {
            "origin_type": "agent_proposal_adopted",
            "human_contributions": [
                {
                    "contributor_ref": "USER_UNRESOLVED",
                    "contribution": "确认采用该机制",
                    "source": "user-response",
                }
            ],
            "source": "SP001 + user-response",
            "inventorship_review_required": True,
        },
    }


def _engineering_proposal(*, screened: bool = True, overlap: str = "low") -> dict:
    return {
        "proposal_id": "SP001",
        "candidate_id": "P001",
        "design_gap_question_id": "Q003",
        "status": "screened" if screened else "proposed",
        "problem": "当前反馈机制缺少可实施的资源选择规则",
        "summary": "在状态反馈与资源分配之间加入阈值选择机制",
        "inputs": ["任务状态"],
        "data_representation": ["状态指标与阈值记录"],
        "processing_steps": ["计算状态指标", "比较阈值", "选择资源路径"],
        "decision_rules": ["指标超过阈值时使用低负载资源"],
        "state_changes": ["待分配状态转为已选择资源路径状态"],
        "outputs": ["资源路径选择结果"],
        "boundary_handling": ["指标缺失时使用保守路径"],
        "conflict_handling": ["多路径冲突时选择负载最低路径"],
        "integration_points": ["状态反馈模块与资源分配模块之间"],
        "technical_effect": "减少不适配资源分配造成的等待",
        "parameters": [
            {
                "name": "load_threshold",
                "value": 0.8,
                "provenance": "PROPOSED_DEFAULT",
                "rationale": "用于形成可讨论的参考实现，不视为项目事实",
            }
        ],
        "source_feature_ids": ["F001"],
        "engineering_evidence_ids": ["E001"],
        "technical_disclosure_ids": [],
        "screening": {
            "status": "completed" if screened else "pending",
            "search_record_ids": ["S901"] if screened else [],
            "overlap_risk": overlap if screened else "unknown",
            "conclusion": "未发现完整公开该组合" if overlap != "high" else "关键组合高度重合",
            "patent_distinction_eligible": screened and overlap != "high",
        },
        "user_decision": {"decision": "pending", "source": None, "decided_at": None},
        "implementation": {
            "authorized": False,
            "authorization_source": None,
            "authorization_purpose": None,
            "status": "not_requested",
        },
        "commit_authorization": {
            "authorized": False,
            "authorization_source": None,
            "status": "not_requested",
            "commit_sha": None,
        },
        "origin_provenance": {
            "origin_type": "agent_proposed",
            "human_contributions": [],
            "source": "patent-skill analysis",
            "inventorship_review_required": True,
        },
        "redesign_of": None,
        "redesign_basis": None,
        "redesign_change_type": None,
    }


def _prepare_engineering_case(
    tmp_path: Path, *, screened: bool = True, overlap: str = "low"
) -> tuple[Path, Path]:
    project = tmp_path / "engineering-project"
    project.mkdir()
    (project / "core.py").write_text("def allocate(state):\n    return state\n", encoding="utf-8")
    case = tmp_path / "engineering-case"
    init_case_workspace(case, project)
    advance_stage(case, "EVIDENCE_MAP")
    _complete_evidence(case)
    questions_path = case / "context-questions.json"
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    questions["questions"].append(
        {
            "id": "Q003",
            "category": "technical",
            "question": "是否采用阈值式资源选择机制？",
            "gap_type": "DESIGN_GAP",
            "blocking": True,
            "impact": "决定候选方案能否形成可实施的完整机制",
            "status": "open",
            "resolution": None,
            "evidence_refs": ["E001"],
            "source": None,
            "candidate_completion": {
                "statement": "在状态反馈后按阈值选择资源路径",
                "basis_refs": ["E001"],
                "status": "proposed",
            },
            "resulting_disclosure_ids": [],
        }
    )
    _write(questions_path, json.dumps(questions, ensure_ascii=False))
    advance_stage(case, "INVENTION_CANDIDATES")
    _complete_candidates(case)
    candidates_path = case / "02-invention-candidates.json"
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    candidates["candidates"][0]["implementation_gap"] = "缺少阈值式资源选择规则"
    _write(candidates_path, json.dumps(candidates, ensure_ascii=False))
    advance_stage(case, "FIRST_SEARCH")
    records = "".join(_search_record(candidate) for candidate in ("P001", "P002", "P003"))
    if screened:
        proposal_search = json.loads(_search_record("P001").strip())
        proposal_search.update(
            {
                "record_id": "S901",
                "proposal_id": "SP001",
                "search_scope": "engineering_proposal",
            }
        )
        records += json.dumps(proposal_search, ensure_ascii=False) + "\n"
    _write(case / "03-prior-art-search" / "search-records.jsonl", records)
    advance_stage(case, "CANDIDATE_RANKING")
    rankings = [_ranking_item("P001", "selected"), _ranking_item("P002"), _ranking_item("P003")]
    rankings[0].update(
        {
            "requires_patent_engineering": True,
            "implementation_completeness": "missing",
            "implementation_gap": "缺少阈值式资源选择规则",
        }
    )
    _write(
        case / "02-candidate-ranking.json",
        json.dumps(
            {
                "ranked_candidates": rankings,
                "selected_candidate_id": "P001",
                "strategic_ambiguity": False,
                "human_confirmation_required": False,
                "human_confirmation": "",
                "selection_reason": "补全设计后具有更清楚的技术机制",
            },
            ensure_ascii=False,
        ),
    )
    advance_stage(case, "FEATURE_MATRIX")
    _complete_matrix(case)
    _write(
        case / "patent-engineering" / "proposals.json",
        json.dumps(
            {
                "case_revision": 0,
                "proposals": [_engineering_proposal(screened=screened, overlap=overlap)],
            },
            ensure_ascii=False,
        ),
    )
    return case, project


def _complete_final_audit(case: Path) -> None:
    review = {
        "status": "PASS",
        "conclusion": "现有材料支持该项审计结论",
        "evidence_refs": ["I1-L1", "CN123"],
        "residual_risk": "仍需代理师终审",
        "recommended_action": "提交代理师复核",
    }
    audit = {
        "audited_application": {
            "revision": json.loads((case / "case-status.json").read_text())["revision"],
            "claims_final_sha256": hashlib.sha256(
                (case / "12-application" / "claims-final.md").read_bytes()
            ).hexdigest(),
            "specification_final_sha256": hashlib.sha256(
                (case / "12-application" / "specification-final.md").read_bytes()
            ).hexdigest(),
            "abstract_sha256": hashlib.sha256(
                (case / "12-application" / "abstract.md").read_bytes()
            ).hexdigest(),
            "drawings_manifest_sha256": hashlib.sha256(
                (case / "12-application" / "figures.json").read_bytes()
            ).hexdigest(),
        },
        "novelty": {
            "I1": {
                **review,
                "closest_reference_ids": ["CN123"],
                "single_reference_full_disclosure": False,
            }
        },
        "inventive_step": {
            **review,
            "closest_prior_art": ["CN123"],
            "distinguishing_limitation_ids": ["I1-L1"],
            "technical_effects": ["降低任务排队等待时延"],
            "objective_technical_problem": "如何降低任务处理过程中的等待时延",
            "combination_motivation": "现有文献未给出组合该反馈机制的技术启示",
        },
        "eligibility": dict(review),
        "clarity_and_support": dict(review),
        "enablement": dict(review),
        "unity": dict(review),
        "amendment_basis": dict(review),
        "sensitive_information": dict(review),
        "unimplemented_disclosures": [],
        "provenance_summary": {
            "frozen_implementation_limitations": ["I1-L1"],
            "td_only_limitations": [],
            "patent_engineering_limitations": [],
        },
        "inventorship_review": {
            "review_required": True,
            "skill_determination": "NOT_DETERMINED",
            "source_ids": [],
            "note": "需由专利专业人员结合实际人员贡献单独审查发明人资格",
        },
    }
    _write(case / "13-final-audit.json", json.dumps(audit, ensure_ascii=False))


def _independent_audit_case(tmp_path: Path) -> tuple[Path, Path]:
    case = tmp_path / "case"
    application = case / "12-application"
    audit_dir = case / "filing-package" / "huang-audit"
    application.mkdir(parents=True)
    audit_dir.mkdir(parents=True)
    for name in ("claims-final.md", "specification-final.md", "abstract.md"):
        _write(application / name, f"# {name}\n\n有效内容\n")
    _write(
        application / "figures.json",
        '{"figures_required":false,"figures":[],"abstract_figure_id":null}',
    )
    _write(case / "13-final-audit.json", '{"audit":"bound"}')
    _write(
        case / "case-status.json",
        json.dumps(
            {
                "revision": 1,
                "revision_history": [{"revision_id": "R001"}],
            }
        ),
    )
    _write(
        case / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1"],
                        "distinguishing_limitation_ids": ["I1-L1"],
                    }
                ],
                "dependent_claims": [],
            }
        ),
    )
    audit = {
        "audit_id": "A001",
        "auditor": {"tool": "HuangXinzhe/cn-patent-drafting", "version": "unknown"},
        "source_application": _application_hash_snapshot(case),
        "source_final_audit_sha256": hashlib.sha256(
            (case / "13-final-audit.json").read_bytes()
        ).hexdigest(),
        "findings": [],
        "overall_status": "RESOLVED",
    }
    audit_path = audit_dir / "independent-audit.json"
    _write(audit_path, json.dumps(audit, ensure_ascii=False))
    return case, audit_path


def test_init_case_creates_only_snapshot_and_uses_clean_git_commit(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "core.py", "def mechanism():\n    return 1\n")
    subprocess.run(["git", "init", str(project)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(project), "add", "core.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(project),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "evidence",
        ],
        check=True,
        capture_output=True,
    )

    case = tmp_path / "patent-case"
    result = init_case_workspace(case, project, "一种测试方法")

    assert result["snapshot"]["snapshot_type"] == "git_commit"
    assert len(result["snapshot"]["snapshot_sha256"]) == 64
    assert result["snapshot"]["git"]["worktree_clean"] is True
    assert not (case / "01-code-evidence-map.md").exists()
    assert validate_case_workspace(case) == []


def test_directory_and_uploaded_archive_snapshots_have_file_hashes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "core.py", "value = 1\n")
    directory_result = init_case_workspace(tmp_path / "directory-case", project)
    assert directory_result["snapshot"]["snapshot_type"] == "directory_manifest"
    assert len(directory_result["snapshot"]["files"][0]["sha256"]) == 64

    archive = tmp_path / "project.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("src/core.py", "value = 1\n")
    archive_result = init_case_workspace(tmp_path / "archive-case", archive)
    assert archive_result["snapshot"]["snapshot_type"] == "uploaded_archive"
    assert (
        archive_result["snapshot"]["archive_sha256"]
        == archive_result["snapshot"]["snapshot_sha256"]
    )
    assert archive_result["snapshot"]["files"][0]["path"] == "src/core.py"


def test_stage_transition_is_sequential_and_candidate_confirmation_is_conditional(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "core.py", "def mechanism():\n    return 1\n")
    case = tmp_path / "case"
    init_case_workspace(case, project)

    with pytest.raises(ValueError, match="Illegal stage transition"):
        advance_stage(case, "CLAIMS_V1")
    advance_stage(case, "EVIDENCE_MAP")
    _complete_evidence(case)
    advance_stage(case, "INVENTION_CANDIDATES")
    _complete_candidates(case)
    advance_stage(case, "FIRST_SEARCH")
    _write(
        case / "03-prior-art-search" / "search-records.jsonl",
        "".join(_search_record(candidate) for candidate in ("P001", "P002", "P003")),
    )
    advance_stage(case, "CANDIDATE_RANKING")
    ranking_path = case / "02-candidate-ranking.json"
    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
    ranking.update(
        {
            "ranked_candidates": [
                _ranking_item("P001", "selected"),
                _ranking_item("P002"),
                _ranking_item("P003"),
            ],
            "selected_candidate_id": "P001",
            "strategic_ambiguity": True,
            "human_confirmation_required": True,
            "selection_reason": "分值接近",
        }
    )
    ranking_path.write_text(json.dumps(ranking, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="human_confirmation"):
        advance_stage(case, "FEATURE_MATRIX")
    advance_stage(case, "FEATURE_MATRIX", confirmation="用户确认选择 P001")
    assert json.loads(ranking_path.read_text(encoding="utf-8"))["human_confirmation"]


def test_golden_case_revision_export_and_docx_gates(tmp_path: Path) -> None:
    project = Path(__file__).parent / "fixtures" / "golden-software-project"
    case = tmp_path / "case"
    init_case_workspace(case, project)
    advance_stage(case, "EVIDENCE_MAP")
    _complete_evidence(case)
    advance_stage(case, "INVENTION_CANDIDATES")
    _complete_candidates(case)
    advance_stage(case, "FIRST_SEARCH")
    _write(
        case / "03-prior-art-search" / "search-records.jsonl",
        "".join(_search_record(candidate) for candidate in ("P001", "P002", "P003")),
    )
    advance_stage(case, "CANDIDATE_RANKING")
    _write(
        case / "02-candidate-ranking.json",
        json.dumps(
            {
                "ranked_candidates": [
                    _ranking_item("P001", "selected"),
                    _ranking_item("P002"),
                    _ranking_item("P003"),
                ],
                "selected_candidate_id": "P001",
                "strategic_ambiguity": False,
                "human_confirmation_required": False,
                "human_confirmation": "",
                "selection_reason": "明显最优",
            }
        ),
    )
    advance_stage(case, "FEATURE_MATRIX")
    _complete_matrix(case)
    advance_stage(case, "CLAIMS_V1")
    _write(case / "05-claims-v1.md", "# Claims V1\n\n1. 一种处理方法，包括步骤A。\n")
    advance_stage(case, "SPECIFICATION_V1")
    _write(case / "06-specification-v1.md", "# 说明书 V1\n\n实施例执行步骤A并得到技术效果。\n")
    advance_stage(case, "SUPPORT_CANDIDATES")
    assert (case / "07-support-candidates.md").exists()
    assert not (case / "09-claim-support-map.md").exists()
    _write(case / "07-support-candidates.md", "| a | b |\n|---|---|\n| 步骤A | E1 |\n")
    advance_stage(case, "CLAIMS_V2")
    _write(
        case / "08-claims-v2.md",
        "# Claims V2\n\n1. 一种处理方法，其特征在于，包括：\n[I1-L1] 执行步骤A。\n",
    )
    _write(
        case / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1"],
                        "distinguishing_limitation_ids": ["I1-L1"],
                    }
                ],
                "dependent_claims": [],
            }
        ),
    )
    advance_stage(case, "CLAIM_SUPPORT_MAP")
    _write(
        case / "09-claim-support-map.json",
        json.dumps(
            {
                "limitations": [
                    {
                        "limitation_id": "I1-L1",
                        "claim_id": "I1",
                        "engineering_evidence_ids": ["E001"],
                        "technical_disclosure_ids": [],
                        "specification_sections": ["段落1"],
                        "technical_effect": "降低任务处理时延",
                        "effect_basis": "mechanism-derived",
                        "status": "supported",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )
    advance_stage(case, "FINAL_SEARCH")
    _write(case / "10-final-search" / "search-records.jsonl", "D4 requires revision")
    revised = revise_case_stage(case, "CLAIMS_V2", "D4 overlaps the original I1-L1 wording")
    assert revised["revision"] == 1
    assert (
        case / "revisions" / "R001" / "artifacts" / "10-final-search" / "search-records.jsonl"
    ).exists()
    _write(
        case / "08-claims-v2.md",
        "# Claims V2\n\n1. 一种处理方法，其特征在于，包括：\n[I1-L1] 基于运行状态反馈执行步骤A。\n",
    )
    _write(
        case / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1"],
                        "distinguishing_limitation_ids": ["I1-L1"],
                    }
                ],
                "dependent_claims": [],
            }
        ),
    )
    advance_stage(case, "CLAIM_SUPPORT_MAP")
    _write(
        case / "09-claim-support-map.json",
        json.dumps(
            {
                "limitations": [
                    {
                        "limitation_id": "I1-L1",
                        "claim_id": "I1",
                        "engineering_evidence_ids": ["E001"],
                        "technical_disclosure_ids": [],
                        "specification_sections": ["段落1"],
                        "technical_effect": "降低任务处理时延",
                        "effect_basis": "mechanism-derived",
                        "status": "supported",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )
    advance_stage(case, "FINAL_SEARCH")
    _write(case / "10-final-search" / "search-records.jsonl", _search_record())
    with pytest.raises(ValueError, match="Final search"):
        advance_stage(case, "APPLICATION_DRAFT")
    _write(case / "10-final-search" / "search-records.jsonl", _final_search_record())
    session_path = case / "10-final-search" / "search-session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    session["completed_at"] = "2026-08-25T00:00:00+00:00"
    _write(session_path, json.dumps(session))
    advance_stage(case, "APPLICATION_DRAFT")
    assert "[I1-L1]" not in (case / "12-application" / "claims-final.md").read_text()
    with pytest.raises(ValueError, match="pending application-draft"):
        advance_stage(case, "FINAL_AUDIT")
    _complete_application(case)
    advance_stage(case, "FINAL_AUDIT")
    _complete_final_audit(case)

    questions_path = case / "context-questions.json"
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    questions["questions"].append(
        {
            "id": "Q003",
            "category": "technical",
            "question": "状态反馈是否发生在任务分配之前？",
            "blocking": True,
            "impact": "影响独立权利要求的步骤顺序",
            "status": "open",
            "resolution": None,
            "evidence_refs": ["E001"],
            "source": None,
        }
    )
    _write(questions_path, json.dumps(questions, ensure_ascii=False))

    with pytest.raises(ValueError, match="Unresolved blocking technical questions"):
        advance_stage(case, "CONTENT_READY_FOR_ATTORNEY_REVIEW")
    resolve_case_question(case, "Q003", "是，反馈先于分配执行", "developer-confirmed")
    advance_stage(case, "CONTENT_READY_FOR_ATTORNEY_REVIEW")
    status = json.loads((case / "case-status.json").read_text(encoding="utf-8"))
    assert "technical_questions_open" not in status
    assert not (case / "filing-package").exists()

    exported = export_case_package(case, tmp_path / "patent-output")
    assert (exported / "claims-final.md").exists()
    assert (exported / "export-manifest.json").exists()

    advance_stage(case, "INDEPENDENT_AUDIT")
    audit_path = case / "filing-package" / "huang-audit" / "independent-audit.json"
    independent = json.loads(audit_path.read_text(encoding="utf-8"))
    independent.update({"audit_id": "A001", "overall_status": "RESOLVED"})
    _write(audit_path, json.dumps(independent, ensure_ascii=False))
    with pytest.raises(ValueError, match="DOCX render gate"):
        advance_stage(case, "DOCX_PACKAGE_RENDERED")
    for subject in BASE_REQUIRED_DOCX_SUBJECTS:
        _write_valid_docx(case / "filing-package" / "docx" / f"{subject}.docx", subject)
    advance_stage(case, "DOCX_PACKAGE_RENDERED")
    assert validate_case_workspace(case) == []


def test_manual_stage_jump_and_filing_ready_are_rejected(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    case = tmp_path / "case"
    init_case_workspace(case, project)
    status_path = case / "case-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["current_stage"] = "CLAIMS_V2"
    status_path.write_text(json.dumps(status), encoding="utf-8")
    assert any("stage_history" in error for error in validate_case_workspace(case))

    status["current_stage"] = "FILING_READY"
    status_path.write_text(json.dumps(status), encoding="utf-8")
    assert "FILING_READY cannot be set by this tool" in validate_case_workspace(case)


def test_claims_v1_gate_runs_chinese_claim_validator(tmp_path: Path) -> None:
    path = tmp_path / "claims.md"
    _write(
        path,
        "# Claims V1\n\n"
        "1. 一种方法，其特征在于，包括A。\n"
        "3. 根据权利要求4所述的方法，其特征在于，包括B。\n",
    )
    errors = _validate_claims_stage(path)
    assert any("consecutive" in error for error in errors)
    assert any("earlier" in error for error in errors)


def test_claim_structure_rejects_unlabelled_limitation_and_mismatch(tmp_path: Path) -> None:
    claims = tmp_path / "claims-v2.md"
    structure = tmp_path / "claims-v2-structure.json"
    _write(
        claims,
        "1. 一种方法，其特征在于，包括：\n"
        "[I1-L1] 获取数据；\n"
        "对所述数据进行状态预测；\n"
        "[I1-L3] 根据状态预测结果调整资源。\n",
    )
    _write(
        structure,
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1", "I1-L2", "I1-L3"],
                        "distinguishing_limitation_ids": ["I1-L2", "I1-L3"],
                    }
                ]
            }
        ),
    )
    errors = _validate_claims_stage(claims, structure)
    assert any("unlabelled substantive limitation" in error for error in errors)
    assert any("unique and consecutive" in error for error in errors)
    assert any("exactly match" in error for error in errors)


def test_claim_structure_traces_dependent_added_limitations(tmp_path: Path) -> None:
    claims = tmp_path / "claims-v2.md"
    structure = tmp_path / "claims-v2-structure.json"
    _write(
        claims,
        "1. 一种方法，其特征在于，包括：\n"
        "[I1-L1] 获取任务状态。\n"
        "2. 根据权利要求1所述的方法，其特征在于：\n"
        "[D2-L1] 根据所述任务状态调整缓存策略。\n",
    )
    _write(
        structure,
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1"],
                        "distinguishing_limitation_ids": ["I1-L1"],
                    }
                ],
                "dependent_claims": [
                    {
                        "claim_id": "D2",
                        "claim_number": 2,
                        "depends_on": [1],
                        "added_limitation_ids": ["D2-L1"],
                        "fallback_priority": "high",
                    }
                ],
            }
        ),
    )
    assert _validate_claims_stage(claims, structure) == []


def test_docx_gate_rejects_fake_and_empty_ooxml(tmp_path: Path) -> None:
    fake = tmp_path / "fake.docx"
    fake.write_bytes(b"docx")
    assert any("not a valid OOXML ZIP" in error for error in _validate_docx_file(fake))

    empty = tmp_path / "empty.docx"
    _write_valid_docx(empty, "")
    assert any("body is empty" in error for error in _validate_docx_file(empty))

    valid = tmp_path / "valid.docx"
    _write_valid_docx(valid)
    assert _validate_docx_file(valid) == []


def test_support_map_requires_exactly_one_row_per_structured_limitation(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1", "I1-L2"],
                        "distinguishing_limitation_ids": ["I1-L2"],
                    }
                ]
            }
        ),
    )
    _write(
        tmp_path / "01-code-evidence-map.json",
        json.dumps({"evidence": [{"evidence_id": "E001"}]}),
    )
    _write(
        tmp_path / "09-claim-support-map.json",
        json.dumps(
            {
                "limitations": [
                    {
                        "limitation_id": "I1-L1",
                        "claim_id": "I1",
                        "engineering_evidence_ids": ["E001"],
                        "technical_disclosure_ids": [],
                        "specification_sections": ["段落1"],
                        "technical_effect": "降低处理时延",
                        "effect_basis": "mechanism-derived",
                        "status": "supported",
                    },
                    {
                        "limitation_id": "I1-L1",
                        "claim_id": "I1",
                        "engineering_evidence_ids": ["E001"],
                        "technical_disclosure_ids": [],
                        "specification_sections": ["段落1"],
                        "technical_effect": "降低处理时延",
                        "effect_basis": "mechanism-derived",
                        "status": "supported",
                    },
                ]
            },
            ensure_ascii=False,
        ),
    )
    errors = _validate_support_map(tmp_path, {})
    assert any("must be unique" in error for error in errors)
    assert any("cover exactly" in error for error in errors)


def test_final_search_requires_claim_combinations_and_distinguishing_coverage(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1", "I1-L2"],
                        "distinguishing_limitation_ids": ["I1-L2"],
                    }
                ],
                "dependent_claims": [],
            }
        ),
    )
    search_dir = tmp_path / "10-final-search"
    search_dir.mkdir()
    _write(tmp_path / "08-claims-v2.md", "1. 一种方法，包括测试步骤。\n")
    _write(
        search_dir / "search-records.jsonl",
        _final_search_record("I1", ("I1-L1",), "distinguishing_limitation"),
    )
    _write(tmp_path / "case-status.json", json.dumps({"revision": 0}))
    _write(
        search_dir / "search-session.json",
        json.dumps(
            {
                "revision": 0,
                "source": {
                    "claims_v2_sha256": hashlib.sha256(
                        (tmp_path / "08-claims-v2.md").read_bytes()
                    ).hexdigest(),
                    "claims_v2_structure_sha256": hashlib.sha256(
                        (tmp_path / "08-claims-v2-structure.json").read_bytes()
                    ).hexdigest(),
                },
                "started_at": "2026-08-25T00:00:00+00:00",
                "completed_at": "2026-08-25T00:01:00+00:00",
            }
        ),
    )
    errors = _validate_final_search(tmp_path, {})
    assert any("full combination query" in error for error in errors)
    assert any("distinguishing limitations: I1-L2" in error for error in errors)
    _write(tmp_path / "08-claims-v2.md", "1. 一种方法，包括被偷偷修改的步骤。\n")
    assert any(
        "stale against current Claims V2" in error for error in _validate_final_search(tmp_path, {})
    )


def test_revision_archives_downstream_and_reopens_target(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    case = tmp_path / "case"
    init_case_workspace(case, project)
    status_path = case / "case-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    stages = [stage.value for stage in CASE_STAGE_ORDER]
    current_index = stages.index("FINAL_SEARCH")
    status["current_stage"] = "FINAL_SEARCH"
    status["stage_history"] = [
        {
            "stage": stage,
            "entered_at": "2026-08-24T00:00:00+00:00",
            "event": "initialize" if index == 0 else "advance",
            "revision": 0,
        }
        for index, stage in enumerate(stages[: current_index + 1])
    ]
    status_path.write_text(json.dumps(status), encoding="utf-8")
    _write(case / "08-claims-v2.md", "old claims")
    _write(case / "08-claims-v2-structure.json", "{}")
    (case / "10-final-search").mkdir()
    _write(case / "10-final-search" / "search-records.jsonl", "old search")

    revised = revise_case_stage(case, "CLAIMS_V2", "D4 overlaps I1-L2")

    assert revised["current_stage"] == "CLAIMS_V2"
    assert revised["revision"] == 1
    revision = case / "revisions" / "R001"
    assert (revision / "artifacts" / "08-claims-v2.md").read_text() == "old claims"
    assert (revision / "artifacts" / "10-final-search" / "search-records.jsonl").exists()
    assert (revision / "reason.json").exists()
    assert (case / "08-claims-v2.md").exists()
    assert not (case / "10-final-search").exists()


def test_markdown_cannot_bypass_structured_evidence_gate(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "core.py", "value = 1\n")
    case = tmp_path / "case"
    init_case_workspace(case, project)
    advance_stage(case, "EVIDENCE_MAP")
    _write(case / "01-code-evidence-map.md", "| E001 | 看似完整但不是事实源 |\n")

    with pytest.raises(ValueError, match="should be non-empty"):
        advance_stage(case, "INVENTION_CANDIDATES")


def test_final_audit_placeholder_cannot_pass_without_structured_analysis(tmp_path: Path) -> None:
    _write(
        tmp_path / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1"],
                        "distinguishing_limitation_ids": ["I1-L1"],
                    }
                ]
            }
        ),
    )
    search = tmp_path / "10-final-search"
    search.mkdir()
    _write(search / "search-records.jsonl", _final_search_record())
    _write(tmp_path / "13-final-audit.md", "# 最终审计\n\n## 新颖性\n\n已完成检查。\n")
    _write(tmp_path / "13-final-audit.json", json.dumps({"novelty": {}}))

    errors = _validate_final_audit(tmp_path, {})
    assert any("required property" in error for error in errors)


def test_independent_audit_rejects_open_revision_required_finding(tmp_path: Path) -> None:
    case, path = _independent_audit_case(tmp_path)
    audit = json.loads(path.read_text(encoding="utf-8"))
    audit["findings"] = [
        {
            "finding_id": "H001",
            "category": "claim_scope",
            "severity": "substantive",
            "affected_claims": [1],
            "affected_limitation_ids": ["I1-L1"],
            "finding": "独立权利要求范围过宽",
            "recommendation": "通过正式修订缩小范围",
            "disposition": "revision_required",
            "resolution": None,
            "revision_id": None,
        }
    ]
    audit["overall_status"] = "PENDING"
    _write(path, json.dumps(audit, ensure_ascii=False))
    errors = _validate_independent_audit(case, {})
    assert any("requires a canonical revision" in error for error in errors)


def test_independent_audit_rejects_unknown_revision_id(tmp_path: Path) -> None:
    case, path = _independent_audit_case(tmp_path)
    audit = json.loads(path.read_text(encoding="utf-8"))
    audit["findings"] = [
        {
            "finding_id": "H001",
            "category": "claim_scope",
            "severity": "blocking",
            "affected_claims": [1],
            "affected_limitation_ids": ["I1-L1"],
            "finding": "独立权利要求存在阻断缺陷",
            "recommendation": "通过正式修订解决缺陷",
            "disposition": "resolved_by_revision",
            "resolution": "声称已经完成修订",
            "revision_id": "R999",
        }
    ]
    _write(path, json.dumps(audit, ensure_ascii=False))
    assert any(
        "unknown canonical revision" in error for error in _validate_independent_audit(case, {})
    )


def test_independent_audit_requires_reason_when_rejecting_finding(tmp_path: Path) -> None:
    case, path = _independent_audit_case(tmp_path)
    audit = json.loads(path.read_text(encoding="utf-8"))
    audit["findings"] = [
        {
            "finding_id": "H001",
            "category": "clarity",
            "severity": "substantive",
            "affected_claims": [1],
            "affected_limitation_ids": ["I1-L1"],
            "finding": "术语可能不够清楚",
            "recommendation": "进一步限定该术语",
            "disposition": "rejected_with_reason",
            "resolution": "",
            "revision_id": None,
        }
    ]
    _write(path, json.dumps(audit, ensure_ascii=False))
    assert any("written resolution" in error for error in _validate_independent_audit(case, {}))


def test_independent_audit_accepts_known_resolved_revision(tmp_path: Path) -> None:
    case, path = _independent_audit_case(tmp_path)
    audit = json.loads(path.read_text(encoding="utf-8"))
    audit["findings"] = [
        {
            "finding_id": "H001",
            "category": "claim_scope",
            "severity": "blocking",
            "affected_claims": [1],
            "affected_limitation_ids": ["I1-L1"],
            "finding": "独立权利要求存在阻断缺陷",
            "recommendation": "通过正式修订解决缺陷",
            "disposition": "resolved_by_revision",
            "resolution": "已在 R001 中完成规范修改",
            "revision_id": "R001",
        }
    ]
    _write(path, json.dumps(audit, ensure_ascii=False))
    assert _validate_independent_audit(case, {}) == []


def test_final_and_independent_audits_reject_stale_application_hashes(tmp_path: Path) -> None:
    case, independent_path = _independent_audit_case(tmp_path)
    old_snapshot = _application_hash_snapshot(case)
    _write(
        case / "13-final-audit.json",
        json.dumps({"audited_application": old_snapshot, "novelty": {}}, ensure_ascii=False),
    )
    independent = json.loads(independent_path.read_text(encoding="utf-8"))
    independent["source_final_audit_sha256"] = hashlib.sha256(
        (case / "13-final-audit.json").read_bytes()
    ).hexdigest()
    _write(independent_path, json.dumps(independent, ensure_ascii=False))
    _write(case / "12-application" / "specification-final.md", "偷偷修改最终说明书")

    assert any(
        "stale against the current application" in error
        for error in _validate_final_audit(case, {})
    )
    assert any(
        "stale against the current application" in error
        for error in _validate_independent_audit(case, {})
    )


def test_docx_subjects_make_specification_and_abstract_figures_conditional(
    tmp_path: Path,
) -> None:
    application = tmp_path / "12-application"
    application.mkdir()
    metadata = {
        "drawings": {
            "required": False,
            "reason": "文字足以清楚完整说明技术方案",
            "abstract_figure_required": False,
            "abstract_figure_id": None,
        }
    }
    _write(application / "application-metadata.json", json.dumps(metadata, ensure_ascii=False))
    subjects = required_docx_subjects(tmp_path)
    assert "说明书附图" not in subjects
    assert "摘要附图" not in subjects

    metadata["drawings"] = {
        "required": True,
        "reason": "流程关系需要附图辅助说明",
        "abstract_figure_required": True,
        "abstract_figure_id": "FIG-01",
    }
    _write(application / "application-metadata.json", json.dumps(metadata, ensure_ascii=False))
    subjects = required_docx_subjects(tmp_path)
    assert "说明书附图" in subjects
    assert "摘要附图" in subjects


def test_figure_manifest_rejects_unproven_semantics_and_missing_file(tmp_path: Path) -> None:
    application = tmp_path / "12-application"
    application.mkdir()
    _write(
        tmp_path / "01-code-evidence-map.json",
        json.dumps({"evidence": [{"evidence_id": "E001"}]}),
    )
    manifest = {
        "figures_required": True,
        "figures": [
            {
                "figure_id": "FIG-01",
                "figure_number": 1,
                "type": "flowchart",
                "purpose": "展示状态反馈流程",
                "engineering_evidence_ids": ["E999"],
                "technical_disclosure_ids": [],
                "claim_limitation_ids": ["I1-L1"],
                "nodes": [{"id": "N1", "label": "获取状态"}],
                "edges": [],
                "file": "figures/FIG-01.svg",
                "sha256": "0" * 64,
            }
        ],
        "abstract_figure_id": "FIG-01",
    }
    manifest_path = application / "figures.json"
    _write(manifest_path, json.dumps(manifest, ensure_ascii=False))
    structure = {
        "independent_claims": [{"limitation_ids": ["I1-L1"]}],
        "dependent_claims": [],
    }
    decision = {
        "required": True,
        "abstract_figure_required": True,
        "abstract_figure_id": "FIG-01",
    }
    errors = _validate_figures(
        tmp_path, manifest_path, decision, "# 附图说明\n\n图1为流程图。", structure
    )
    assert any("unknown engineering evidence" in error for error in errors)
    assert any("Figure file is missing" in error for error in errors)


def test_patent_engineering_requires_screening_and_limits_high_overlap_purpose(
    tmp_path: Path,
) -> None:
    case, _ = _prepare_engineering_case(tmp_path, screened=False)
    with pytest.raises(ValueError, match="screened before user decision"):
        resolve_engineering_proposal(
            case,
            "SP001",
            "adopt",
            "同意采用",
            "user-response",
            technical_disclosure=_engineering_disclosure(),
        )

    other = tmp_path / "overlap"
    other.mkdir()
    case, project = _prepare_engineering_case(other, overlap="high")
    proposal = resolve_engineering_proposal(
        case,
        "SP001",
        "adopt",
        "因真实工程价值采用，但不作为专利区别特征",
        "user-response",
        technical_disclosure=_engineering_disclosure(),
    )
    assert proposal["screening"]["patent_distinction_eligible"] is False
    with pytest.raises(ValueError, match="real engineering value"):
        authorize_engineering_implementation(
            case,
            "SP001",
            "explicit-user-authorization",
            purpose="patent_distinction",
        )
    proposal = authorize_engineering_implementation(
        case,
        "SP001",
        "explicit-user-authorization",
        purpose="real_engineering_value",
    )
    assert proposal["implementation"]["authorized"] is True
    core = project / "core.py"
    core.write_text(
        "def allocate(state, load):\n    return 'stable' if load > 0.8 else state\n",
        encoding="utf-8",
    )
    iteration = record_engineering_iteration(
        case,
        project,
        "SP001",
        authorization_source="explicit-user-authorization",
        reason="即使不考虑专利也能改善资源稳定性",
        changed_files=["core.py"],
        test_results=[
            {"name": "unit", "command": "pytest", "passed": True, "output_summary": "通过"}
        ],
        new_evidence=[
            {
                "evidence_id": "E002",
                "source": {
                    "path": "core.py",
                    "sha256": hashlib.sha256(core.read_bytes()).hexdigest(),
                },
                "processing_step": "按负载状态选择稳定资源路径",
                "state_change": "待分配状态变为稳定资源路径状态",
                "technical_effect": "改善资源分配稳定性",
                "effect_basis": "mechanism-derived",
                "status": "code-supported",
            }
        ],
        origin_provenance={
            "origin_type": "agent_implemented",
            "human_contributions": [],
            "source": "explicit real-engineering-value authorization",
            "inventorship_review_required": True,
        },
    )
    assert iteration["iteration"]["status"] == "validated"
    evidence = json.loads((case / "01-code-evidence-map.json").read_text())
    assert evidence["evidence"][0]["novelty_distinction_eligible"] is False
    _write(
        case / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1"],
                        "distinguishing_limitation_ids": ["I1-L1"],
                    }
                ],
                "dependent_claims": [],
            }
        ),
    )
    _write(
        case / "09-claim-support-map.json",
        json.dumps(
            {
                "limitations": [
                    {
                        "limitation_id": "I1-L1",
                        "claim_id": "I1",
                        "engineering_evidence_ids": ["E002"],
                        "technical_disclosure_ids": ["TD001"],
                        "specification_sections": ["实施例1"],
                        "technical_effect": "改善资源分配稳定性",
                        "effect_basis": "mechanism-derived",
                        "status": "supported",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )
    assert any(
        "novelty/inventive-step distinction" in error for error in _validate_support_map(case, {})
    )


def test_sp_proposed_default_is_valid_but_sp_cannot_be_claim_support() -> None:
    proposals = {"case_revision": 0, "proposals": [_engineering_proposal()]}
    assert validate_schema(proposals, "patent-engineering-proposals.schema.json") == []
    invalid_support = {
        "limitations": [
            {
                "limitation_id": "I1-L1",
                "claim_id": "I1",
                "engineering_evidence_ids": ["SP001"],
                "technical_disclosure_ids": [],
                "specification_sections": ["实施例1"],
                "technical_effect": "降低处理等待时延",
                "effect_basis": "mechanism-derived",
                "status": "supported",
            }
        ]
    }
    assert validate_schema(invalid_support, "claim-support-map.schema.json")


def test_high_overlap_allows_one_searched_substantive_redesign(tmp_path: Path) -> None:
    case, _ = _prepare_engineering_case(tmp_path, overlap="high")
    proposals_path = case / "patent-engineering" / "proposals.json"
    proposals = json.loads(proposals_path.read_text())
    redesign = json.loads(json.dumps(proposals["proposals"][0]))
    redesign.update(
        {
            "proposal_id": "SP002",
            "status": "screened",
            "summary": "改用状态窗口趋势与资源稳定度联合选择资源路径",
            "processing_steps": ["构造状态窗口", "计算趋势", "联合稳定度选择资源路径"],
            "decision_rules": ["趋势恶化且稳定度下降时切换资源路径"],
            "screening": {
                "status": "completed",
                "search_record_ids": ["S902"],
                "overlap_risk": "low",
                "conclusion": "实质性因果机制未见完整公开",
                "patent_distinction_eligible": True,
            },
            "redesign_of": "SP001",
            "redesign_basis": "由单阈值判断改为时间窗口趋势和资源稳定度的联合状态机制",
            "redesign_change_type": "substantive_mechanism",
        }
    )
    proposals["proposals"].append(redesign)
    _write(proposals_path, json.dumps(proposals, ensure_ascii=False))
    search_path = case / "03-prior-art-search" / "search-records.jsonl"
    search = json.loads(_search_record("P001").strip())
    search.update(
        {
            "record_id": "S902",
            "proposal_id": "SP002",
            "search_scope": "engineering_proposal",
        }
    )
    search_path.write_text(
        search_path.read_text() + json.dumps(search, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    assert not any("redesign" in error.lower() for error in _validate_patent_engineering(case))

    second = json.loads(json.dumps(redesign))
    second["proposal_id"] = "SP003"
    second["screening"]["search_record_ids"] = ["S903"]
    proposals["proposals"].append(second)
    _write(proposals_path, json.dumps(proposals, ensure_ascii=False))
    search["record_id"] = "S903"
    search["proposal_id"] = "SP003"
    search_path.write_text(
        search_path.read_text() + json.dumps(search, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    assert any(
        "only one substantive redesign" in error for error in _validate_patent_engineering(case)
    )


def test_modified_patent_engineering_promotes_td_and_preserves_user_parameter(
    tmp_path: Path,
) -> None:
    case, _ = _prepare_engineering_case(tmp_path)
    proposal = resolve_engineering_proposal(
        case,
        "SP001",
        "modify",
        "采用，但阈值改为 0.65",
        "user-response",
        technical_disclosure=_engineering_disclosure(),
        modified_parameters={"load_threshold": 0.65},
    )
    assert proposal["status"] == "modified"
    assert proposal["technical_disclosure_ids"] == ["TD001"]
    assert proposal["parameters"][0]["value"] == 0.65
    assert proposal["parameters"][0]["provenance"] == "USER_CONFIRMED"
    disclosures = json.loads((case / "01-technical-disclosures.json").read_text())
    assert [item["disclosure_id"] for item in disclosures["disclosures"]] == ["TD001"]
    assert disclosures["disclosures"][0]["parameters"][0]["value"] == 0.65
    assert disclosures["disclosures"][0]["parameters"][0]["provenance"] == "USER_CONFIRMED"
    assert proposal["implementation"]["authorized"] is False
    assert proposal["commit_authorization"]["authorized"] is False

    authorized = authorize_engineering_implementation(
        case,
        "SP001",
        "separate-implementation-approval",
        purpose="patent_distinction",
    )
    assert authorized["implementation"]["authorized"] is True
    assert authorized["commit_authorization"]["authorized"] is False
    committed = authorize_engineering_commit(case, "SP001", "separate-commit-approval")
    assert committed["commit_authorization"]["authorized"] is True


def test_rejected_patent_engineering_does_not_create_td(tmp_path: Path) -> None:
    case, _ = _prepare_engineering_case(tmp_path)
    proposal = resolve_engineering_proposal(
        case,
        "SP001",
        "reject",
        "不采用该参考实现",
        "user-response",
    )
    assert proposal["status"] == "rejected"
    assert proposal["technical_disclosure_ids"] == []
    disclosures = json.loads((case / "01-technical-disclosures.json").read_text())
    assert disclosures["disclosures"] == []

    other = tmp_path / "uncertain"
    other.mkdir()
    case, _ = _prepare_engineering_case(other)
    proposal = resolve_engineering_proposal(
        case,
        "SP001",
        "uncertain",
        "暂时无法确认是否采用",
        "user-response",
    )
    assert proposal["status"] == "uncertain"
    disclosures = json.loads((case / "01-technical-disclosures.json").read_text())
    assert disclosures["disclosures"] == []


def test_patent_engineering_iteration_freezes_failed_validation_as_nonvalidated_evidence(
    tmp_path: Path,
) -> None:
    case, project = _prepare_engineering_case(tmp_path)
    resolve_engineering_proposal(
        case,
        "SP001",
        "adopt",
        "同意采用并实施",
        "user-response",
        technical_disclosure=_engineering_disclosure(),
    )
    authorize_engineering_implementation(
        case,
        "SP001",
        "separate-implementation-approval",
        purpose="patent_distinction",
    )

    core = project / "core.py"
    core.write_text(
        "def allocate(state, load):\n    return 'low-load' if load > 0.8 else state\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(core.read_bytes()).hexdigest()
    result = record_engineering_iteration(
        case,
        project,
        "SP001",
        authorization_source="separate-implementation-approval",
        reason="实现经确认的参考方案",
        changed_files=["core.py"],
        test_results=[
            {"name": "unit", "command": "pytest", "passed": False, "output_summary": "失败"}
        ],
        new_evidence=[
            {
                "evidence_id": "E002",
                "source": {"path": "core.py", "sha256": digest},
                "processing_step": "根据负载阈值选择资源路径",
                "state_change": "任务状态变为带资源路径的状态",
                "technical_effect": "减少不适配资源分配造成的等待",
                "effect_basis": "mechanism-derived",
                "status": "code-supported",
            }
        ],
        origin_provenance={
            "origin_type": "agent_implemented",
            "human_contributions": [],
            "source": "authorized Codex implementation",
            "inventorship_review_required": True,
        },
    )
    assert result["snapshot_id"] == "S002"
    assert (case / "00-project-snapshot" / "snapshots" / "S001" / "snapshot-manifest.json").exists()
    assert (case / "00-project-snapshot" / "snapshots" / "S002" / "snapshot-manifest.json").exists()
    assert result["status"]["current_stage"] == "EVIDENCE_MAP"
    assert (case / "revisions" / "R001" / "artifacts" / "02-invention-candidates.json").exists()
    evidence = json.loads((case / "01-code-evidence-map.json").read_text())
    assert [item["evidence_id"] for item in evidence["evidence"]] == ["E002"]
    assert evidence["evidence"][0]["validation_status"] == "failed"
    assert evidence["evidence"][0]["snapshot_id"] == "S002"
    assert evidence["evidence"][0]["engineering_iteration_id"] == "IT001"
    assert evidence["evidence"][0]["proposal_id"] == "SP001"
    assert result["iteration"]["status"] == "validation_failed"
    validated = validate_engineering_iteration(
        case,
        "IT001",
        [
            {
                "name": "rerun-unit",
                "command": "pytest",
                "passed": True,
                "output_summary": "修复验证环境后通过",
            }
        ],
    )
    assert validated["status"] == "validated"
    evidence = json.loads((case / "01-code-evidence-map.json").read_text())
    assert evidence["evidence"][0]["validation_status"] == "passed"
    evidence["evidence"][0]["proposal_id"] = "SP999"
    _write(
        case / "01-code-evidence-map.json",
        json.dumps(evidence, ensure_ascii=False),
    )
    assert any("inconsistent lineage" in error for error in _validate_evidence_map(case, {}))


def test_validated_patent_engineering_iteration_reaches_claims_v1(tmp_path: Path) -> None:
    case, project = _prepare_engineering_case(tmp_path)
    resolve_engineering_proposal(
        case,
        "SP001",
        "adopt",
        "同意采用该工程方案",
        "user-response",
        technical_disclosure=_engineering_disclosure(),
    )
    authorize_engineering_implementation(
        case,
        "SP001",
        "separate-implementation-approval",
        purpose="patent_distinction",
    )
    core = project / "core.py"
    core.write_text(
        "def allocate(state, load):\n    return 'low-load' if load > 0.8 else state\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(core.read_bytes()).hexdigest()
    result = record_engineering_iteration(
        case,
        project,
        "SP001",
        authorization_source="separate-implementation-approval",
        reason="实现经确认的参考方案",
        changed_files=["core.py"],
        test_results=[
            {"name": "unit", "command": "pytest", "passed": True, "output_summary": "通过"}
        ],
        new_evidence=[
            {
                "evidence_id": "E002",
                "source": {"path": "core.py", "sha256": digest},
                "processing_step": "根据负载阈值选择资源路径",
                "state_change": "任务状态变为带资源路径的状态",
                "technical_effect": "减少不适配资源分配造成的等待",
                "effect_basis": "mechanism-derived",
                "status": "code-supported",
            }
        ],
        origin_provenance={
            "origin_type": "agent_implemented",
            "human_contributions": [],
            "source": "authorized Codex implementation",
            "inventorship_review_required": True,
        },
    )
    assert result["iteration"]["status"] == "validated"
    evidence = json.loads((case / "01-code-evidence-map.json").read_text())

    # Re-understand and re-search the changed project before Claims V1.
    implemented_evidence = evidence
    _complete_evidence(case)
    _write(case / "01-code-evidence-map.json", json.dumps(implemented_evidence, ensure_ascii=False))
    for relative in (
        "project-understanding/technical-model.json",
        "project-understanding/search-feature-model.json",
    ):
        path = case / relative
        _write(path, path.read_text(encoding="utf-8").replace("E001", "E002"))
    advance_stage(case, "INVENTION_CANDIDATES")
    _complete_candidates(case)
    candidates_path = case / "02-invention-candidates.json"
    _write(
        candidates_path,
        candidates_path.read_text(encoding="utf-8").replace("E001", "E002"),
    )
    advance_stage(case, "FIRST_SEARCH")
    proposal_search = json.loads(_search_record("P001").strip())
    proposal_search.update(
        {
            "record_id": "S901",
            "proposal_id": "SP001",
            "search_scope": "engineering_proposal",
        }
    )
    _write(
        case / "03-prior-art-search" / "search-records.jsonl",
        "".join(_search_record(candidate) for candidate in ("P001", "P002", "P003"))
        + json.dumps(proposal_search, ensure_ascii=False)
        + "\n",
    )
    advance_stage(case, "CANDIDATE_RANKING")
    _write(
        case / "02-candidate-ranking.json",
        json.dumps(
            {
                "ranked_candidates": [
                    _ranking_item("P001", "selected"),
                    _ranking_item("P002"),
                    _ranking_item("P003"),
                ],
                "selected_candidate_id": "P001",
                "strategic_ambiguity": False,
                "human_confirmation_required": False,
                "human_confirmation": "",
                "selection_reason": "新实现经重新检索后仍为最优候选",
            },
            ensure_ascii=False,
        ),
    )
    advance_stage(case, "FEATURE_MATRIX")
    _complete_matrix(case)
    matrix_path = case / "04-feature-matrix.json"
    _write(matrix_path, matrix_path.read_text(encoding="utf-8").replace("E001", "E002"))
    advance_stage(case, "CLAIMS_V1")
    assert json.loads((case / "case-status.json").read_text())["current_stage"] == "CLAIMS_V1"


def test_methodology_v2_requires_understanding_and_landscape_before_candidates(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "core.py").write_text("def step(value):\n    return value\n", encoding="utf-8")
    case = tmp_path / "case"
    init_case_workspace(case, project)
    advance_stage(case, "EVIDENCE_MAP")
    snapshot = json.loads((case / "00-project-snapshot" / "snapshot-manifest.json").read_text())
    source = snapshot["files"][0]
    _write(
        case / "01-code-evidence-map.json",
        json.dumps(
            {
                "evidence": [
                    {
                        "evidence_id": "E001",
                        "source": {"path": source["path"], "sha256": source["sha256"]},
                        "processing_step": "执行输入状态传递",
                        "state_change": "输入状态成为输出状态",
                        "technical_effect": "保持状态传递一致性",
                        "effect_basis": "mechanism-derived",
                        "status": "code-supported",
                    }
                ]
            },
            ensure_ascii=False,
        ),
    )
    with pytest.raises(ValueError, match="project-technical-model"):
        advance_stage(case, "INVENTION_CANDIDATES")

    _complete_evidence(case)
    technical_model = json.loads(
        (case / "project-understanding" / "technical-model.json").read_text()
    )
    technical_model["core_modules"][0]["engineering_evidence_ids"] = ["E999"]
    _write(
        case / "project-understanding" / "technical-model.json",
        json.dumps(technical_model, ensure_ascii=False),
    )
    with pytest.raises(ValueError, match="unknown engineering evidence"):
        advance_stage(case, "INVENTION_CANDIDATES")
