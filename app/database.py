import sqlite3
import json

from pathlib import Path
from datetime import datetime, timezone

from app.models import TestCaseResponse


DATABASE_PATH = (
    Path(__file__).resolve().parent.parent
    / "test_cases.db"
)


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def normalize_requirement(requirement: str) -> str:
    return " ".join(
        requirement.strip().lower().split()
    )


def initialize_database():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requirement TEXT NOT NULL,
                normalized_requirement TEXT UNIQUE NOT NULL,
                response_json TEXT NOT NULL,
                embedding_json TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("PRAGMA table_info(test_cases)")

        columns = [
            row[1] for row in cursor.fetchall()
        ]

        if "embedding_json" not in columns:
            cursor.execute("""
                ALTER TABLE test_cases
                ADD COLUMN embedding_json TEXT
            """)

        connection.commit()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_requirement TEXT NOT NULL UNIQUE
            )
        """)


    finally:
        connection.close()


def get_cached_response(requirement: str):
    normalized = normalize_requirement(requirement)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT response_json
            FROM test_cases
            WHERE normalized_requirement = ?
        """, (normalized,))

        result = cursor.fetchone()

        if result is None:
            return None

        try:
            cached_response = (
                TestCaseResponse.model_validate_json(
                    result[0]
                )
            )

            return cached_response.model_dump(
                mode="json"
            )

        except (ValueError, TypeError) as error:
            print(
                f"Invalid exact cache entry skipped: {error}"
            )
            return None

    finally:
        connection.close()


def save_cached_response(
    requirement: str,
    response,
    embedding=None
):
    # Validate before saving anything
    validated_response = (
        TestCaseResponse.model_validate(response)
    )

    response_json = json.dumps(
        validated_response.model_dump(mode="json"),
        ensure_ascii=False
    )

    embedding_json = (
        json.dumps(embedding)
        if embedding is not None
        else None
    )

    normalized = normalize_requirement(requirement)

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO test_cases (
                requirement,
                normalized_requirement,
                response_json,
                embedding_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(normalized_requirement)
            DO UPDATE SET
                requirement = excluded.requirement,
                response_json = excluded.response_json,
                embedding_json = excluded.embedding_json,
                created_at = excluded.created_at
        """, (
            requirement,
            normalized,
            response_json,
            embedding_json,
            created_at
        ))

        connection.commit()

    finally:
        connection.close()


def get_all_cached_embeddings():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                requirement,
                response_json,
                embedding_json
            FROM test_cases
            WHERE embedding_json IS NOT NULL
        """)

        return cursor.fetchall()

    finally:
        connection.close()


def save_embedding(
    requirement: str,
    embedding: list[float]
):
    normalized = normalize_requirement(requirement)

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE test_cases
            SET embedding_json = ?
            WHERE normalized_requirement = ?
        """, (
            json.dumps(embedding),
            normalized
        ))

        connection.commit()

    finally:
        connection.close()


def get_or_create_requirement_id(requirement: str) -> str:
    """
    Return a stable ID for a requirement.

    The same normalized requirement always receives
    the same ID.
    """

    normalized = normalize_requirement(requirement)

    if not normalized:
        raise ValueError("Requirement cannot be empty.")

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO requirements (
                normalized_requirement
            )
            VALUES (?)
        """, (normalized,))

        cursor.execute("""
            SELECT id
            FROM requirements
            WHERE normalized_requirement = ?
        """, (normalized,))

        row = cursor.fetchone()

        if row is None:
            raise RuntimeError(
                "Unable to retrieve requirement ID."
            )

        connection.commit()

        return f"REQ-{row[0]:03d}"

    finally:
        connection.close()
