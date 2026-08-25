import json
from pathlib import Path

from patent_skill.case_workspace import (
    _validate_content_ready,
    _validate_evidence_map,
    _validate_invention_candidates,
    _validate_support_map,
    advance_stage,
    init_case_workspace,
    resolve_case_question,
)
from patent_skill.schema_validation import validate_schema


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _case(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir(parents=True)
    (project / "core.py").write_text("def existing_step(value):\n    return value + 1\n")
    case = tmp_path / "patent-case"
    init_case_workspace(case, project)
    advance_stage(case, "EVIDENCE_MAP")
    snapshot = json.loads(
        (case / "00-project-snapshot" / "snapshot-manifest.json").read_text()
    )
    source = snapshot["files"][0]
    _write_json(
        case / "01-code-evidence-map.json",
        {
            "evidence": [
                {
                    "evidence_id": "E001",
                    "source": {"path": source["path"], "sha256": source["sha256"]},
                    "processing_step": "执行已有的数据转换步骤",
                    "state_change": "输入数据变为中间状态数据",
                    "technical_effect": "形成后续机制可以处理的结构化状态",
                    "effect_basis": "mechanism-derived",
                    "status": "code-supported",
                }
            ]
        },
    )
    return case


def _add_candidate_question(case: Path, *, blocking: bool = True) -> None:
    path = case / "context-questions.json"
    data = json.loads(path.read_text())
    data["questions"].append(
        {
            "id": "Q003",
            "category": "technical",
            "question": "是否采用所述状态映射机制？",
            "blocking": blocking,
            "impact": "影响主发明的必要处理链",
            "status": "open",
            "resolution": None,
            "evidence_refs": ["E001"],
            "source": None,
            "candidate_completion": {
                "statement": "将中间状态映射为结构化标签并连接到输出模块",
                "basis_refs": ["E001"],
                "status": "proposed",
            },
            "resulting_disclosure_ids": [],
        }
    )
    _write_json(path, data)


def _disclosure(
    *,
    disclosure_id: str = "TD001",
    enablement: str = "sufficient",
    implementation_status: str = "designed_not_implemented",
) -> dict:
    missing = [] if enablement == "sufficient" else ["标签冲突时的处理规则"]
    return {
        "disclosure_id": disclosure_id,
        "question_id": "Q003",
        "statement": "将已有中间状态映射为结构化标签并传递到输出模块",
        "source_role": "developer",
        "implementation_status": implementation_status,
        "mechanism": {
            "input": "已有中间状态数据",
            "processing": ["读取状态字段", "根据已确认规则生成结构化标签"],
            "state_change": "未标注状态转变为具有结构化标签的状态",
            "output": "结构化标签记录",
            "integration": "标签记录通过现有输出接口交给后续模块",
            "conflict_and_exception_handling": "冲突时保留冲突标记并进入人工确认队列",
        },
        "technical_effect": {
            "statement": "把一次状态处理转化为可供后续模块使用的结构化记录",
            "effect_basis": "mechanism-derived",
            "evidence_refs": [],
        },
        "enablement": {"status": enablement, "missing_details": missing},
        "confirmed_via": "user_response",
        "confirmed_at": "2026-08-25T00:00:00+00:00",
        "lifecycle_status": "active",
        "superseded_by": None,
    }


def _promote(case: Path, disclosure: dict | None = None) -> None:
    _add_candidate_question(case)
    item = disclosure or _disclosure()
    _write_json(
        case / "01-technical-disclosures.json",
        {"case_revision": 0, "disclosures": [item]},
    )
    resolve_case_question(
        case,
        "Q003",
        "确认采用该机制",
        "developer-response",
        resolution_type="candidate_confirmed",
        resulting_disclosure_ids=[item["disclosure_id"]],
    )


def _structure(*limitation_ids: str) -> dict:
    return {
        "independent_claims": [
            {
                "claim_id": "I1",
                "claim_number": 1,
                "limitation_ids": list(limitation_ids),
                "distinguishing_limitation_ids": [limitation_ids[-1]],
            }
        ],
        "dependent_claims": [],
    }


def _support(
    limitation_id: str,
    *,
    engineering: list[str],
    disclosures: list[str],
) -> dict:
    return {
        "limitation_id": limitation_id,
        "claim_id": "I1",
        "engineering_evidence_ids": engineering,
        "technical_disclosure_ids": disclosures,
        "specification_sections": ["实施方式5.2"],
        "technical_effect": "形成可供后续模块使用的结构化状态",
        "effect_basis": "mechanism-derived",
        "status": "supported",
    }


def test_engineering_evidence_rejects_developer_confirmation_without_frozen_source() -> None:
    record = {
        "evidence": [
            {
                "evidence_id": "E001",
                "processing_step": "开发者描述处理步骤",
                "state_change": "状态发生变化",
                "technical_effect": "产生预期效果",
                "effect_basis": "mechanism-derived",
                "status": "developer-confirmed",
            }
        ]
    }
    assert validate_schema(record, "engineering-provenance.schema.json")


def test_candidate_completion_cannot_support_candidate_or_claim(tmp_path: Path) -> None:
    case = _case(tmp_path)
    _add_candidate_question(case)
    _write_json(
        case / "02-invention-candidates.json",
        {
            "candidates": [
                {
                    "candidate_id": f"P00{index}",
                    "title": "基于状态映射的处理方案",
                    "technical_problem": "现有状态不能形成结构化输出记录",
                    "mechanism": "根据状态关系生成并传递结构化标签",
                    "distinguishing_features": ["状态与结构化标签的映射"],
                    "technical_effects": ["形成结构化输出记录"],
                    "effect_basis": "mechanism-derived",
                    "engineering_evidence_ids": ["E001"],
                    "technical_disclosure_ids": ["Q003"],
                    "risk": "medium",
                }
                for index in range(1, 4)
            ]
        },
    )
    assert _validate_invention_candidates(case, {})

    _write_json(case / "08-claims-v2-structure.json", _structure("I1-L1"))
    _write_json(
        case / "09-claim-support-map.json",
        {"limitations": [_support("I1-L1", engineering=[], disclosures=["Q003"])]},
    )
    assert _validate_support_map(case, {})


def test_confirmed_but_incomplete_disclosure_cannot_advance(tmp_path: Path) -> None:
    case = _case(tmp_path)
    _promote(case, _disclosure(enablement="incomplete"))
    errors = _validate_evidence_map(case, {})
    assert any("incomplete enablement" in error for error in errors)


def test_td_only_limitation_passes_when_independent_claim_has_engineering_anchor(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    _promote(case)
    _write_json(case / "08-claims-v2-structure.json", _structure("I1-L1", "I1-L2"))
    _write_json(
        case / "09-claim-support-map.json",
        {
            "limitations": [
                _support("I1-L1", engineering=["E001"], disclosures=[]),
                _support("I1-L2", engineering=[], disclosures=["TD001"]),
            ]
        },
    )
    assert _validate_support_map(case, {}) == []


def test_candidate_and_independent_claim_cannot_be_td_only(tmp_path: Path) -> None:
    candidate = {
        "candidates": [
            {
                "candidate_id": f"P00{index}",
                "title": "基于状态映射的处理方案",
                "technical_problem": "现有状态不能形成结构化输出记录",
                "mechanism": "根据状态关系生成并传递结构化标签",
                "distinguishing_features": ["状态与结构化标签的映射"],
                "technical_effects": ["形成结构化输出记录"],
                "effect_basis": "mechanism-derived",
                "engineering_evidence_ids": [],
                "technical_disclosure_ids": ["TD001"],
                "risk": "medium",
            }
            for index in range(1, 4)
        ]
    }
    assert validate_schema(candidate, "invention.schema.json")

    case = _case(tmp_path)
    _promote(case)
    _write_json(case / "08-claims-v2-structure.json", _structure("I1-L1"))
    _write_json(
        case / "09-claim-support-map.json",
        {"limitations": [_support("I1-L1", engineering=[], disclosures=["TD001"])]},
    )
    assert any("engineering-evidence anchors" in error for error in _validate_support_map(case, {}))


def test_superseded_td_makes_old_claim_support_stale(tmp_path: Path) -> None:
    case = _case(tmp_path)
    _promote(case)
    path = case / "01-technical-disclosures.json"
    data = json.loads(path.read_text())
    data["disclosures"][0]["lifecycle_status"] = "superseded"
    data["disclosures"][0]["superseded_by"] = "TD002"
    successor = _disclosure(disclosure_id="TD002")
    data["disclosures"].append(successor)
    _write_json(path, data)
    questions_path = case / "context-questions.json"
    questions = json.loads(questions_path.read_text())
    questions["questions"][-1]["resulting_disclosure_ids"] = ["TD001", "TD002"]
    _write_json(questions_path, questions)

    _write_json(case / "08-claims-v2-structure.json", _structure("I1-L1", "I1-L2"))
    _write_json(
        case / "09-claim-support-map.json",
        {
            "limitations": [
                _support("I1-L1", engineering=["E001"], disclosures=[]),
                _support("I1-L2", engineering=[], disclosures=["TD001"]),
            ]
        },
    )
    assert any(
        "unavailable technical disclosure" in error
        for error in _validate_support_map(case, {})
    )


def test_rejected_and_unknown_answers_never_create_td(tmp_path: Path) -> None:
    rejected = _case(tmp_path / "rejected")
    _add_candidate_question(rejected)
    resolve_case_question(
        rejected,
        "Q003",
        "不是该技术方向",
        "developer-response",
        resolution_type="candidate_rejected",
    )
    rejected_questions = json.loads((rejected / "context-questions.json").read_text())
    assert rejected_questions["questions"][-1]["candidate_completion"]["status"] == "rejected"
    assert json.loads((rejected / "01-technical-disclosures.json").read_text())["disclosures"] == []

    unknown = _case(tmp_path / "unknown")
    _add_candidate_question(unknown)
    resolve_case_question(
        unknown,
        "Q003",
        "目前不知道",
        "developer-response",
        resolution_type="unknown",
    )
    assert any("Unresolved blocking" in error for error in _validate_content_ready(unknown, {}))
    assert json.loads((unknown / "01-technical-disclosures.json").read_text())["disclosures"] == []


def test_effect_basis_rejects_unmeasured_numbers_but_accepts_mechanism_effect(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    evidence_path = case / "01-code-evidence-map.json"
    evidence = json.loads(evidence_path.read_text())
    evidence["evidence"][0]["technical_effect"] = "处理速度提高40%"
    _write_json(evidence_path, evidence)
    assert any("without measured basis" in error for error in _validate_evidence_map(case, {}))

    evidence["evidence"][0]["technical_effect"] = "形成可供后续处理的结构化状态"
    _write_json(evidence_path, evidence)
    assert _validate_evidence_map(case, {}) == []


def test_golden_missing_mechanism_can_be_confirmed_and_traced_to_claim(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path)
    _promote(case)
    assert _validate_evidence_map(case, {}) == []
    advance_stage(case, "INVENTION_CANDIDATES")

    candidates = []
    for index in range(1, 4):
        candidates.append(
            {
                "candidate_id": f"P00{index}",
                "title": "基于状态映射的结构化标签生成方法",
                "technical_problem": "已有中间状态不能直接供后续模块使用",
                "mechanism": "将已有状态映射为结构化标签并传递到输出模块",
                "distinguishing_features": ["状态到结构化标签的映射与传递"],
                "technical_effects": ["形成可供后续模块处理的结构化记录"],
                "effect_basis": "mechanism-derived",
                "engineering_evidence_ids": ["E001"],
                "technical_disclosure_ids": ["TD001"],
                "risk": "medium",
            }
        )
    _write_json(case / "02-invention-candidates.json", {"candidates": candidates})
    assert _validate_invention_candidates(case, {}) == []

    _write_json(case / "08-claims-v2-structure.json", _structure("I1-L1", "I1-L2"))
    _write_json(
        case / "09-claim-support-map.json",
        {
            "limitations": [
                _support("I1-L1", engineering=["E001"], disclosures=[]),
                _support("I1-L2", engineering=[], disclosures=["TD001"]),
            ]
        },
    )
    assert _validate_support_map(case, {}) == []
