import json

from app import main
from app.models import TestCaseResponse as ResponseModel


def sample_response(requirement):
    return ResponseModel.model_validate({
        "requirement": requirement,
        "test_cases": [
            {
                "test_case_id": "TC-001",
                "title": "Verify password reset",
                "category": "Positive",
                "priority": "High",
                "preconditions": [
                    "User has a registered account"
                ],
                "steps": [
                    "Request a password reset"
                ],
                "expected_result": (
                    "A password reset message is delivered"
                ),
                "requirement_reference": "REQ-001"
            }
        ],
        "assumptions": [],
        "source": "gemini"
    })


def test_exact_cache_reuse(monkeypatch):
    requirement = (
        "User receives password reset link by email "
        "valid for 30 minutes"
    )

    monkeypatch.setattr(
        main,
        "get_cached_response",
        lambda req: sample_response(req).model_dump()
    )

    response = main.generate_test_cases(
        main.RequirementRequest(requirement=requirement)
    )

    assert response.source == "database"
    assert response.cache_info.decision == "reuse"
    assert response.cache_info.similarity_score == 1.0


def test_constraint_mismatch_bypasses_cache(monkeypatch):
    old_requirement = (
        "User receives password reset link via email "
        "valid for 30 minutes"
    )

    new_requirement = (
        "User receives password reset code via SMS "
        "valid for 5 minutes"
    )

    monkeypatch.setattr(
        main,
        "get_cached_response",
        lambda req: None
    )

    monkeypatch.setattr(
        main,
        "generate_embedding",
        lambda req: [1.0, 0.0]
    )

    monkeypatch.setattr(
        main,
        "get_all_cached_embeddings",
        lambda: [
            (
                old_requirement,
                sample_response(
                    old_requirement
                ).model_dump_json(),
                json.dumps([1.0, 0.0])
            )
        ]
    )

    monkeypatch.setattr(
        main,
        "calculate_similarity",
        lambda a, b: 0.98
    )

    monkeypatch.setattr(
        main,
        "create_test_cases",
        lambda req: sample_response(req)
    )

    saved = []

    monkeypatch.setattr(
        main,
        "save_cached_response",
        lambda *args: saved.append(args)
    )

    response = main.generate_test_cases(
        main.RequirementRequest(
            requirement=new_requirement
        )
    )

    assert response.source == "gemini"
    assert response.cache_info.decision == "bypass"
    assert response.cache_info.similarity_score == 0.98

    mismatch_fields = {
        item.constraint
        for item in response.cache_info.mismatched_constraints
    }

    assert "channel" in mismatch_fields
    assert "expiry_minutes" in mismatch_fields
    assert len(saved) == 1


def test_compatible_semantic_cache_reuse(monkeypatch):
    old_requirement = (
        "User receives password reset link via email "
        "valid for 30 minutes"
    )

    new_requirement = (
        "A user gets an email password reset link "
        "that expires after 30 minutes"
    )

    monkeypatch.setattr(
        main,
        "get_cached_response",
        lambda req: None
    )

    monkeypatch.setattr(
        main,
        "generate_embedding",
        lambda req: [1.0, 0.0]
    )

    monkeypatch.setattr(
        main,
        "get_all_cached_embeddings",
        lambda: [
            (
                old_requirement,
                sample_response(
                    old_requirement
                ).model_dump_json(),
                json.dumps([1.0, 0.0])
            )
        ]
    )

    monkeypatch.setattr(
        main,
        "calculate_similarity",
        lambda a, b: 0.97
    )

    def unexpected_gemini_call(req):
        raise AssertionError(
            "Gemini should not be called for safe cache reuse"
        )

    monkeypatch.setattr(
        main,
        "create_test_cases",
        unexpected_gemini_call
    )

    response = main.generate_test_cases(
        main.RequirementRequest(
            requirement=new_requirement
        )
    )

    assert response.source == "semantic_cache"
    assert response.cache_info.decision == "reuse"
    assert response.cache_info.mismatched_constraints == []
