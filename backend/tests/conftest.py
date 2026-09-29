import pytest

from app.config import settings


@pytest.fixture(autouse=True)
def _no_live_semantic_judge(monkeypatch):
    # The Jev risk signal calls a paid API when a key is configured; tests stay offline.
    monkeypatch.setattr(settings, "typesafe_api_key", None)
