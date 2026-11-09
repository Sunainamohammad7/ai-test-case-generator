
from pydantic import BaseModel, Field


class RequirementRequest(BaseModel):
    requirement: str = Field(
        min_length=10,
        description="Software requirement provided by the user"
    )


class TestCase(BaseModel):
    test_case_id: str = Field(
        description="Unique test case identifier"
    )

    title: str = Field(
        description="Short test case title"
    )

    category: str = Field(
        description="Positive, negative or boundary"
    )

    priority: str = Field(
        description="High, Medium or Low"
    )

    preconditions: list[str] = Field(
        description="Conditions required before testing"
    )

    steps: list[str] = Field(
        description="Steps to execute the test case"
    )

    expected_result: str = Field(
        description="Expected outcome of the test"
    )


class TestCaseResponse(BaseModel):
    requirement: str
    test_cases: list[TestCase]
    assumptions: list[str]
