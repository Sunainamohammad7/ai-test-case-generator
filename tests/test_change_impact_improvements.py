
from fastapi.testclient import TestClient

from app.main import app
from app.models import ChangeImpactRequest
from app.change_impact_service import analyze_change_impact

client = TestClient(app)

OLD = (
    "User receives a password reset link via email "
    "valid for 30 minutes."
)

NEW = (
    "User receives a password reset link via email "
    "valid for 10 minutes."
)


def sample_tests():
    def make_case(test_id, title, steps, expected):
        return {
            "test_case_id": test_id,
            "title": title,
            "category": "Positive",
            "priority": "High",
            "preconditions": ["User is registered"],
            "steps": steps,
            "expected_result": expected,
            "requirement_reference": "REQ-001",
        }

    return [
        make_case(
            "TC-001",
            "Verify email delivery",
            ["Request password reset", "Check email inbox"],
            "Reset email containing a link is received",
        ),
        make_case(
            "TC-002",
            "Verify 30-minute validity window",
            ["Use reset link within 30 minutes"],
            "Password reset page is displayed",
        ),
        make_case(
            "TC-003",
            "Verify 30-minute boundary",
            ["Use reset link at the 30-minute boundary"],
            "Expiry behavior is enforced at the boundary",
        ),
        make_case(
            "TC-004",
            "Verify expired link",
            ["Use link after 30 minutes"],
            "Expired link is rejected",
        ),
        make_case(
            "TC-005",
            "Verify link reuse",
            ["Use an already consumed link"],
            "Previously used link is rejected",
        ),
        make_case(
            "TC-006",
            "Verify invalid link",
            ["Modify the reset token"],
            "Invalid reset token is rejected",
        ),
    ]


def test_expiry_classification():
    request = ChangeImpactRequest(
        previous_requirement=OLD,
        revised_requirement=NEW,
        existing_test_cases=sample_tests(),
    )

    result = analyze_change_impact(request)

    classifications = {
        test.test_case_id: test.classification
        for test in result.impacted_test_cases
    }

    assert classifications == {
        "TC-001": "Unchanged",
        "TC-002": "Needs Update",
        "TC-003": "Needs Update",
        "TC-004": "Needs Update",
        "TC-005": "Unchanged",
        "TC-006": "Unchanged",
    }


def test_full_response_format():
    generation_response = {
        "requirement": OLD,
        "test_cases": sample_tests(),
        "assumptions": [],
        "source": "database",
        "cache_info": {
            "similarity_score": 1.0,
            "decision": "reuse",
            "mismatched_constraints": [],
            "reason": "Exact requirement found in cache.",
        },
    }

    response = client.post(
        "/analyze-change-impact",
        params={"revised_requirement": NEW},
        json=generation_response,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["impacted_test_cases"]) == 6
    assert data["changed_constraints"][0]["constraint"] == (
        "expiry_minutes"
    )


def test_original_assignment_format():
    request_body = {
        "previous_requirement": OLD,
        "revised_requirement": NEW,
        "existing_test_cases": sample_tests(),
    }

    response = client.post(
        "/analyze-change-impact",
        json=request_body,
    )

    assert response.status_code == 200
    assert len(response.json()["impacted_test_cases"]) == 6


def test_missing_revised_requirement():
    generation_response = {
        "requirement": OLD,
        "test_cases": sample_tests(),
    }

    response = client.post(
        "/analyze-change-impact",
        json=generation_response,
    )

    assert response.status_code == 422


def test_invalid_revised_requirement():
    generation_response = {
        "requirement": OLD,
        "test_cases": sample_tests(),
    }

    response = client.post(
        "/analyze-change-impact",
        params={"revised_requirement": "short"},
        json=generation_response,
    )

    assert response.status_code == 422
