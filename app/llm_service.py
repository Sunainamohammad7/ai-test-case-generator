
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.models import TestCaseResponse
from app.prompts import build_test_case_prompt


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Gemini API key is missing!")

client = genai.Client(api_key=api_key)


def generate_test_cases(requirement: str) -> TestCaseResponse:

    prompt = build_test_case_prompt(requirement)

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TestCaseResponse,
            temperature=0.2
        )
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response")

    result = TestCaseResponse.model_validate_json(response.text)

    return result
