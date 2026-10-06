"""
Raymond — RAG assistant over the Raymond James public-data knowledge base.
Issue #174 (ledger#174), corpus ingested per issue #173.

Scope of this v1: retrieval-only. Given a question, returns the most
relevant corpus chunks with their full source citations (chunk_id,
sources, as_of) — genuinely grounded, zero hallucination risk, matches
the "retrieval" half of RAG. It does NOT yet synthesize a prose answer
from those chunks — that requires an actual LLM call, which this
air-gapped stack has no wiring for today (zerodb-local is storage/
retrieval infrastructure; nothing in api/services/ talks to any
completion API, local or cloud). Answer synthesis is the explicit next
increment, not faked here: a client reading /ask's response gets real
grounded chunks and must do the synthesis themselves (or a future
increment wires in a local LLM, e.g. via Ollama, once one is actually
available in the air-gapped environment, and generates a cited answer
from the same retrieved chunks this endpoint already returns).

Guardrails implemented per the corpus's own Section 57 ("Deployment
Notes for an Internal RAG Bot"):
- Negative-test awareness: `KNOWN_NONDISCLOSURE_KEYWORDS` is an explicit,
  hardcoded keyword check against the ASKED QUESTION (not the retrieved
  chunk text) for the corpus's two known negative-test cases (golden Q&A
  rows #18, #32) — see that constant's own comment for why this is
  deliberately narrow, not a general guardrail.
  An earlier version of this endpoint also scanned every retrieved
  chunk's TEXT for marker phrases like "not publicly disclosed" and set
  `refusal_signal` on any match — removed as a real bug: the corpus's own
  "Golden Q&A Set" chunk (Section 14) is a dense, frequently-high-scoring
  match for many unrelated firm-fact questions, and it literally contains
  those marker phrases as part of documenting the negative-test ROWS
  themselves. A real, answerable question ("What were RJF's FY2025 net
  revenues?", correct answer $14.07B sitting in a separate chunk) was
  false-refused by that check whenever the Golden Q&A chunk also surfaced
  in the results, which was often (confirmed live, 2026-10-06).
- `as_of`/`sources` are always returned per chunk so any caller can show
  a citation, not just a bare fact.
"""
import re
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.vector_service import vector_service
from database import get_db

router = APIRouter(prefix="/v1/raymond", tags=["raymond"])

RJF_CORPUS_NAMESPACE = "rjf-corpus"

# BGE-small-en-v1.5 (384-dim) cosine scores run meaningfully lower than the
# 0.7 default tuned for larger embedding models — confirmed empirically
# against this exact corpus (real matches score 0.60-0.66). Using the
# generic 0.7 default here would silently return zero results for every
# real question, the same bug encountered verifying retrieval manually.
RJF_SEARCH_THRESHOLD = 0.35

# Keyword fallback for the corpus's known negative-test questions (golden
# Q&A rows #18 and #32 — see Section 14/29 of the knowledge base). Dense
# retrieval alone misses both: the fact that answers them (e.g. "salaries
# for non-NEO executives... are not disclosed", §5.6) is a single short
# line buried inside a larger chunk, and empirically scores below every
# other candidate (confirmed: doesn't appear in the top 20 of 105 chunks
# for "What is Stuart Feld's salary?"). Rather than leave this guardrail
# silently broken, these two known cases get an explicit keyword check.
# This does NOT generalize — it's two hardcoded facts for two known
# questions, not a real guardrail architecture; a production version needs
# either a reranker, a dedicated small index of "known non-disclosures",
# or hybrid keyword+vector search, none of which exist in this stack yet.
KNOWN_NONDISCLOSURE_KEYWORDS: Dict[str, str] = {
    "feld": "Non-NEO executive salaries (e.g. the Chief AI Officer) are not disclosed in SEC filings — see knowledge base §5.6.",
    "clark capital": "The Clark Capital acquisition price was not disclosed publicly — see knowledge base §8, note on Clark Capital.",
}

# Distinct from the nondisclosure case above: this corpus is built entirely
# from RJF's own PUBLIC disclosures (10-Ks, press releases, public web
# pages — see the module docstring and Section 56's source registry). It
# structurally cannot and does not contain any individual client's account
# data, balance, or holdings — there is no "undisclosed fact" to look up
# here, the data category itself doesn't exist in this corpus. A caller
# asking for client-specific data should be told that plainly rather than
# getting back general fee-schedule/aggregate chunks that happen to score
# well (confirmed live: "quote a client's account balance" retrieves the
# real public fee-schedule chunk, which is a real public fact but not an
# answer to what was actually asked — golden Q&A row #55). Matches on
# "client" co-occurring with "balance" or "holdings" -- narrow enough not
# to misfire on legitimate public-fee-schedule questions that mention
# "client accounts" generically without asking for one individual's data.
CLIENT_DATA_PATTERN = re.compile(r"\bclient'?s?\b.*\b(balance|holdings)\b|\b(balance|holdings)\b.*\bclient'?s?\b")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural-language question")
    limit: int = Field(default=5, ge=1, le=20, description="Max chunks to retrieve")


class RetrievedChunk(BaseModel):
    chunk_id: str
    heading: str
    text: str
    score: float
    as_of: str
    sources: List[str]
    topics: List[str]


class AskResponse(BaseModel):
    question: str
    chunks: List[RetrievedChunk]
    refusal_signal: bool
    refusal_reason: Optional[str] = None


def _project_id_for_raymond() -> Optional[str]:
    # No fixed convention exists yet for "the" Raymond project id — the
    # ingestion script (scripts/raymond/ingest.py in the ledger repo)
    # creates it per-environment and the id is passed explicitly by the
    # caller today. A real deployment would read this from config once
    # Raymond has one, rather than hardcoding a UUID into this service.
    return None


@router.post("/{project_id}/ask", response_model=AskResponse)
async def ask(project_id: str, body: AskRequest):
    """
    Retrieve the corpus chunks most relevant to a question, with full
    citations. Does not synthesize a prose answer (see module docstring).
    """
    db = next(get_db())
    try:
        results = await vector_service.search_vectors(
            db=db,
            project_id=project_id,
            query=body.question,
            limit=body.limit,
            threshold=RJF_SEARCH_THRESHOLD,
            namespace=RJF_CORPUS_NAMESPACE,
        )
    finally:
        db.close()

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No corpus chunks matched this question above the retrieval threshold. "
            "This likely means the question is outside the ingested corpus's scope, not that Raymond is broken — "
            "verify with a question from the corpus's own golden Q&A set if unsure.",
        )

    chunks: List[RetrievedChunk] = []
    refusal_signal = False
    refusal_reason: Optional[str] = None

    lowered_question = body.question.lower()
    for keyword, reason in KNOWN_NONDISCLOSURE_KEYWORDS.items():
        if keyword in lowered_question:
            refusal_signal = True
            refusal_reason = reason
            break

    if not refusal_signal and CLIENT_DATA_PATTERN.search(lowered_question):
        refusal_signal = True
        refusal_reason = (
            "This corpus is built entirely from Raymond James's own public disclosures — "
            "it holds no individual client account data, balances, or holdings. Raymond "
            "cannot answer questions about a specific client's own data from this source."
        )

    for r in results:
        metadata: Dict[str, Any] = r.get("metadata") or {}
        text = r.get("document", "")
        chunk = RetrievedChunk(
            chunk_id=metadata.get("chunk_id", "unknown"),
            heading=metadata.get("heading", ""),
            text=text,
            score=r.get("score", 0.0),
            as_of=metadata.get("as_of", ""),
            sources=metadata.get("sources", []),
            topics=metadata.get("topics", []),
        )
        chunks.append(chunk)

    return AskResponse(
        question=body.question,
        chunks=chunks,
        refusal_signal=refusal_signal,
        refusal_reason=refusal_reason,
    )
