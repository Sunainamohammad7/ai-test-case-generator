import json
import os

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body, Query
from pydantic import ValidationError
from typing import Union

from app.models import (
    ChangeImpactRequest,
    ChangeImpactResponse,
)

from app.change_impact_service import analyze_change_impact

from app.models import (
    RequirementRequest,
    TestCaseResponse,
    CacheInfo
)

from app.llm_service import (
    generate_test_cases as create_test_cases,
    InvalidTestCaseOutputError
)

from app.llm_service import (
    generate_change_impact,
    InvalidChangeImpactOutputError,
)


from app.database import (
    initialize_database,
    get_cached_response,
    save_cached_response,
    get_all_cached_embeddings,
    normalize_requirement,
    get_or_create_requirement_id,
)


from app.embedding_service import (
    generate_embedding,
    calculate_similarity
)

from app.constraint_service import compare_constraints
from app.models import ChangeImpactResponse

load_dotenv()

SIMILARITY_THRESHOLD = float(
    os.getenv("SIMILARITY_THRESHOLD", "0.85")
)

if not 0 <= SIMILARITY_THRESHOLD <= 1:
    raise ValueError(
        "SIMILARITY_THRESHOLD must be between 0 and 1"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="AI-Powered Test Case Generator",
    description=(
        "Generate validated test cases with "
        "constraint-aware semantic caching"
    ),
    version="2.2.0",
    lifespan=lifespan
)


@app.get("/")
def home():
    return {
        "message": "Welcome to AI-Powered Test Case Generator!",
        "status": "Application is running"
    }


def assign_requirement_reference(
    response: TestCaseResponse,
    requirement: str,
) -> TestCaseResponse:
    """
    Assign a stable requirement ID to every test case.
    Validate the updated response before returning it.
    """

    requirement_id = get_or_create_requirement_id(
        requirement
    )

    updated_cases = [
        test_case.model_copy(
            update={
                "requirement_reference": requirement_id
            }
        )
        for test_case in response.test_cases
    ]

    updated_response = response.model_copy(
        update={
            "requirement": requirement,
            "test_cases": updated_cases,
        }
    )

    return TestCaseResponse.model_validate(
        updated_response.model_dump(mode="json")
    )


@app.post(
    "/generate-test-cases",
    response_model=TestCaseResponse
)
def generate_test_cases(request: RequirementRequest):

    try:
        # STEP 1: Exact cache lookup
        cached_data = get_cached_response(
            request.requirement
        )

        if cached_data is not None:
            validated_cache = TestCaseResponse.model_validate(
                cached_data
            )
            validated_cache = assign_requirement_reference(
                validated_cache,
                request.requirement,
            )

            return validated_cache.model_copy(
                update={
                    "requirement": request.requirement,
                    "source": "database",
                    "cache_info": CacheInfo(
                        similarity_score=1.0,
                        decision="reuse",
                        reason="Exact requirement found in cache."
                    )
                }
            )

        # STEP 2: Generate embedding
        new_embedding = generate_embedding(
            request.requirement
        )


        # STEP 3: Retrieve semantic cache candidates
        cached_records = get_all_cached_embeddings()

        best_candidate = None
        best_candidate_score = -1.0
        best_candidate_mismatches = []

        best_safe_match = None
        best_safe_score = -1.0

        # STEP 4: Evaluate every valid candidate
        for (
            stored_requirement,
            response_json,
            stored_embedding_json,
        ) in cached_records:

            try:
                if normalize_requirement(
                    stored_requirement
                ) == normalize_requirement(
                    request.requirement
                ):
                    continue

                stored_embedding = json.loads(
                    stored_embedding_json
                )

                cached_response = (
                    TestCaseResponse.model_validate_json(
                        response_json
                    )
                )

                similarity = calculate_similarity(
                    new_embedding,
                    stored_embedding
                )

                mismatches = compare_constraints(
                    stored_requirement,
                    request.requirement
                )

                # Track the highest-scoring candidate
                # for explaining bypass decisions.
                if similarity > best_candidate_score:
                    best_candidate = cached_response
                    best_candidate_score = similarity
                    best_candidate_mismatches = mismatches

                # Only consider candidates that pass
                # BOTH similarity and constraint checks.
                if (
                    similarity >= SIMILARITY_THRESHOLD
                    and not mismatches
                    and similarity > best_safe_score
                ):
                    best_safe_match = cached_response
                    best_safe_score = similarity

            except (
                ValidationError,
                ValueError,
                TypeError,
                ZeroDivisionError,
            ):
                print(
                    "Skipping invalid semantic cache entry."
                )
                continue

        # STEP 5: Reuse the best safe candidate
        if best_safe_match is not None:
            updated_match = assign_requirement_reference(
                best_safe_match,
                request.requirement,
            )

            return updated_match.model_copy(
                update={
                    "source": "semantic_cache",
                    "cache_info": CacheInfo(
                        similarity_score=round(
                            best_safe_score, 4
                        ),
                        decision="reuse",
                        mismatched_constraints=[],
                        reason=(
                            "A compatible cached requirement "
                            "passed the similarity threshold "
                            "and all recognized constraint checks."
                        ),
                    ),
                }
            )

        # STEP 6: No safe match. Generate new tests.
        similarity_score = (
            round(best_candidate_score, 4)
            if best_candidate is not None
            else None
        )

        mismatches = best_candidate_mismatches

        if best_candidate is None:
            decision = "new_generation"
            reason = (
                "No valid semantic cache candidate found."
            )

        elif best_candidate_score < SIMILARITY_THRESHOLD:
            decision = "bypass"
            reason = (
                "The highest similarity score is below "
                "the configured threshold."
            )

        else:
            decision = "bypass"

            fields = ", ".join(
                item["constraint"]
                for item in mismatches
            )

            reason = (
                "Similarity meets the threshold, but "
                "material constraints differ: "
                f"{fields}. Generating new test cases."
            )


        # STEP 7: Generate fresh test cases
        result = create_test_cases(
            request.requirement
        )

        try:
            validated_result = (
                TestCaseResponse.model_validate(result)
            )

        except ValidationError as error:
            raise InvalidTestCaseOutputError(
                f"Generated test cases failed validation: {error}"
            ) from error


        # Assign the correct requirement ID to all test cases
        validated_result = assign_requirement_reference(
            validated_result,
            request.requirement
        )

        # STEP 8: Save only validated test cases
        # Exclude request-specific cache metadata
        clean_response = validated_result.model_copy(
            update={
                "requirement": request.requirement,
                "source": "gemini",
                "cache_info": None
            }
        )

        save_cached_response(
            request.requirement,
            clean_response,
            new_embedding
        )


        # STEP 9: Return generation and cache decision details
        return clean_response.model_copy(
            update={
                "cache_info": CacheInfo(
                    similarity_score=similarity_score,
                    decision=decision,
                    mismatched_constraints=mismatches,
                    reason=reason
                )
            }
        )

    except InvalidTestCaseOutputError as error:
        print(f"Invalid Gemini output: {error}")

        raise HTTPException(
            status_code=502,
            detail=(
                "AI generated invalid test cases. "
                "Nothing was cached."
            )
        ) from error

    except Exception as error:
        import traceback

        print(f"Error generating test cases: {error}")
        traceback.print_exc()

        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to generate test cases. "
                "Please try again."
            )
        ) from error

@app.post(
    "/analyze-change-impact",
    response_model=ChangeImpactResponse,
)
def analyze_requirement_change(
    request_data: Union[
        TestCaseResponse,
        ChangeImpactRequest,
    ] = Body(...),
    revised_requirement: str | None = Query(
        default=None,
        min_length=10,
        description=(
            "Enter the revised requirement here when "
            "pasting the full response from Endpoint 1."
        ),
    ),
):
    """
    Supports two input formats:

    1. Full response from /generate-test-cases,
       with revised_requirement in the query box.

    2. Original ChangeImpactRequest containing
       previous_requirement, revised_requirement,
       and existing_test_cases.
    """

    if isinstance(request_data, ChangeImpactRequest):
        impact_request = request_data

    else:
        if not revised_requirement:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Enter revised_requirement in the "
                    "Swagger parameter field."
                ),
            )

        if not request_data.test_cases:
            raise HTTPException(
                status_code=422,
                detail="No existing test cases were provided.",
            )

        try:
            impact_request = ChangeImpactRequest(
                previous_requirement=request_data.requirement,
                revised_requirement=revised_requirement,
                existing_test_cases=request_data.test_cases,
            )
        except ValidationError as error:
            raise HTTPException(
                status_code=422,
                detail=error.errors(
                    include_context=False
                ),
            ) from error


    try:
        ai_result = generate_change_impact(
            previous_requirement=impact_request.previous_requirement,
            revised_requirement=impact_request.revised_requirement,
            existing_test_cases=impact_request.existing_test_cases,
        )

        # Build the complete response using the existing schema.
        return ChangeImpactResponse(
            previous_requirement=impact_request.previous_requirement,
            revised_requirement=impact_request.revised_requirement,
            impacted_test_cases=ai_result.impacted_test_cases,
            new_tests_required=ai_result.new_tests_required,
            changed_constraints=compare_constraints(
                impact_request.previous_requirement,
                impact_request.revised_requirement,
            ),
            analysis_method="gemini",
        )

    except InvalidChangeImpactOutputError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "AI returned invalid change-impact analysis. "
                "Please review the requirements and try again."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to complete AI change-impact analysis. "
                "Please try again."
            ),
        ) from error


    
