
from fastapi import FastAPI, HTTPException

from app.models import RequirementRequest, TestCaseResponse
from app.llm_service import generate_test_cases as create_test_cases


app = FastAPI(
    title="AI-Powered Test Case Generator",
    description="Generate software test cases using AI",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to AI-Powered Test Case Generator!",
        "status": "Application is running"
    }


@app.post(
    "/generate-test-cases",
    response_model=TestCaseResponse
)
def generate_test_cases(request: RequirementRequest):

    try:
        result = create_test_cases(request.requirement)
        return result

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate test cases. Please try again."
        )
