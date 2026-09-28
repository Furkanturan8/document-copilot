import uuid

import pytest

from app.retrieval.fusion import reciprocal_rank_fusion

A, B, C, D = (uuid.uuid4() for _ in range(4))


def test_chunk_found_by_both_searches_beats_single_top_hit():
    # A is first for semantic only; B is second in both lists.
    fused = reciprocal_rank_fusion([[A, B, C], [D, B]], k=60)
    assert fused[0][0] == B
    assert fused[0][1] == pytest.approx(2 / 62)


def test_scores_use_rank_not_list_length():
    fused = dict(reciprocal_rank_fusion([[A], [B, C, D]], k=60))
    assert fused[A] == pytest.approx(1 / 61)
    assert fused[A] == fused[B]
    assert fused[D] == pytest.approx(1 / 63)


def test_empty_rankings_fuse_to_nothing():
    assert reciprocal_rank_fusion([[], []]) == []
