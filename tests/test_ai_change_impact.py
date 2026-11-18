import json, pytest
from unittest.mock import patch, MagicMock

from app.llm_service import generate_change_impact, AIChangeImpactResult, InvalidChangeImpactOutputError
from app.main import app
from fastapi.testclient import TestClient


client=TestClient(app)


def test_generate_change_impact_valid_response():
    previous = (
        "Users can export reports in PDF, CSV and Excel."
    )

    revised = (
        "Users can export reports in PDF and CSV."
    )

    existing_tests = [
        {
            "test_case_id": "TC-001",
            "title": "Verify Excel export",
            "category": "Positive",
            "priority": "High",
            "preconditions": [],
            "steps": ["Export report as Excel."],
            "expected_result": "An Excel file is downloaded.",
            "requirement_reference": "REQ-001",
        }
    ]

    mocked_response = {
        "impacted_test_cases": [
            {
                "test_case_id": "TC-001",
                "title": "Verify Excel export",
                "classification": "Obsolete",
                "rationale": (
                    "Excel export is no longer supported."
                ),
            }
        ],
        "new_tests_required": [],
    }

    mock_gemini_response = MagicMock()
    mock_gemini_response.text = json.dumps(mocked_response)

    with patch(
        "app.llm_service.client.models.generate_content",
        return_value=mock_gemini_response,
    ) as mock_generate:

        result = generate_change_impact(
            previous,
            revised,
            existing_tests,
        )

        assert (
            result.impacted_test_cases[0].classification
            == "Obsolete"
        )

        assert (
            result.impacted_test_cases[0].test_case_id
            == "TC-001"
        )

        mock_generate.assert_called_once()

def test_ai_change_impact_endpoint():
    previous = (
        "Users can export reports in PDF, CSV and Excel."
    )

    revised = (
        "Users can export reports in PDF and CSV."
    )

    existing_test = {
        "test_case_id": "TC-001",
        "title": "Verify Excel export",
        "category": "Positive",
        "priority": "High",
        "preconditions": [],
        "steps": ["Export the report in Excel format."],
        "expected_result": "An Excel file is downloaded.",
        "requirement_reference": "REQ-001",
    }

    mock_result = AIChangeImpactResult.model_validate({
        "impacted_test_cases": [
            {
                "test_case_id": "TC-001",
                "title": "Verify Excel export",
                "classification": "Obsolete",
                "rationale": "Excel export was removed.",
            }
        ],
        "new_tests_required": [],
    })

    with patch(
        "app.main.generate_change_impact",
        return_value=mock_result,
    ) as mock_generate:

        response = client.post(
            "/analyze-change-impact",
            json={
                "previous_requirement": previous,
                "revised_requirement": revised,
                "existing_test_cases": [existing_test],
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["analysis_method"] == "gemini"

        assert (
            data["impacted_test_cases"][0]["classification"]
            == "Obsolete"
        )

        assert (
            data["impacted_test_cases"][0]["test_case_id"]
            == "TC-001"
        )

        mock_generate.assert_called_once()

def test_ai_change_impact_rejects_missing_test_cases():
    previous = "Users can export reports in PDF and Excel."
    revised = "Users can export reports in PDF only."

    existing_tests = [
        {
            "test_case_id": "TC-001",
            "title": "Verify Excel export",
        },
        {
            "test_case_id": "TC-002",
            "title": "Verify PDF export",
        },
    ]

    invalid_response = {
        "impacted_test_cases": [
            {
                "test_case_id": "TC-001",
                "title": "Verify Excel export",
                "classification": "Obsolete",
                "rationale": "Excel export was removed.",
            }
        ],
        "new_tests_required": [],
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(invalid_response)

    with patch(
        "app.llm_service.client.models.generate_content",
        return_value=mock_response,
    ):
        with pytest.raises(InvalidChangeImpactOutputError):
            generate_change_impact(
                previous,
                revised,
                existing_tests,
            )


@pytest.mark.parametrize(
    "exception",
    [
        InvalidChangeImpactOutputError(
            "Gemini returned invalid JSON"
        ),
        RuntimeError("Gemini service unavailable"),
    ],
)
def test_change_impact_endpoint_handles_ai_failure(exception):
    existing_test = {
        "test_case_id": "TC-001",
        "title": "Verify Excel export",
        "category": "Positive",
        "priority": "High",
        "preconditions": [],
        "steps": ["Export the report as Excel."],
        "expected_result": "An Excel file is downloaded.",
        "requirement_reference": "REQ-001",
    }

    with patch(
        "app.main.generate_change_impact",
        side_effect=exception,
    ):
        response = client.post(
            "/analyze-change-impact",
            json={
                "previous_requirement": (
                    "Users can export reports as PDF and Excel."
                ),
                "revised_requirement": (
                    "Users can export reports as PDF only."
                ),
                "existing_test_cases": [existing_test],
            },
        )

    assert response.status_code == 502
    assert "detail" in response.json()
