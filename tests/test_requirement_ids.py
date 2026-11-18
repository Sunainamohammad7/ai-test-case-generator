from app.database import (
    initialize_database,
    get_or_create_requirement_id,
)
from app.main import assign_requirement_reference
from app.models import TestCaseResponse as ResponseModel


def test_same_requirement_keeps_same_id():
    initialize_database()

    requirement = (
        "User can download an account statement "
        "as a PDF file."
    )

    first_id = get_or_create_requirement_id(requirement)
    second_id = get_or_create_requirement_id(requirement)

    assert first_id == second_id


def test_different_requirements_get_different_ids():
    initialize_database()

    first_id = get_or_create_requirement_id(
        "User can download an account statement."
    )

    second_id = get_or_create_requirement_id(
        "User can upload a profile picture."
    )

    assert first_id != second_id


def test_all_test_cases_share_requirement_id():
    initialize_database()

    requirement = (
        "User can download an account statement "
        "as a PDF file."
    )

    response = ResponseModel.model_validate({
        "requirement": requirement,
        "test_cases": [
            {
                "test_case_id": "TC-001",
                "title": "Verify PDF download",
                "category": "Positive",
                "priority": "High",
                "preconditions": ["User is logged in"],
                "steps": ["Click the download button"],
                "expected_result": (
                    "A PDF statement is downloaded."
                ),
                "requirement_reference": "PENDING",
            },
            {
                "test_case_id": "TC-002",
                "title": "Verify download failure",
                "category": "Negative",
                "priority": "Medium",
                "preconditions": ["User is logged in"],
                "steps": ["Simulate a failed download"],
                "expected_result": (
                    "An error message is displayed."
                ),
                "requirement_reference": "PENDING",
            },
        ],
    })

    updated = assign_requirement_reference(
        response,
        requirement,
    )

    references = {
        case.requirement_reference
        for case in updated.test_cases
    }

    assert len(references) == 1
    assert next(iter(references)).startswith("REQ-")
