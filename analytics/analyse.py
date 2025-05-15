import json, networkx as nx, matplotlib.pyplot as plt
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd, json, pathlib
events = [json.loads(l) for l in pathlib.Path("logs/events.jsonl").read_text().splitlines()]
df = pd.DataFrame(events)
searches = df[df.type == "internalSearch"][["t", "query"]]
print(searches.tail(10))


LOG = Path(__file__).parent / "logs" / "events.jsonl"
if not LOG.exists():
    raise SystemExit("No events yet – browse first!")

G = nx.DiGraph()
last = None
for line in LOG.read_text().splitlines():
    ev = json.loads(line)
    if ev["type"] != "dwell":
        continue
    node = urlparse(ev["url"]).netloc
    G.nodes[node]["ms"] = G.nodes[node].get("ms", 0) + ev["ms"]
    if last and last != node:
        G.edges[last, node]["w"] = G.edges[last, node].get("w", 0) + 1
    last = node

pos = nx.spring_layout(G, k=1/len(G))
nx.draw(G, pos, with_labels=True,
        node_size=[G.nodes[n]["ms"]/20 for n in G],
        width=[G[u][v]["w"] for u,v in G.edges])
plt.show()