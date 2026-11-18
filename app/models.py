from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator
)


class RequirementRequest(BaseModel):
    requirement: str = Field(min_length=10)


class ConstraintMismatch(BaseModel):
    constraint: str
    cached_value: str | int | float | list[str] | None
    requested_value: str | int | float | list[str] | None


class CacheInfo(BaseModel):
    similarity_score: float | None = None
    decision: Literal["reuse", "bypass", "new_generation"]
    mismatched_constraints: list[ConstraintMismatch] = Field(
        default_factory=list
    )
    reason: str


class TestCase(BaseModel):
    test_case_id: str = Field(min_length=1)
    title: str = Field(min_length=1)

    category: Literal[
        "Positive",
        "Negative",
        "Boundary"
    ]

    priority: Literal[
        "High",
        "Medium",
        "Low"
    ]

    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    requirement_reference: str = Field(min_length=1)

    @field_validator(
        "test_case_id",
        "title",
        "expected_result",
        "requirement_reference"
    )
    @classmethod
    def validate_nonempty_text(cls, value):
        if not value.strip():
            raise ValueError("Field cannot be empty")
        return value

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, steps):
        if any(not step.strip() for step in steps):
            raise ValueError("Test steps cannot be empty")
        return steps

    @field_validator("expected_result")
    @classmethod
    def validate_expected_result(cls, value):
        vague_results = {
            "works",
            "works correctly",
            "should work",
            "success",
            "successful"
        }

        if value.strip().lower() in vague_results:
            raise ValueError(
                "Expected result must be specific and verifiable"
            )

        return value


class TestCaseResponse(BaseModel):
    requirement: str
    test_cases: list[TestCase]
    assumptions: list[str] = Field(default_factory=list)
    source: str = "gemini"
    cache_info: CacheInfo | None = None

    @model_validator(mode="after")
    def validate_unique_ids(self):
        ids = [
            test.test_case_id
            for test in self.test_cases
        ]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "Duplicate test case IDs are not allowed"
            )

        return self


class ChangeImpactRequest(BaseModel):
    previous_requirement: str = Field(min_length=10)
    revised_requirement: str = Field(min_length=10)
    existing_test_cases: list[TestCase] = Field(min_length=1)


class ImpactedTestCase(BaseModel):
    test_case_id: str
    title: str
    classification: Literal[
        "Unchanged",
        "Needs Update",
        "Obsolete"
    ]
    rationale: str


class NewTestRequirement(BaseModel):
    classification: Literal["New Tests Required"] = (
        "New Tests Required"
    )
    description: str
    rationale: str


class ChangeImpactResponse(BaseModel):
    previous_requirement: str
    revised_requirement: str
    impacted_test_cases: list[ImpactedTestCase]
    new_tests_required: list[NewTestRequirement]
    changed_constraints: list[ConstraintMismatch]
    analysis_method: str = "rule_based"

