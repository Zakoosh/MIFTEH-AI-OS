"""
MIFTEH OS — Semantic Retrieval Engine
Searches vector memory for semantically similar content.
Used by agents to inject historical context into their decisions.
Produces pre-computed retrieval results for common agent queries.
"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
INDEX_FILE = MEMORY_DIR / "vector_index.json"

TOP_K = 5
SIMILARITY_THRESHOLD = 0.70  # Minimum cosine similarity

STANDARD_QUERIES = [
    {"id": "top_seo_learnings",       "query": "best SEO strategies and topical authority patterns",         "filter_type": "seo_learning"},
    {"id": "top_monetization_wins",   "query": "most effective monetization and revenue optimization",       "filter_type": "monetization_learning"},
    {"id": "ux_conversion_patterns",  "query": "UX improvements that reduced bounce and increased sessions", "filter_type": "ux_learning"},
    {"id": "deployment_failures",     "query": "deployment rollbacks and production failures to avoid",      "filter_type": "failure"},
    {"id": "market_opportunities",    "query": "emerging market trends and competitor gaps to exploit",      "filter_type": "market_intel"},
    {"id": "successful_experiments",  "query": "experiments that showed positive results",                  "filter_type": "experiment"},
    {"id": "reasoning_insights",      "query": "key AI reasoning conclusions about strategy",               "filter_type": "reasoning_trace"},
    {"id": "growth_patterns",         "query": "backlink and content strategies that drove traffic growth",  "filter_type": "seo_learning"},
]


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def keyword_similarity(query_text, memory_text):
    """Fallback similarity when no embeddings available."""
    qwords = set(query_text.lower().split())
    mwords = set(memory_text.lower().split())
    qwords = {w.strip(".,!?;:()") for w in qwords if len(w) > 3}
    mwords = {w.strip(".,!?;:()") for w in mwords if len(w) > 3}
    if not qwords or not mwords:
        return 0.0
    intersection = len(qwords & mwords)
    union = len(qwords | mwords)
    return intersection / union if union > 0 else 0.0


def load_index():
    if not INDEX_FILE.exists():
        return {"memories": []}
    try:
        return json.loads(INDEX_FILE.read_text())
    except Exception:
        return {"memories": []}


def get_query_embedding(query_text, openai_client=None):
    if not openai_client:
        return None
    try:
        response = openai_client.embeddings.create(model="text-embedding-3-small", input=query_text[:2000])
        return response.data[0].embedding
    except Exception:
        return None


def search_memories(index, query_text, query_embedding=None, filter_type=None, top_k=TOP_K):
    """Search index by embedding cosine similarity or keyword fallback."""
    memories = index.get("memories", [])
    if filter_type:
        memories = [m for m in memories if m.get("type") == filter_type]

    scored = []
    for mem in memories:
        mem_embedding = mem.get("embedding")

        if query_embedding and mem_embedding and len(mem_embedding) == len(query_embedding):
            score = cosine_similarity(query_embedding, mem_embedding)
        else:
            score = keyword_similarity(query_text, mem.get("text", ""))

        scored.append((score, mem))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, mem in scored[:top_k]:
        if score >= (SIMILARITY_THRESHOLD if query_embedding else 0.05):
            results.append({
                "id": mem.get("id", ""),
                "type": mem.get("type", ""),
                "text": mem.get("text", ""),
                "source": mem.get("source", ""),
                "project": mem.get("project", ""),
                "metadata": mem.get("metadata", {}),
                "similarity_score": round(score, 4),
                "retrieval_method": "embedding" if (query_embedding and mem.get("embedding")) else "keyword",
                "indexed_at": mem.get("indexed_at", ""),
            })
    return results


def ai_synthesize_retrieval(query_id, query_text, results):
    """AI synthesizes retrieved memories into actionable context."""
    if not results:
        return {"synthesis": "No relevant memories found.", "confidence": 0, "key_insights": []}

    system = (
        "You synthesize retrieved memory fragments into actionable intelligence. "
        "Return valid JSON only."
    )
    snippets = "\n".join(f"- [{r['type']}] {r['text'][:200]}" for r in results[:5])
    prompt = f"""Query: {query_text}

Retrieved memory fragments:
{snippets}

Synthesize these memories into actionable intelligence. Return JSON:
{{
  "synthesis": "2-3 sentence synthesis of the retrieved knowledge",
  "confidence": 0-100,
  "key_insights": ["insight1", "insight2", "insight3"],
  "recommended_action": "single most actionable recommendation",
  "related_patterns": ["pattern1", "pattern2"]
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 400)
    if not ok:
        data = {
            "synthesis": f"Retrieved {len(results)} relevant memories for '{query_text[:50]}'.",
            "confidence": 60,
            "key_insights": [r["text"][:100] for r in results[:3]],
            "recommended_action": "Apply top-ranked pattern to current strategy",
            "related_patterns": [r["type"] for r in results[:3]],
        }
    return data, tokens, cost


def build_context_injection_payload(all_results):
    """Build a compact context payload for agent consumption."""
    payload = {}
    for qid, result in all_results.items():
        top_memories = result.get("memories", [])[:3]
        payload[qid] = {
            "summary": result.get("synthesis", {}).get("synthesis", ""),
            "insights": result.get("synthesis", {}).get("key_insights", [])[:3],
            "top_matches": [{"text": m["text"][:150], "type": m["type"], "score": m["similarity_score"]} for m in top_memories],
        }
    return payload


def main():
    print("[retrieval_engine] Starting semantic retrieval...")

    # Try to initialize OpenAI client for query embeddings
    openai_client = None
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=api_key)
        except Exception:
            pass

    index = load_index()
    total_memories = len(index.get("memories", []))
    embedded_memories = sum(1 for m in index.get("memories", []) if m.get("has_embedding"))
    print(f"[retrieval_engine] Index: {total_memories} memories, {embedded_memories} with embeddings")

    all_tokens, all_cost = 0, 0.0
    all_results = {}

    for query_def in STANDARD_QUERIES:
        qid = query_def["id"]
        qtext = query_def["query"]
        ftype = query_def.get("filter_type")

        print(f"[retrieval_engine] Querying: {qid}...")
        query_emb = get_query_embedding(qtext, openai_client)
        results = search_memories(index, qtext, query_emb, filter_type=ftype)

        synthesis_result = ai_synthesize_retrieval(qid, qtext, results)
        if isinstance(synthesis_result, tuple):
            synthesis, tokens, cost = synthesis_result
            all_tokens += tokens
            all_cost += cost
        else:
            synthesis = synthesis_result

        all_results[qid] = {
            "query": qtext,
            "filter_type": ftype,
            "memories": results,
            "memory_count": len(results),
            "synthesis": synthesis,
        }

    context_payload = build_context_injection_payload(all_results)

    report = {
        "generated_at": now_iso(),
        "index_size": total_memories,
        "embedded_memories": embedded_memories,
        "queries_run": len(STANDARD_QUERIES),
        "results": all_results,
        "context_injection_payload": context_payload,
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "retrieval_results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    total_hits = sum(r["memory_count"] for r in all_results.values())
    print(f"[retrieval_engine] Done — {total_hits} total hits across {len(STANDARD_QUERIES)} queries, ${all_cost:.4f}")


if __name__ == "__main__":
    main()
