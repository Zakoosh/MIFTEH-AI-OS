"""
MIFTEH OS — Knowledge Graph
Builds a relationship graph of projects, features, trends, competitors,
keywords, and events. Surfaces hidden connections and cross-project insights.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

PROJECTS = ["yallaplays", "fionera", "mifteh"]

NODE_TYPES = ["project", "feature", "keyword", "competitor", "trend", "event", "pattern"]
EDGE_TYPES = ["targets", "competes_with", "implements", "shares_pattern",
              "ranks_for", "influenced_by", "transfers_to"]


def load_source(path: str) -> dict:
    f = Path(path)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def extract_nodes_from_sources(all_data: dict) -> list:
    nodes = []
    seen = set()

    def add(node_id: str, node_type: str, label: str, project: str = "", **attrs):
        if node_id in seen:
            return
        seen.add(node_id)
        nodes.append({
            "id": node_id,
            "type": node_type,
            "label": label,
            "project": project,
            **attrs,
        })

    # Project nodes
    for proj in PROJECTS:
        add(f"project:{proj}", "project", proj.title(), project=proj)

    # Competitor nodes
    comp_data = all_data.get("competitor", {})
    for proj, proj_data in comp_data.get("projects", {}).items():
        for profile in proj_data.get("profiles", []):
            name = profile.get("name", "")
            if name:
                add(f"competitor:{name}", "competitor", name, project=proj)

    # SEO keyword nodes
    seo_data = all_data.get("seo", {})
    for proj, clusters_data in seo_data.get("projects", {}).items():
        for cluster in clusters_data.get("topical_clusters", [])[:5]:
            kw = cluster.get("hub_keyword", "")
            if kw:
                kw_id = f"keyword:{kw[:40].replace(' ', '_')}"
                add(kw_id, "keyword", kw, project=proj,
                    est_monthly_searches=cluster.get("est_monthly_searches", 0),
                    difficulty=cluster.get("difficulty", "medium"))
        for lt in clusters_data.get("long_tail_opportunities", [])[:3]:
            kw = lt.get("keyword", "")
            if kw:
                kw_id = f"keyword:{kw[:40].replace(' ', '_')}"
                add(kw_id, "keyword", kw, project=proj,
                    est_monthly_searches=lt.get("est_monthly_searches", 0),
                    difficulty=lt.get("difficulty", "easy"))

    # Trend nodes from social signals
    social_data = all_data.get("social", {})
    for proj, proj_signals in social_data.get("projects", {}).items():
        sa = proj_signals.get("sentiment_analysis", {})
        for vt in sa.get("viral_topics", [])[:3]:
            topic = vt.get("topic", "")
            if topic:
                trend_id = f"trend:{topic[:40].replace(' ', '_')}"
                add(trend_id, "trend", topic, project=proj,
                    momentum=vt.get("momentum", "stable"))
        for et in sa.get("emerging_trends", [])[:2]:
            if et:
                trend_id = f"trend:{et[:40].replace(' ', '_')}"
                add(trend_id, "trend", et, project=proj, momentum="rising")

    # Event nodes from realtime alerts
    alerts_data = all_data.get("alerts", {})
    for event in alerts_data.get("events", [])[:5]:
        title = event.get("title", "")
        if title:
            event_id = f"event:{title[:40].replace(' ', '_')}"
            add(event_id, "event", title[:60],
                event_types=event.get("event_types", []),
                impact_score=event.get("impact_score", 0))

    # Cross-project pattern nodes
    cross_data = all_data.get("cross", {})
    for pattern in cross_data.get("transferable_patterns", [])[:5]:
        pname = pattern.get("pattern_name", pattern.get("name", ""))
        if pname:
            pat_id = f"pattern:{pname[:40].replace(' ', '_')}"
            add(pat_id, "pattern", pname,
                category=pattern.get("category", ""),
                success_rate=pattern.get("success_rate_pct", 0))

    return nodes


def extract_edges(nodes: list, all_data: dict) -> list:
    edges = []
    node_ids = {n["id"] for n in nodes}

    def add_edge(src: str, tgt: str, edge_type: str, weight: float = 1.0, **attrs):
        if src in node_ids and tgt in node_ids:
            edges.append({
                "source": src,
                "target": tgt,
                "type": edge_type,
                "weight": weight,
                **attrs,
            })

    # Project → Competitor (competes_with)
    comp_data = all_data.get("competitor", {})
    for proj, proj_data in comp_data.get("projects", {}).items():
        for profile in proj_data.get("profiles", []):
            name = profile.get("name", "")
            add_edge(f"project:{proj}", f"competitor:{name}", "competes_with", weight=1.0)

    # Project → Keyword (ranks_for / targets)
    seo_data = all_data.get("seo", {})
    for proj, clusters_data in seo_data.get("projects", {}).items():
        diff_weight = {"easy": 1.0, "medium": 0.7, "hard": 0.4, "expert": 0.2}
        for cluster in clusters_data.get("topical_clusters", [])[:5]:
            kw = cluster.get("hub_keyword", "")
            if kw:
                kw_id = f"keyword:{kw[:40].replace(' ', '_')}"
                w = diff_weight.get(cluster.get("difficulty", "medium"), 0.5)
                add_edge(f"project:{proj}", kw_id, "targets", weight=w)

    # Project → Trend (influenced_by)
    social_data = all_data.get("social", {})
    for proj, proj_signals in social_data.get("projects", {}).items():
        sa = proj_signals.get("sentiment_analysis", {})
        for vt in sa.get("viral_topics", [])[:3]:
            topic = vt.get("topic", "")
            if topic:
                trend_id = f"trend:{topic[:40].replace(' ', '_')}"
                add_edge(f"project:{proj}", trend_id, "influenced_by",
                         weight=1.0 if vt.get("relevance") == "high" else 0.5)

    # Pattern → Project (transfers_to)
    cross_data = all_data.get("cross", {})
    for pattern in cross_data.get("transferable_patterns", [])[:5]:
        pname = pattern.get("pattern_name", pattern.get("name", ""))
        pat_id = f"pattern:{pname[:40].replace(' ', '_')}" if pname else ""
        if not pat_id:
            continue
        for proj in pattern.get("target_projects", PROJECTS):
            add_edge(pat_id, f"project:{proj}", "transfers_to",
                     weight=pattern.get("success_rate_pct", 50) / 100)

    # Trend → Event (related)
    alerts_data = all_data.get("alerts", {})
    for event in alerts_data.get("events", [])[:5]:
        title = event.get("title", "")
        event_id = f"event:{title[:40].replace(' ', '_')}" if title else ""
        if not event_id:
            continue
        for event_type in event.get("event_types", []):
            # Link events to relevant project
            for proj, rel_types in {
                "yallaplays": ["gaming_event", "viral_launch"],
                "fionera": ["market_event", "tech_trend"],
                "mifteh": ["tech_trend", "viral_launch"],
            }.items():
                if event_type in rel_types:
                    add_edge(f"project:{proj}", event_id, "influenced_by", weight=0.8)

    return edges


def compute_graph_metrics(nodes: list, edges: list) -> dict:
    # Degree centrality
    degree: dict = {n["id"]: 0 for n in nodes}
    for e in edges:
        degree[e["source"]] = degree.get(e["source"], 0) + 1
        degree[e["target"]] = degree.get(e["target"], 0) + 1

    # Most connected nodes
    top_nodes = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:10]

    # Edge type distribution
    edge_types: dict = {}
    for e in edges:
        et = e["type"]
        edge_types[et] = edge_types.get(et, 0) + 1

    return {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "node_type_counts": {nt: sum(1 for n in nodes if n["type"] == nt) for nt in NODE_TYPES},
        "edge_type_counts": edge_types,
        "top_connected_nodes": [{"id": nid, "degree": deg} for nid, deg in top_nodes],
        "density": round(len(edges) / max(len(nodes) * (len(nodes) - 1), 1), 4),
    }


def ai_graph_insights(nodes: list, edges: list, metrics: dict) -> dict:
    system = (
        "You are a knowledge graph analyst. Extract strategic insights from "
        "product-competitor-keyword relationship graphs."
    )
    top_nodes_detail = [n for n in nodes if n["id"] in
                        {x["id"] for x in metrics["top_connected_nodes"][:5]}]
    prompt = f"""Knowledge graph summary:
Nodes: {metrics['total_nodes']} ({metrics['node_type_counts']})
Edges: {metrics['total_edges']} ({metrics['edge_type_counts']})
Most connected: {json.dumps(top_nodes_detail[:5], indent=2)}
Sample edges: {json.dumps(edges[:10], indent=2)}

Extract strategic insights. Respond with JSON:
{{
  "hidden_connections": [
    {{"connection": "description", "nodes_involved": ["id1", "id2"], "strategic_value": "why this matters"}}
  ],
  "cross_project_opportunities": [
    {{"opportunity": "description", "from_project": "project", "to_project": "project", "mechanism": "how"}}
  ],
  "knowledge_gaps": ["gap 1 — what we don't know but should", "gap 2"],
  "strategic_clusters": [
    {{"cluster_name": "name", "nodes": ["id1", "id2"], "theme": "theme"}}
  ],
  "graph_insight": "single most valuable insight from this graph"
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=900)
    if ok and data:
        return data
    return {
        "hidden_connections": [],
        "cross_project_opportunities": [],
        "knowledge_gaps": [],
        "strategic_clusters": [],
        "graph_insight": "Graph built — run again with more data for AI insights.",
    }


def main():
    print("[knowledge-graph] Building knowledge graph...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # Load all intelligence sources
    all_data = {
        "competitor": load_source("memory/competitor_memory.json"),
        "seo":        load_source("memory/seo_opportunities.json"),
        "social":     load_source("memory/social_signals.json"),
        "alerts":     load_source("memory/realtime_alerts.json"),
        "cross":      load_source("memory/cross_project_summary.json"),
        "web":        load_source("memory/web_intelligence.json"),
        "traffic":    load_source("memory/traffic_intelligence.json"),
    }
    print(f"  [knowledge-graph] Loaded {sum(1 for v in all_data.values() if v)} intelligence sources")

    nodes = extract_nodes_from_sources(all_data)
    print(f"  [knowledge-graph] {len(nodes)} nodes extracted")

    edges = extract_edges(nodes, all_data)
    print(f"  [knowledge-graph] {len(edges)} edges built")

    metrics = compute_graph_metrics(nodes, edges)

    print("  [knowledge-graph] Running AI insight analysis...")
    insights = ai_graph_insights(nodes, edges, metrics)

    report = {
        "generated_at": now_iso(),
        "metrics": metrics,
        "nodes": nodes,
        "edges": edges,
        "insights": insights,
    }

    out = MEMORY_DIR / "knowledge_graph.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[knowledge-graph] {metrics['total_nodes']} nodes, {metrics['total_edges']} edges")
    print(f"[knowledge-graph] Density: {metrics['density']}")
    print(f"[knowledge-graph] Report → {out}")
    return report


if __name__ == "__main__":
    main()
