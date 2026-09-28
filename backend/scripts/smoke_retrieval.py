"""Run the client-brief questions through hybrid retrieval and print what comes back.

A manual check that retrieval surfaces the right filings, pages and sections. Each query
costs one embedding and at most one small keyword-model call.

    cd backend && uv run python -m scripts.smoke_retrieval
"""

import time

from app.retrieval.retriever import DocumentRetriever
from app.retrieval.types import SearchFilters

QUESTIONS = [
    ("How did the revenue mix between iPhone, Services, Mac, iPad, and Wearables change?", SearchFilters(ticker="AAPL")),
    ("Compare AWS operating income and margin against North America and International.", SearchFilters(ticker="AMZN")),
    ("How did NVIDIA describe demand drivers, customer concentration, and supply constraints for Data Center?", SearchFilters(ticker="NVDA")),
    ("How does Microsoft describe Azure, AI infrastructure, and cloud capacity constraints?", SearchFilters(ticker="MSFT")),
    ("How did Google Search, YouTube ads, Google Network, and Google Cloud revenue trends differ?", SearchFilters(ticker="GOOGL")),
    ("Risk factors about export controls and AI regulation", None),
    ("Dependence on third-party manufacturing and supplier concentration", SearchFilters(ticker="AAPL")),
    ("Capital expenditures and purchase commitments for AI infrastructure", SearchFilters(ticker="MSFT")),
    ("Revenue by geographic area in the latest filing", SearchFilters(ticker="NVDA", fiscal_years=[2025])),
    ("Did generative AI improve gross margins?", None),
]


def main() -> None:
    retriever = DocumentRetriever()
    for question, filters in QUESTIONS:
        started = time.perf_counter()
        passages = retriever.search(question, filters=filters)
        print(f"\n### {question}  [{filters.model_dump(exclude_none=True) if filters else 'no filter'}]")
        print(f"{len(passages)} passages in {time.perf_counter() - started:.1f}s")
        for passage in passages[:5]:
            first_line = passage.text.splitlines()[0][:90]
            kind = "table" if passage.text.count("|") > 4 else "text "
            print(
                f"  {passage.fusion_score:.4f} {passage.ticker} FY{passage.fiscal_year} p.{passage.page} "
                f"{(passage.section or '-')[:28]:28} {kind} | {first_line}"
            )


if __name__ == "__main__":
    main()
