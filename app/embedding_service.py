
import os
import math

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Gemini API key is missing!")

client = genai.Client(api_key=api_key)

EMBEDDING_MODEL = "gemini-embedding-2"


def generate_embedding(text: str) -> list[float]:
    """Convert text into a numerical embedding vector."""

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config={
            "output_dimensionality": 768
        }
    )

    return response.embeddings[0].values


def calculate_similarity(
    embedding1: list[float],
    embedding2: list[float],
) -> float:
    """Calculate cosine similarity safely."""

    if not embedding1 or not embedding2:
        raise ValueError("Embedding vectors cannot be empty.")

    if len(embedding1) != len(embedding2):
        raise ValueError(
            "Embedding vectors must have equal dimensions."
        )

    if not all(
        math.isfinite(value)
        for value in embedding1 + embedding2
    ):
        raise ValueError(
            "Embedding vectors contain invalid numbers."
        )

    dot_product = sum(
        a * b
        for a, b in zip(embedding1, embedding2)
    )

    magnitude1 = math.sqrt(
        sum(value * value for value in embedding1)
    )

    magnitude2 = math.sqrt(
        sum(value * value for value in embedding2)
    )

    if magnitude1 == 0 or magnitude2 == 0:
        raise ValueError(
            "Embedding magnitude cannot be zero."
        )

    similarity = dot_product / (
        magnitude1 * magnitude2
    )

    return max(-1.0, min(1.0, similarity))
