"""OpenAI embeddings for chunk text."""

from __future__ import annotations

from openai import OpenAI

from app.config import settings

EMBED_BATCH_SIZE = 100


def embed_texts(texts: list[str], *, batch_size: int = EMBED_BATCH_SIZE) -> list[list[float]]:
    client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
    dimensions = settings.openai_embedding_dimensions
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        response = client.embeddings.create(
            input=texts[start : start + batch_size],
            model=settings.openai_embedding_model,
            dimensions=dimensions,
        )
        # Ordered by index so each vector lines up with the text it came from.
        for item in sorted(response.data, key=lambda item: item.index):
            if len(item.embedding) != dimensions:
                raise ValueError(f"Expected {dimensions}-dimensional embeddings, got {len(item.embedding)}")
            vectors.append(item.embedding)
    return vectors
