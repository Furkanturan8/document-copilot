"""Reciprocal Rank Fusion: merge ranked lists using ranks only, never raw scores.

Cosine similarity and ts_rank_cd live on different scales, so their scores cannot be
compared; ranks can. Each appearance at rank r adds 1 / (k + r), so a chunk ranked well
by both searches beats one ranked first by only one of them.
"""

import uuid
from collections import defaultdict


def reciprocal_rank_fusion(rankings: list[list[uuid.UUID]], *, k: int = 60) -> list[tuple[uuid.UUID, float]]:
    scores: dict[uuid.UUID, float] = defaultdict(float)
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)
