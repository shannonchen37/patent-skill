from patent_skill.claims import (
    render_filing_claims,
    validate_abstract_cn,
    validate_background_assertions,
    validate_claims_cn,
    validate_no_internal_prose_inside_claim_body,
)


def test_valid_simple_claims() -> None:
    text = (
        "1. 一种调度方法，其特征在于，包括获取资源状态。\n"
        "2. 根据权利要求1所述的调度方法，其特征在于，还包括预测资源状态。"
    )
    assert validate_claims_cn(text) == []


def test_rejects_forward_and_nested_multiple_dependency() -> None:
    text = (
        "1. 一种方法，其特征在于，包括A。\n"
        "2. 根据权利要求1或3所述的方法，其特征在于，包括B。\n"
        "3. 根据权利要求1或2所述的方法，其特征在于，包括C。"
    )
    errors = validate_claims_cn(text)
    assert any("earlier" in error for error in errors)
    assert any("multiple dependent" in error for error in errors)


def test_abstract_length_and_promotional_language() -> None:
    assert validate_abstract_cn("卓越" + "中" * 300)


def test_background_model_inference_is_blocked() -> None:
    errors = validate_background_assertions([{"statement": "公知", "status": "model-inferred"}])
    assert errors


def test_filing_claim_renderer_removes_internal_metadata() -> None:
    source = """# Claims V2

> internal drafting note

1. 一种方法，其特征在于，包括：
[I1-L1] 获取数据；
[I1-L2] 根据所述数据生成状态信息。

2. 根据权利要求1所述的方法，其特征在于，还包括缓存结果。
"""
    result = render_filing_claims(source)
    assert result.startswith("# 权利要求书\n")
    assert "# Claims V2" not in result
    assert "> internal" not in result
    assert "[I1-L1]" not in result
    assert "[I1-L2]" not in result
    assert "1. 一种方法" in result
    assert "2. 根据权利要求1" in result


def test_claims_reject_internal_prose_after_formal_claims_begin() -> None:
    source = "1. 一种方法，包括步骤A。\n> drafting note\n"
    assert validate_no_internal_prose_inside_claim_body(source)
