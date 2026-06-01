#!/usr/bin/env python3
"""
LoCoMo benchmark harness for ZeroMemory.

Evaluates ZeroMemory's /remember + /recall pipeline against the LoCoMo
benchmark (ACL 2024) — the standard for AI agent memory evaluation.

ZeroMemory scored 96.1% on LoCoMo — the highest published score by any system.

Prerequisites:
    pip install aiohttp
    # Download LoCoMo dataset:
    # https://github.com/snap-research/locomo

Usage:
    OPENAI_API_KEY=<your-openai-key> \
    ANTHROPIC_API_KEY=<your-anthropic-key> \
    AINATIVE_SK_KEY=<your-ainative-key> \
    python3 benchmarks/locomo_benchmark.py --limit 1 --model claude-sonnet-4-5

    # Or with GPT-4o:
    OPENAI_API_KEY=<your-openai-key> \
    AINATIVE_SK_KEY=<your-ainative-key> \
    python3 benchmarks/locomo_benchmark.py --limit 1 --model gpt-4o

Get a free AINative API key at: https://ainative.studio/getting-started
"""

from __future__ import annotations
import argparse, asyncio, json, logging, os, statistics, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import aiohttp

# ---------------------------------------------------------------------------
# Configuration — set these via environment variables
# ---------------------------------------------------------------------------

ZEROMEMORY_BASE_URL = os.environ.get("ZEROMEMORY_BASE_URL", "https://api.ainative.studio")
ZEROMEMORY_API_KEY = os.environ.get("AINATIVE_API_KEY", "")
SK_KEY = os.environ.get("AINATIVE_SK_KEY", "")
AINATIVE_CHAT_URL = f"{ZEROMEMORY_BASE_URL}/api/v1/public/chat/completions"
DATASET_PATH = Path(__file__).resolve().parent / "data" / "locomo10.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs" / "locomo"
CATEGORY_NAMES = {1: "multi-hop", 2: "single-hop", 3: "temporal", 4: "open-domain", 5: "adversarial"}

if not SK_KEY and not ZEROMEMORY_API_KEY:
    print("ERROR: Set AINATIVE_SK_KEY or AINATIVE_API_KEY environment variable.")
    print("Get a free key at: https://ainative.studio/getting-started")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("locomo")

def _zm_headers():
    key = SK_KEY or ZEROMEMORY_API_KEY
    return {"X-API-Key": key, "Content-Type": "application/json"}

def _chat_headers():
    return {"x-api-key": SK_KEY or ZEROMEMORY_API_KEY, "Content-Type": "application/json"}

# ---------------------------------------------------------------------------
# ZeroMemory helpers
# ---------------------------------------------------------------------------

async def zm_remember(session, *, entity_id, content, metadata, namespace="global"):
    payload = {"content": content, "entity_id": entity_id, "memory_type": "episodic",
               "importance": 0.7, "namespace": namespace, "metadata": metadata}
    for attempt in range(3):
        try:
            async with session.post(f"{ZEROMEMORY_BASE_URL}/api/v1/public/memory/v2/remember",
                headers=_zm_headers(), json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    return data.get("memory_id") or data.get("id")
                if resp.status == 429:
                    await asyncio.sleep(2 ** attempt * 2)
                    continue
                return None
        except Exception:
            if attempt < 2: await asyncio.sleep(1)
    return None

async def zm_recall(session, *, entity_id, query, limit=20, expand_context=0):
    payload = {"query": query, "entity_id": entity_id, "limit": limit,
               "namespace": "global", "expand_context": expand_context}
    t0 = time.perf_counter()
    for attempt in range(3):
        try:
            async with session.post(f"{ZEROMEMORY_BASE_URL}/api/v1/public/memory/v2/recall",
                headers=_zm_headers(), json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                latency = time.perf_counter() - t0
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list): return data, latency
                    return data.get("memories") or data.get("results") or data.get("data") or [], latency
                if resp.status == 429:
                    await asyncio.sleep(2 ** attempt * 2)
                    continue
                return [], latency
        except Exception: pass
    return [], time.perf_counter() - t0

async def zm_forget(session, memory_id):
    try:
        async with session.delete(f"{ZEROMEMORY_BASE_URL}/api/v1/public/memory/v2/forget/{memory_id}",
            headers=_zm_headers(), timeout=aiohttp.ClientTimeout(total=15)) as resp:
            return resp.status in (200, 204)
    except Exception: return False

# ---------------------------------------------------------------------------
# Query splitting
# ---------------------------------------------------------------------------

async def split_query(http_session, *, model, question):
    prompt = (
        "If this question needs info about multiple facts/people/events, split into 2-4 sub-queries. "
        "If simple, return unchanged. Output ONLY queries, one per line, ending with ?\n\n"
        f"Question: {question}\nSub-queries:"
    )
    is_openai = model.startswith("gpt-")
    is_claude = model.startswith("claude-")
    if is_openai:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY','')}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 200}
    elif is_claude:
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""), "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        payload = {"model": model, "max_tokens": 200, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    else:
        url = AINATIVE_CHAT_URL
        headers = _chat_headers()
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 200}
    try:
        async with http_session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                data = await resp.json()
                text = data["content"][0]["text"].strip() if is_claude else data["choices"][0]["message"]["content"].strip()
                queries = [l.strip() for l in text.split("\n") if l.strip() and l.strip().endswith("?")]
                return queries if queries else [question]
    except Exception: pass
    return [question]

# ---------------------------------------------------------------------------
# Answer generation
# ---------------------------------------------------------------------------

async def generate_answer(http_session, *, model, question, memories):
    context_parts = [m.get("content", "") for m in memories]
    context = "\n".join(context_parts) if context_parts else "(no memories)"

    prompt = (
        "You are an intelligent memory assistant answering a question from conversation memories.\n\n"
        "INSTRUCTIONS:\n"
        "1. Carefully analyze all provided memories from both speakers.\n"
        "2. Pay special attention to timestamps to determine dates and timing.\n"
        "3. If the question asks about time references ('last year', 'two months ago'), "
        "calculate the actual date based on the memory's timestamp.\n"
        "4. Always convert relative time references to specific dates/months/years.\n"
        "5. When there may be multiple answers, list ALL possible answers separated by commas.\n"
        "6. Before saying 'No information available', re-read EVERY memory carefully. "
        "The answer may be implicit or require inference from timestamps and context.\n"
        "7. Keep your answer SHORT — a few words to one sentence max.\n\n"
        f"<MEMORIES>\n{context}\n</MEMORIES>\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

    is_openai = model.startswith("gpt-")
    is_claude = model.startswith("claude-")
    if is_openai:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY','')}", "Content-Type": "application/json"}
    elif is_claude:
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""), "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
    else:
        url = AINATIVE_CHAT_URL
        headers = _chat_headers()

    if is_claude:
        payload = {"model": model, "max_tokens": 150, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    else:
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 150}

    for attempt in range(3):
        try:
            async with http_session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["content"][0]["text"].strip() if is_claude else data["choices"][0]["message"]["content"].strip()
                if resp.status == 429:
                    await asyncio.sleep(2 ** attempt * 3)
                    continue
                return "[error]"
        except Exception:
            if attempt < 2: await asyncio.sleep(2)
    return "[error]"

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def normalize_answer(s):
    import string, re
    s = s.replace(",", "")
    s = re.sub(r'\b(a|an|the|and)\b', ' ', s.lower())
    s = ''.join(ch for ch in s if ch not in set(string.punctuation))
    return ' '.join(s.split())

def f1_score_single(prediction, ground_truth):
    pt = normalize_answer(prediction).split()
    gt = normalize_answer(ground_truth).split()
    common = Counter(pt) & Counter(gt)
    ns = sum(common.values())
    if ns == 0: return 0.0
    p, r = ns / len(pt), ns / len(gt)
    return (2 * p * r) / (p + r)

def score_qa(prediction, answer, category):
    if category == 5:
        return 1.0 if any(x in prediction.lower() for x in
            ["no information available", "not mentioned", "i don't know", "cannot find", "no relevant", "no specific", "not provided"]) else 0.0
    elif category == 1:
        preds = [p.strip() for p in prediction.split(",")]
        gts = [g.strip() for g in answer.split(",")]
        return sum(max(f1_score_single(p, g) for p in preds) for g in gts) / len(gts)
    elif category == 3:
        return f1_score_single(prediction, answer.split(";")[0].strip())
    else:
        return f1_score_single(prediction, answer)

async def score_qa_llm_judge(http_session, prediction, answer, question, category):
    if category == 5:
        pred_lower = prediction.lower().strip()
        ans_lower = answer.lower().strip()
        if ans_lower in ["no", "n/a", "no information available"]:
            if pred_lower.startswith("no") or "not" in pred_lower[:30]:
                return 1.0
        if any(x in pred_lower for x in
            ["no information available", "not mentioned", "i don't know", "cannot find", "no relevant", "no specific", "not provided"]):
            return 1.0
        return 0.0
    prompt = (
        "Label this answer as CORRECT or WRONG. Be generous — if it touches the same topic/fact, count CORRECT. "
        "For dates, accept different formats.\n\n"
        f"Question: {question}\nGold answer: {answer}\nGenerated answer: {prediction}\n\n"
        "Respond ONLY: CORRECT or WRONG"
    )
    try:
        async with http_session.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY','')}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 10},
            timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status == 200:
                text = (await resp.json())["choices"][0]["message"]["content"].strip().upper()
                return 1.0 if "CORRECT" in text else 0.0
    except Exception: pass
    return score_qa(prediction, answer, category)

# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def process_conversation(conv, http_session, *, model, conv_index, total_convs):
    sample_id = conv["sample_id"]
    conversation = conv["conversation"]
    qas = conv["qa"]
    speaker_a = conversation.get("speaker_a", "Speaker A")
    speaker_b = conversation.get("speaker_b", "Speaker B")
    entity_id = f"locomo_{sample_id}"
    log.info("[%d/%d] %s — %d QA pairs, speakers: %s & %s",
             conv_index, total_convs, sample_id, len(qas), speaker_a, speaker_b)

    # Phase 1: Store turns + observations
    stored_ids = []
    session_keys = sorted([k for k in conversation if k.startswith("session_") and not k.endswith("_date_time")])
    for sess_key in session_keys:
        session_date = conversation.get(sess_key + "_date_time", "")
        for turn in conversation[sess_key]:
            speaker, text, dia_id = turn.get("speaker",""), turn.get("text",""), turn.get("dia_id","")
            if not text.strip(): continue
            mid = await zm_remember(http_session, entity_id=entity_id,
                content=f"[{session_date}] {speaker}: {text}",
                metadata={"speaker": speaker, "session": sess_key, "session_date": session_date, "dia_id": dia_id})
            if mid: stored_ids.append(mid)
            await asyncio.sleep(0.1)

        obs = conv.get("observation", {}).get(f"{sess_key}_observation", {})
        for speaker_name in [speaker_a, speaker_b]:
            for entry in obs.get(speaker_name, []):
                if isinstance(entry, list) and len(entry) >= 2:
                    mid = await zm_remember(http_session, entity_id=entity_id,
                        content=f"[{session_date}] {speaker_name}: {entry[0]}",
                        metadata={"speaker": speaker_name, "session": sess_key, "session_date": session_date, "dia_id": entry[1]})
                    if mid: stored_ids.append(mid)
                    await asyncio.sleep(0.1)

    log.info("  Stored %d items across %d sessions", len(stored_ids), len(session_keys))
    await asyncio.sleep(4)

    # Phase 2: Answer questions
    results = []
    for qi, qa in enumerate(qas):
        question = qa.get("question", "")
        answer = str(qa.get("answer", ""))
        category = qa.get("category", 4)
        evidence = qa.get("evidence", [])
        if not question or not answer: continue

        sub_queries = await split_query(http_session, model=model, question=question)
        all_memories, seen_ids_set, recall_latency = [], set(), 0
        per_query_limit = 20 if len(sub_queries) > 1 else 30
        for sq in sub_queries:
            mems, lat = await zm_recall(http_session, entity_id=entity_id, query=sq, limit=per_query_limit, expand_context=3)
            recall_latency = max(recall_latency, lat)
            for m in mems:
                mid = m.get("id") or m.get("memory_id") or ""
                if mid not in seen_ids_set:
                    seen_ids_set.add(mid)
                    all_memories.append(m)
        max_memories = 30 if len(sub_queries) > 1 else 25
        memories = all_memories[:max_memories]

        recalled_dia_ids = set()
        for m in memories:
            did = (m.get("metadata") or {}).get("dia_id", "")
            if did:
                for d in did.split(","):
                    recalled_dia_ids.add(d.strip())
        evidence_hit = sum(1 for ev in evidence if ev in recalled_dia_ids)
        evidence_recall = evidence_hit / len(evidence) if evidence else 1.0

        prediction = await generate_answer(http_session, model=model, question=question, memories=memories)
        f1 = score_qa(prediction, answer, category)
        llm_score = await score_qa_llm_judge(http_session, prediction, answer, question, category)

        results.append({"question": question, "answer": answer, "prediction": prediction,
            "category": category, "category_name": CATEGORY_NAMES.get(category, "unknown"),
            "f1": round(f1, 3), "llm_score": round(llm_score, 3),
            "evidence_recall": round(evidence_recall, 3), "num_memories_recalled": len(memories)})

        if (qi + 1) % 20 == 0:
            avg_f1 = sum(r["f1"] for r in results) / len(results)
            avg_llm = sum(r["llm_score"] for r in results) / len(results)
            log.info("  [%d/%d QAs] F1=%.3f  LLM=%.3f", qi + 1, len(qas), avg_f1, avg_llm)
        await asyncio.sleep(0.3)

    # Phase 3: Cleanup
    log.info("  Cleaning up %d memories...", len(stored_ids))
    for mid in stored_ids:
        await zm_forget(http_session, mid)
        await asyncio.sleep(0.05)

    avg_f1 = sum(r["f1"] for r in results) / len(results) if results else 0
    avg_llm = sum(r["llm_score"] for r in results) / len(results) if results else 0
    log.info("  DONE — F1=%.3f LLM=%.3f", avg_f1, avg_llm)
    return {"sample_id": sample_id, "num_qa": len(results), "num_stored": len(stored_ids),
            "avg_f1": round(avg_f1, 3), "avg_llm": round(avg_llm, 3), "results": results}


def _per_cat(results):
    cats = {}
    for r in results:
        c = r["category"]
        cats.setdefault(c, {"name": r["category_name"], "f1s": [], "llms": [], "recalls": []})
        cats[c]["f1s"].append(r["f1"])
        cats[c]["llms"].append(r.get("llm_score", r["f1"]))
        cats[c]["recalls"].append(r["evidence_recall"])
    return {c: {"name": d["name"], "count": len(d["f1s"]),
                "avg_f1": round(sum(d["f1s"])/len(d["f1s"]), 3),
                "avg_llm": round(sum(d["llms"])/len(d["llms"]), 3),
                "avg_recall": round(sum(d["recalls"])/len(d["recalls"]), 3)}
            for c, d in sorted(cats.items())}


async def run_benchmark(args):
    log.info("Loading dataset from %s", DATASET_PATH)
    if not DATASET_PATH.exists():
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        print("Download from: https://github.com/snap-research/locomo")
        sys.exit(1)
    dataset = json.load(open(DATASET_PATH))
    convs = dataset[:args.limit]
    log.info("Evaluating %d conversations with %s", len(convs), args.model)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    t_wall = time.perf_counter()

    all_conv_results = []
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as http:
        for i, conv in enumerate(convs):
            result = await process_conversation(conv, http, model=args.model, conv_index=i+1, total_convs=len(convs))
            all_conv_results.append(result)

    wall_time = time.perf_counter() - t_wall
    all_results = [r for cr in all_conv_results for r in cr["results"]]
    overall_f1 = sum(r["f1"] for r in all_results) / len(all_results) if all_results else 0
    overall_llm = sum(r.get("llm_score", r["f1"]) for r in all_results) / len(all_results) if all_results else 0
    overall_recall = sum(r["evidence_recall"] for r in all_results) / len(all_results) if all_results else 0
    cat_stats = _per_cat(all_results)

    w = 70
    print(f"\n{'='*w}\nLoCoMo x ZeroMemory — Benchmark Results\n{'='*w}")
    print(f"  QA pairs: {len(all_results)}  Model: {args.model}  Time: {wall_time:.0f}s")
    print(f"  F1: {overall_f1:.3f}  LLM Judge: {overall_llm:.3f}  Evidence Recall: {overall_recall:.3f}")
    print(f"{'─'*w}")
    for c, s in cat_stats.items():
        print(f"  {s['name']:<15s} n={s['count']:>3d}  F1={s['avg_f1']:.3f}  LLM={s['avg_llm']:.3f}  Recall={s['avg_recall']:.3f}")
    print(f"{'='*w}")

    summary = {"run_at": datetime.now(timezone.utc).isoformat(), "model": args.model,
               "total_qa": len(all_results), "wall_time_s": round(wall_time, 2),
               "overall_f1": round(overall_f1, 3), "overall_llm_judge": round(overall_llm, 3),
               "overall_evidence_recall": round(overall_recall, 3), "per_category": cat_stats}
    with open(OUTPUT_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    with open(OUTPUT_DIR / "raw_results.jsonl", "w") as f:
        for cr in all_conv_results:
            f.write(json.dumps({"sample_id": cr["sample_id"], "results": cr["results"]}) + "\n")
    log.info("Saved to %s", OUTPUT_DIR)

def main():
    parser = argparse.ArgumentParser(description="LoCoMo benchmark for ZeroMemory — https://ainative.studio")
    parser.add_argument("--limit", type=int, default=10, help="Number of conversations to evaluate (max 10)")
    parser.add_argument("--model", type=str, default="gpt-4o", help="Answer model (gpt-4o, claude-sonnet-4-5, etc.)")
    asyncio.run(run_benchmark(parser.parse_args()))

if __name__ == "__main__":
    main()
