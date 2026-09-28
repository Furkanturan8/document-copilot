import pytest

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import SearchFilters

pytestmark = pytest.mark.integration


def test_apple_net_sales_by_category_is_retrieved():
    passages = DocumentRetriever().search(
        "How did iPhone, Mac, iPad, Wearables and Services net sales change?",
        filters=SearchFilters(ticker="AAPL", fiscal_years=[2024]),
    )

    assert passages, "no passages retrieved"
    assert all(p.ticker == "AAPL" and p.fiscal_year == 2024 for p in passages)
    assert any("net sales by category" in p.text and "iPhone" in p.text for p in passages[:5])
