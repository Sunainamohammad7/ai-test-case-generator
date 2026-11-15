
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
    embedding2: list[float]
) -> float:
    """Calculate cosine similarity between two embeddings."""

    dot_product = sum(
        a * b for a, b in zip(embedding1, embedding2)
    )

    magnitude1 = math.sqrt(sum(a * a for a in embedding1))
    magnitude2 = math.sqrt(sum(b * b for b in embedding2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)
