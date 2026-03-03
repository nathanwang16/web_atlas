"""
analyse.py — Web Atlas Event Analysis

Analyzes browser events from JSONL log to visualize browsing patterns.
Generates domain-level navigation graph with dwell time weighting.

Usage: python analyse.py
"""

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd

# ---------- Setup ----------
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("analyse")

LOG_FILE = Path(__file__).parent / "logs" / "events.jsonl"


def load_events() -> pd.DataFrame:
    """Load events from JSONL into DataFrame."""
    if not LOG_FILE.exists():
        raise SystemExit(f"No events file: {LOG_FILE}")
    
    events = [json.loads(line) for line in LOG_FILE.read_text().splitlines() if line.strip()]
    log.info(f"Loaded {len(events)} events")
    return pd.DataFrame(events)


def show_recent_searches(df: pd.DataFrame, n: int = 10):
    """Display recent search queries."""
    searches = df[df["type"].isin(["searchRequest", "omniboxSearch", "omniboxInput"])]
    if searches.empty:
        log.info("No search events found")
        return
    
    cols = ["timestamp", "type", "query"]
    available = [c for c in cols if c in searches.columns]
    print("\n=== Recent Searches ===")
    print(searches[available].tail(n).to_string(index=False))


def show_event_summary(df: pd.DataFrame):
    """Display event type distribution."""
    print("\n=== Event Type Summary ===")
    print(df["type"].value_counts().to_string())


def build_navigation_graph(df: pd.DataFrame) -> nx.DiGraph:
    """Build domain navigation graph from dwell events."""
    G = nx.DiGraph()
    dwell_events = df[df["type"] == "dwell"]
    
    last_domain = None
    for _, ev in dwell_events.iterrows():
        url = ev.get("url", "")
        domain = urlparse(url).netloc
        if not domain:
            continue
        
        # Accumulate dwell time per domain
        if domain not in G.nodes:
            G.add_node(domain, ms=0)
        G.nodes[domain]["ms"] += ev.get("ms", 0)
        
        # Track transitions
        if last_domain and last_domain != domain:
            if not G.has_edge(last_domain, domain):
                G.add_edge(last_domain, domain, w=0)
            G.edges[last_domain, domain]["w"] += 1
        
        last_domain = domain
    
    log.info(f"Graph: {G.number_of_nodes()} domains, {G.number_of_edges()} transitions")
    return G


def visualize_graph(G: nx.DiGraph):
    """Visualize navigation graph."""
    if G.number_of_nodes() == 0:
        log.warning("Empty graph, nothing to visualize")
        return
    
    plt.figure(figsize=(14, 10))
    pos = nx.spring_layout(G, k=2/max(1, len(G)**0.5), iterations=50)
    
    # Scale node sizes by dwell time (capped)
    node_sizes = [min(G.nodes[n].get("ms", 1000) / 50, 3000) for n in G]
    edge_widths = [G[u][v].get("w", 1) for u, v in G.edges]
    
    nx.draw(
        G, pos,
        with_labels=True,
        node_size=node_sizes,
        width=edge_widths,
        font_size=8,
        node_color="lightblue",
        edge_color="gray",
        arrows=True,
        arrowsize=10
    )
    plt.title("Web Atlas: Domain Navigation Graph")
    plt.tight_layout()
    plt.show()


def main():
    df = load_events()
    show_event_summary(df)
    show_recent_searches(df)
    
    G = build_navigation_graph(df)
    visualize_graph(G)


if __name__ == "__main__":
    main()
