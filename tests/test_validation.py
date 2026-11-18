
import pytest

from pydantic import ValidationError

from app.models import TestCaseResponse as ResponseModel


def valid_test_case(test_id):
    return {
        "test_case_id": test_id,
        "title": "Verify valid login",
        "category": "Positive",
        "priority": "High",
        "preconditions": ["User is registered"],
        "steps": [
            "Enter valid email and password",
            "Click Login"
        ],
        "expected_result": (
            "User is redirected to the dashboard"
        ),
        "requirement_reference": "REQ-001"
    }


def test_valid_response():
    response = ResponseModel.model_validate({
        "requirement": "User can log in using email and password",
        "test_cases": [valid_test_case("TC-001")],
        "assumptions": []
    })

    assert len(response.test_cases) == 1


def test_duplicate_ids_rejected():
    with pytest.raises(ValidationError):
        ResponseModel.model_validate({
            "requirement": "User can log in using email and password",
            "test_cases": [
                valid_test_case("TC-001"),
                valid_test_case("TC-001")
            ],
            "assumptions": []
        })


def test_empty_steps_rejected():
    test_case = valid_test_case("TC-002")
    test_case["steps"] = []

    with pytest.raises(ValidationError):
        ResponseModel.model_validate({
            "requirement": "User can log in using email and password",
            "test_cases": [test_case],
            "assumptions": []
        })


def test_invalid_priority_rejected():
    test_case = valid_test_case("TC-003")
    test_case["priority"] = "Urgent"

    with pytest.raises(ValidationError):
        ResponseModel.model_validate({
            "requirement": "User can log in using email and password",
            "test_cases": [test_case],
            "assumptions": []
        })


def test_malformed_json_rejected():
    with pytest.raises(ValidationError):
        ResponseModel.model_validate_json(
            '{"requirement": "Login", "test_cases": [}'
        )
