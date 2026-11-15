
import json

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.models import RequirementRequest, TestCaseResponse

from app.llm_service import (
    generate_test_cases as create_test_cases
)

from app.database import (
    initialize_database,
    get_cached_response,
    save_cached_response,
    get_all_cached_embeddings
)

from app.embedding_service import (
    generate_embedding,
    calculate_similarity
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database when application starts."""

    initialize_database()

    yield


app = FastAPI(
    title="AI-Powered Test Case Generator",
    description="Generate software test cases using AI",
    version="2.0.0",
    lifespan=lifespan
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
        # STEP 1: Check exact cache first
        cached_data = get_cached_response(
            request.requirement
        )

        if cached_data is not None:

            cached_data["requirement"] = request.requirement
            cached_data["source"] = "database"

            return TestCaseResponse.model_validate(
                cached_data
            )

        # STEP 2: Generate embedding for new requirement
        new_embedding = generate_embedding(
            request.requirement
        )

        # STEP 3: Retrieve existing embeddings
        cached_records = get_all_cached_embeddings()

        similarity_threshold = 0.85

        best_match = None
        best_similarity = 0.0

        # STEP 4: Compare embeddings
        for requirement, response_json, stored_embedding_json in cached_records:

            stored_embedding = json.loads(
                stored_embedding_json
            )

            similarity = calculate_similarity(
                new_embedding,
                stored_embedding
            )

            if similarity > best_similarity:

                best_similarity = similarity
                best_match = response_json

        # STEP 5: Return semantic cache result if sufficiently similar
        if (
            best_match is not None
            and best_similarity >= similarity_threshold
        ):

            cached_data = json.loads(best_match)

            cached_data["requirement"] = request.requirement
            cached_data["source"] = "semantic_cache"

            return TestCaseResponse.model_validate(
                cached_data
            )

        # STEP 6: Generate new test cases using Gemini
        result = create_test_cases(
            request.requirement
        )

        # STEP 7: Save response and embedding in SQLite
        save_cached_response(
            request.requirement,
            result,
            new_embedding
        )

        return result.model_copy(
            update={"source": "gemini"}
        )

    except Exception as error:

        print(f"Error generating test cases: {error}")

        raise HTTPException(
            status_code=502,
            detail="Unable to generate test cases. Please try again."
        )
