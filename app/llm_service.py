import os
import time
import random

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from pydantic import ValidationError

from app.models import (
    TestCaseResponse,
    ImpactedTestCase,
    NewTestRequirement,
)
from app.prompts import (
    build_test_case_prompt,
    build_change_impact_prompt,
)
from pydantic import BaseModel, Field, model_validator

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Gemini API key is missing!")

client = genai.Client(api_key=api_key)

MODEL_NAME = "gemini-3.5-flash-lite"


class InvalidTestCaseOutputError(Exception):
    """Raised when Gemini returns invalid test cases."""
    pass


class InvalidChangeImpactOutputError(Exception):
    """Raised when Gemini returns invalid change-impact data."""
    pass


class AIChangeImpactResult(BaseModel):
    impacted_test_cases: list[ImpactedTestCase]
    new_tests_required: list[NewTestRequirement] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def validate_unique_test_ids(self):
        ids = [
            item.test_case_id
            for item in self.impacted_test_cases
        ]

        if len(ids) != len(set(ids)):
            raise ValueError(
                "Duplicate test case IDs in change-impact response"
            )

        return self

def generate_test_cases(requirement: str) -> TestCaseResponse:

    prompt = build_test_case_prompt(requirement)

    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TestCaseResponse,
                    temperature=0.2
                )
            )

            if not response.text:
                raise InvalidTestCaseOutputError(
                    "Gemini returned an empty response"
                )

            try:
                result = TestCaseResponse.model_validate_json(
                    response.text
                )
            except (ValidationError, ValueError) as error:
                raise InvalidTestCaseOutputError(
                    f"Invalid generated test cases: {error}"
                ) from error

            return result

        except ServerError as error:
            # Retry only temporary server errors
            if error.code not in (500, 502, 503, 504):
                raise

            if attempt == max_attempts - 1:
                raise

            delay = (2 ** attempt) + random.uniform(0, 0.5)

            print(
                f"Gemini temporarily unavailable. "
                f"Retrying in {delay:.1f} seconds..."
            )

            time.sleep(delay)


def generate_change_impact(
    previous_requirement: str,
    revised_requirement: str,
    existing_test_cases: list,
) -> AIChangeImpactResult:

    test_cases_data = [
        test.model_dump(mode="json")
        if hasattr(test, "model_dump")
        else test
        for test in existing_test_cases
    ]

    prompt = build_change_impact_prompt(
        previous_requirement,
        revised_requirement,
        test_cases_data,
    )

    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=AIChangeImpactResult,
                    temperature=0.1,
                ),
            )

            if not response.text:
                raise InvalidChangeImpactOutputError(
                    "Gemini returned an empty change-impact response."
                )

            try:
                result = AIChangeImpactResult.model_validate_json(
                    response.text
                )
            except (ValidationError, ValueError) as error:
                raise InvalidChangeImpactOutputError(
                    f"Invalid change-impact response: {error}"
                ) from error

            # Validate that Gemini has analyzed exactly
            # the test cases supplied by the user.
            expected_tests = {
                test["test_case_id"]: test["title"]
                for test in test_cases_data
            }

            actual_tests = {
                test.test_case_id: test.title
                for test in result.impacted_test_cases
            }

            if actual_tests != expected_tests:
                raise InvalidChangeImpactOutputError(
                    "Gemini omitted, invented, or modified "
                    "existing test case IDs or titles."
                )
            
            for item in result.impacted_test_cases:
                if not item.rationale.strip():
                    raise InvalidChangeImpactOutputError(
                        f"Missing rationale for {item.test_case_id}"
                    )

            for item in result.new_tests_required:
                if (
                    not item.description.strip()
                    or not item.rationale.strip()
                ):
                    raise InvalidChangeImpactOutputError(
                        "New test requirement contains "
                        "an empty description or rationale."
                    )           

            return result

        except ServerError as error:
            if error.code not in (500, 502, 503, 504):
                raise

            if attempt == max_attempts - 1:
                raise

            delay = (2 ** attempt) + random.uniform(0, 0.5)

            print(
                "Gemini change-impact analysis temporarily "
                f"unavailable. Retrying in {delay:.1f} seconds..."
            )

            time.sleep(delay)

