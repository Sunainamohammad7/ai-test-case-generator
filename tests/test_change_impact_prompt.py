
from app.prompts import build_change_impact_prompt


def test_change_impact_prompt_contains_required_data():
    previous = (
        "Users can export reports in PDF, CSV, "
        "and Excel formats."
    )

    revised = (
        "Users can export reports in PDF "
        "and CSV formats."
    )

    existing_tests = [
        {
            "test_case_id": "TC-001",
            "title": "Verify Excel export",
            "steps": ["Export report as Excel"],
            "expected_result": "Excel file is downloaded."
        }
    ]

    prompt = build_change_impact_prompt(
        previous,
        revised,
        existing_tests,
    )

    assert previous in prompt
    assert revised in prompt
    assert "TC-001" in prompt
    assert "Verify Excel export" in prompt

    assert "Unchanged" in prompt
    assert "Needs Update" in prompt
    assert "Obsolete" in prompt
    assert "New Tests Required" in prompt

    assert "untrusted" in prompt.lower()
