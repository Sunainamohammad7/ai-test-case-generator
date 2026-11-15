
import sqlite3
import json

from pathlib import Path
from datetime import datetime, timezone


# Store database in the project root directory
DATABASE_PATH = Path(__file__).resolve().parent.parent / "test_cases.db"


def get_connection():
    """Create a connection to the SQLite database."""
    return sqlite3.connect(DATABASE_PATH)


def normalize_requirement(requirement: str) -> str:
    """Normalize text for exact matching."""
    return " ".join(requirement.strip().lower().split())


def initialize_database():
    """Create the database table if it doesn't exist."""

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

        # Add embedding column to existing databases if needed
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

    finally:
        connection.close()


def get_cached_response(requirement: str):
    """Retrieve an exact cached response."""

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

        if result:
            return json.loads(result[0])

        return None

    finally:
        connection.close()


def save_cached_response(
    requirement: str,
    response,
    embedding=None
):
    """Save generated test cases and their embedding."""

    normalized = normalize_requirement(requirement)

    if hasattr(response, "model_dump"):
        response_data = response.model_dump(mode="json")
    else:
        response_data = response

    response_json = json.dumps(
        response_data,
        ensure_ascii=False
    )

    embedding_json = (
        json.dumps(embedding)
        if embedding is not None
        else None
    )

    created_at = datetime.now(timezone.utc).isoformat()

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
            ON CONFLICT(normalized_requirement) DO NOTHING
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
    """Retrieve all stored requirements and embeddings."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT requirement, response_json, embedding_json
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
    """Save an embedding for an existing requirement."""

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
