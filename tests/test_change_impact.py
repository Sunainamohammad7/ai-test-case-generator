from app.change_impact_service import analyze_change_impact
from app.models import ChangeImpactRequest


def make_test_case(
    test_id="TC-001",
    title="Verify password reset expiry"
):
    return {
        "test_case_id": test_id,
        "title": title,
        "category": "Positive",
        "priority": "High",
        "preconditions": ["User is registered"],
        "steps": [
            "Request password reset",
            "Wait for the reset link to expire"
        ],
        "expected_result": (
            "The reset link expires after 30 minutes"
        ),
        "requirement_reference": "REQ-001"
    }


def analyze(previous, revised, tests=None):
    request = ChangeImpactRequest(
        previous_requirement=previous,
        revised_requirement=revised,
        existing_test_cases=tests or [make_test_case()]
    )
    return analyze_change_impact(request)


def test_unchanged_requirement():
    requirement = (
        "User can reset password using an email link "
        "valid for 30 minutes"
    )

    result = analyze(requirement, requirement)

    assert (
        result.impacted_test_cases[0].classification
        == "Unchanged"
    )


def test_expiry_change_needs_update():
    result = analyze(
        "User can reset password using an email link "
        "valid for 30 minutes",
        "User can reset password using an email link "
        "valid for 10 minutes"
    )

    assert (
        result.impacted_test_cases[0].classification
        == "Needs Update"
    )

    assert any(
        item.constraint == "expiry_minutes"
        for item in result.changed_constraints
    )


def test_removed_capability_obsolete():
    result = analyze(
        "Users can reset password and export reports",
        "Users can only export reports"
    )

    assert (
        result.impacted_test_cases[0].classification
        == "Obsolete"
    )


def test_new_capability_requires_tests():
    result = analyze(
        "Users can reset password",
        "Users can reset password and export reports"
    )

    assert any(
        "export" in item.description
        for item in result.new_tests_required
    )


def test_changed_constraint_requires_coverage():
    result = analyze(
        "User can reset password using email "
        "valid for 30 minutes",
        "User can reset password using SMS "
        "valid for 5 minutes"
    )

    assert len(result.new_tests_required) >= 2
