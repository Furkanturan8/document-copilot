"""Embed a live query with the same model and width as the ingested chunks."""

from openai import OpenAI

from app.config import settings


def embed_query(text: str) -> list[float]:
    client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
    response = client.embeddings.create(
        input=[text],
        model=settings.openai_embedding_model,
        dimensions=settings.openai_embedding_dimensions,
    )
    embedding = response.data[0].embedding
    if len(embedding) != settings.openai_embedding_dimensions:
        raise ValueError(
            f"Expected {settings.openai_embedding_dimensions}-dimensional embeddings, got {len(embedding)}"
        )
    return embedding
