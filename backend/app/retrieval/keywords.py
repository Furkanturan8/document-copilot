"""Turn an analyst question into a short keyword string for Postgres full-text search.

plainto_tsquery ANDs every word it is given, so passing a whole question ("How did NVIDIA
describe demand drivers ...") matches almost nothing. A small model picks 3-5 search terms
instead; names the analyst typed (iPhone, Azure) and known SEC phrases are always kept, and
a rule-based fallback covers the model being unavailable.
"""

import re

from openai import OpenAI, OpenAIError
from pydantic import BaseModel, Field

from app.config import settings
from app.retrieval.types import SearchFilters

FILLER_WORDS = frozenset(
    ["a", "an", "and", "across", "are", "as", "at", "be", "between", "by", "change", "changed", "describe", "describes", "described", "did", "do", "does", "for", "from", "how", "in", "into", "is", "its", "of", "on", "or", "over", "the", "their", "they", "this", "to", "was", "way", "what", "when", "where", "which", "who", "with", "driver", "drivers", "k", "ks"]
)
KNOWN_PHRASES = ("customer concentration", "data center", "revenue mix", "cloud capacity", "ai infrastructure")
COMPANY_NAMES = {"AAPL": "apple", "AMZN": "amazon", "GOOGL": "google", "MSFT": "microsoft", "NVDA": "nvidia"}

SYSTEM_PROMPT = """\
You extract search keywords for PostgreSQL full-text search over SEC 10-K filing chunks.

Rules:
- Return 3 to 5 terms. Joined with spaces they must total 5 words or fewer: PostgreSQL ANDs \
every word, and extra words cause zero matches.
- Prefer domain nouns and standard two-word SEC phrases (e.g. "data center", "revenue mix", \
"customer concentration"); a phrase counts as two words.
- Omit question filler and generic verbs (how, what, describe, change, drivers, across).
- Keep product-name casing from the query (iPhone, Mac, iPad, Azure).
- When a ticker filter is given, leave the company name out.
"""


class KeywordExtraction(BaseModel):
    terms: list[str] = Field(min_length=1, description="3-5 search terms")


def _is_company_word(word: str, filters: SearchFilters | None) -> bool:
    company = COMPANY_NAMES.get(filters.ticker or "") if filters else None
    return bool(company and word.casefold().startswith(company))


def _named_terms(query: str, filters: SearchFilters | None) -> list[str]:
    """Known phrases and capitalised names from the query itself, in query order."""
    lowered = query.casefold()
    phrases = [query[start : start + len(phrase)] for phrase in KNOWN_PHRASES if (start := lowered.find(phrase)) >= 0]
    names = [
        word
        for token in re.findall(r"[A-Za-z][A-Za-z0-9]*(?:'s)?", query)
        if (word := token.removesuffix("'s"))
        and len(word) > 2
        and word.casefold() not in FILLER_WORDS
        and not _is_company_word(word, filters)
        and (word[0].isupper() or re.fullmatch(r"i[A-Z]\w*", word))
    ]
    return phrases + names


def _word_budget(terms: list[str], filters: SearchFilters | None) -> list[str]:
    seen: set[str] = set()
    words: list[str] = []
    for word in (part for term in terms for part in term.split()):
        key = word.casefold()
        if key in seen or key in FILLER_WORDS or _is_company_word(word, filters):
            continue
        seen.add(key)
        words.append(word)
        if len(words) == settings.retrieval_fts_keyword_max:
            break
    return words


def _fallback(query: str, filters: SearchFilters | None) -> str:
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-/]*", query)
    words = _word_budget(_named_terms(query, filters) + tokens, filters)
    return " ".join(words) or query


def _ask_model(query: str, filters: SearchFilters | None) -> list[str]:
    context = [f"Query: {query}"]
    if filters and filters.ticker:
        context.append(f"Ticker filter: {filters.ticker} (omit the company name)")
    client = OpenAI(api_key=settings.openai_api_key.get_secret_value())
    response = client.chat.completions.parse(
        model=settings.retrieval_fts_keyword_model,
        temperature=0,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": "\n".join(context)}],
        response_format=KeywordExtraction,
    )
    parsed = response.choices[0].message.parsed
    return parsed.terms if parsed else []


def extract_fts_keywords(query: str, *, filters: SearchFilters | None = None) -> str:
    """Return a space-joined keyword string for plainto_tsquery."""
    query = query.strip()
    # Short queries are already keyword-like; plainto_tsquery drops their stop words itself.
    if len(query.split()) <= settings.retrieval_fts_keyword_fast_path_tokens:
        return query
    try:
        model_terms = _ask_model(query, filters)
    except OpenAIError:
        # Keyword search degrades to the rule-based terms; semantic search is unaffected.
        return _fallback(query, filters)

    named = _named_terms(query, filters)
    # Names the analyst typed come first; the model's terms fill the remaining word budget.
    words = _word_budget(named + model_terms, filters)
    if len(words) < settings.retrieval_fts_keyword_min:
        return _fallback(query, filters)
    return " ".join(words)
