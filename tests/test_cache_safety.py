
import json
import sqlite3

import pytest
from pydantic import ValidationError

from app import database


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    db_path = tmp_path / "test_cache.db"

    monkeypatch.setattr(
        database,
        "DATABASE_PATH",
        db_path
    )

    database.initialize_database()

    return db_path


def valid_response():
    return {
        "requirement": "User can log in with email",
        "test_cases": [
            {
                "test_case_id": "TC-001",
                "title": "Verify successful login",
                "category": "Positive",
                "priority": "High",
                "preconditions": [
                    "User has a registered account"
                ],
                "steps": [
                    "Enter valid email",
                    "Enter valid password",
                    "Click Login"
                ],
                "expected_result": (
                    "User is redirected to the dashboard"
                ),
                "requirement_reference": "REQ-001"
            }
        ],
        "assumptions": [],
        "source": "gemini"
    }


def test_valid_response_is_cached(test_database):
    response = valid_response()

    database.save_cached_response(
        response["requirement"],
        response,
        [0.1, 0.2, 0.3]
    )

    cached = database.get_cached_response(
        response["requirement"]
    )

    assert cached is not None
    assert cached["test_cases"][0]["test_case_id"] == "TC-001"


def test_duplicate_ids_never_cached(test_database):
    response = valid_response()

    duplicate = response["test_cases"][0].copy()
    response["test_cases"].append(duplicate)

    with pytest.raises(ValidationError):
        database.save_cached_response(
            response["requirement"],
            response
        )

    assert database.get_cached_response(
        response["requirement"]
    ) is None


def test_empty_steps_never_cached(test_database):
    response = valid_response()

    response["test_cases"][0]["steps"] = []

    with pytest.raises(ValidationError):
        database.save_cached_response(
            response["requirement"],
            response
        )

    assert database.get_cached_response(
        response["requirement"]
    ) is None


def test_invalid_old_cache_is_skipped(test_database):
    requirement = "User can log in with email"

    with sqlite3.connect(test_database) as connection:
        connection.execute("""
            INSERT INTO test_cases (
                requirement,
                normalized_requirement,
                response_json,
                embedding_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            requirement,
            database.normalize_requirement(requirement),
            '{"invalid": true}',
            None,
            "2026-01-01T00:00:00"
        ))

    assert database.get_cached_response(
        requirement
    ) is None


def test_valid_response_replaces_old_cache(test_database):
    response = valid_response()

    database.save_cached_response(
        response["requirement"],
        response
    )

    updated_response = valid_response()

    updated_response["test_cases"][0]["title"] = (
        "Verify login with registered credentials"
    )

    database.save_cached_response(
        updated_response["requirement"],
        updated_response
    )

    cached = database.get_cached_response(
        updated_response["requirement"]
    )

    assert cached["test_cases"][0]["title"] == (
        "Verify login with registered credentials"
    )
