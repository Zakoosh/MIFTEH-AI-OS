"""
MIFTEH OS — Vector Memory System
Embeds knowledge into vector space using OpenAI text-embedding-3-small.
Stores prompts, deployments, failures, SEO/monetization/UX learnings,
market intelligence, experiments, AI reasoning traces.
Enables semantic search and long-term knowledge retention.
"""
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import now_iso

MEMORY_DIR = Path("memory")
VECTORS_DIR = MEMORY_DIR / "vectors"
INDEX_FILE = MEMORY_DIR / "vector_index.json"
STATS_FILE = MEMORY_DIR / "vector_stats.json"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
MAX_MEMORIES_PER_TYPE = 50

MEMORY_TYPES = [
    "seo_learning", "monetization_learning", "ux_learning",
    "market_intel", "deployment", "experiment", "reasoning_trace",
    "failure", "pattern", "prompt",
]

# Max chars to embed per memory (keep costs low)
MAX_EMBED_CHARS = 800


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def keyword_vector(text, vocab=None):
    """Fallback: simple keyword frequency vector for when embeddings unavailable."""
    words = text.lower().split()
    freq = {}
    for w in words:
        w = w.strip(".,!?;:()")
        if len(w) > 3:
            freq[w] = freq.get(w, 0) + 1
    return freq


def get_embedding(text, openai_client=None):
    """Get embedding vector from OpenAI, fallback to None."""
    if not openai_client:
        return None
    try:
        text = text[:MAX_EMBED_CHARS * 4]  # Limit tokens
        response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return response.data[0].embedding
    except Exception:
        return None


def load_index():
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text())
        except Exception:
            pass
    return {"memories": [], "version": 1, "last_updated": now_iso()}


def save_index(index):
    INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False))


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def extract_memories_from_sources():
    """Pull learnable facts from all memory sources."""
    memories = []

    # SEO learnings
    seo = _rj("seo_opportunities.json")
    for pid, pdata in seo.get("projects", {}).items():
        for cluster in (pdata.get("topical_clusters") or [])[:3]:
            memories.append({
                "type": "seo_learning",
                "text": f"SEO cluster for {pid}: {json.dumps(cluster, ensure_ascii=False)[:MAX_EMBED_CHARS]}",
                "source": "seo_opportunities",
                "project": pid,
                "metadata": {"cluster_type": "topical"},
            })
    growth = _rj("growth_report.json")
    for pid, pdata in growth.get("projects", {}).items():
        strat = pdata.get("ai_strategy", {})
        if strat.get("executive_summary"):
            memories.append({
                "type": "seo_learning",
                "text": f"Growth strategy {pid}: {strat['executive_summary']} | {strat.get('primary_growth_lever', '')}",
                "source": "growth_report",
                "project": pid,
                "metadata": {"growth_score": pdata.get("growth_score", 0)},
            })

    # Monetization learnings
    mon = _rj("monetization_runtime_report.json")
    for pid, pdata in mon.get("projects", {}).items():
        plan = pdata.get("ai_plan", {})
        if plan.get("revenue_gap_strategy"):
            memories.append({
                "type": "monetization_learning",
                "text": f"Monetization {pid} ({pdata.get('model','')}): {plan.get('revenue_gap_strategy','')} | Top action: {plan.get('top_revenue_action','')}",
                "source": "monetization_runtime_report",
                "project": pid,
                "metadata": {"current_rev": pdata.get("current_revenue_est_usd", 0), "target": pdata.get("monthly_target_usd", 0)},
            })

    # UX learnings
    conversion = _rj("conversion_report.json")
    for pid, pdata in conversion.get("projects", {}).items():
        recs = pdata.get("ai_recommendations", {})
        if recs.get("top_priority_fix"):
            memories.append({
                "type": "ux_learning",
                "text": f"CRO for {pid}: {recs.get('top_priority_fix','')} | {recs.get('summary','')}",
                "source": "conversion_report",
                "project": pid,
                "metadata": {"cro_score": recs.get("cro_score", 0)},
            })

    # Market intelligence
    market = _rj("market_intelligence.json")
    for pid, topics in market.get("trending_topics", {}).items():
        if topics:
            memories.append({
                "type": "market_intel",
                "text": f"Market trends {pid}: {json.dumps(topics, ensure_ascii=False)[:MAX_EMBED_CHARS]}",
                "source": "market_intelligence",
                "project": pid,
                "metadata": {},
            })

    # Deployment learnings
    deploy = _rj("deployment_pipeline_report.json")
    for pid, pdata in deploy.get("projects", {}).items():
        if pdata.get("health_score", 0) > 0:
            memories.append({
                "type": "deployment",
                "text": f"Deployment {pid}: health {pdata['health_score']}/100 | triggers: {pdata.get('rollback_triggers',[])}",
                "source": "deployment_pipeline_report",
                "project": pid,
                "metadata": {"health_score": pdata.get("health_score", 0)},
            })

    # Experiments
    experiments = _rj("experiment_summary.json")
    for exp in (experiments.get("experiments") or [])[:5]:
        memories.append({
            "type": "experiment",
            "text": f"Experiment: {exp.get('name','')} | result: {exp.get('result','')} | insight: {exp.get('insight','')}",
            "source": "experiment_summary",
            "project": exp.get("project", ""),
            "metadata": {"status": exp.get("status", "")},
        })

    # AI reasoning traces
    reasoning_dir = MEMORY_DIR / "reasoning_chains"
    if reasoning_dir.exists():
        for f in list(reasoning_dir.glob("*.json"))[:5]:
            try:
                chain = json.loads(f.read_text())
                conclusion = chain.get("conclusion") or chain.get("summary") or ""
                if conclusion:
                    memories.append({
                        "type": "reasoning_trace",
                        "text": f"Reasoning: {conclusion[:MAX_EMBED_CHARS]}",
                        "source": f"reasoning_chains/{f.name}",
                        "project": chain.get("project", ""),
                        "metadata": {"chain_id": chain.get("id", "")},
                    })
            except Exception:
                pass

    # Failure patterns
    trust = _rj("trust_scores.json")
    for repo, data in trust.get("repos", {}).items():
        if data.get("rollback_count", 0) > 0:
            memories.append({
                "type": "failure",
                "text": f"Rollback pattern: {repo} had {data['rollback_count']} rollbacks | score {data.get('score', 0)}",
                "source": "trust_scores",
                "project": repo.split("/")[0] if "/" in repo else repo,
                "metadata": {"rollback_count": data.get("rollback_count", 0)},
            })

    return memories


def cluster_memories(index):
    """Group memories by type for summary stats."""
    by_type = {}
    for mem in index["memories"]:
        t = mem.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return by_type


def main():
    print("[vector_memory] Starting vector memory indexing...")
    VECTORS_DIR.mkdir(exist_ok=True)

    # Try to initialize OpenAI client for embeddings
    openai_client = None
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=api_key)
        except Exception:
            pass

    index = load_index()
    existing_texts = {m["text"] for m in index["memories"]}

    new_memories = extract_memories_from_sources()
    embedded_count = 0
    skipped_count = 0
    total_embedding_tokens = 0

    for mem in new_memories:
        text = mem["text"]
        if text in existing_texts:
            skipped_count += 1
            continue

        # Generate embedding
        embedding = get_embedding(text, openai_client)
        if embedding:
            embedded_count += 1
            total_embedding_tokens += len(text.split())  # Rough token estimate

        memory_record = {
            "id": f"{mem['type']}_{len(index['memories'])}_{now_iso()[:10]}",
            "type": mem["type"],
            "text": text,
            "source": mem["source"],
            "project": mem.get("project", ""),
            "metadata": mem.get("metadata", {}),
            "embedding": embedding,
            "has_embedding": embedding is not None,
            "indexed_at": now_iso(),
        }
        index["memories"].append(memory_record)
        existing_texts.add(text)

    # Prune to max per type
    by_type = {}
    for mem in index["memories"]:
        by_type.setdefault(mem["type"], []).append(mem)

    pruned_memories = []
    for mem_type, mems in by_type.items():
        mems.sort(key=lambda m: m.get("indexed_at", ""), reverse=True)
        pruned_memories.extend(mems[:MAX_MEMORIES_PER_TYPE])

    index["memories"] = pruned_memories
    index["last_updated"] = now_iso()
    index["total_memories"] = len(pruned_memories)
    index["embedded_count"] = sum(1 for m in pruned_memories if m.get("has_embedding"))

    save_index(index)

    # Save stats (without embeddings to keep it lean)
    stats = {
        "generated_at": now_iso(),
        "total_memories": len(pruned_memories),
        "new_memories_added": embedded_count + (len(new_memories) - skipped_count - embedded_count),
        "embedded_memories": index["embedded_count"],
        "skipped_duplicates": skipped_count,
        "by_type": cluster_memories(index),
        "embedding_model": EMBEDDING_MODEL if openai_client else "none (fallback mode)",
        "embeddings_enabled": openai_client is not None,
        "approx_tokens_used": total_embedding_tokens,
    }
    STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False))

    print(f"[vector_memory] Done — {stats['total_memories']} memories, {stats['embedded_memories']} embedded, {skipped_count} skipped")


if __name__ == "__main__":
    main()
