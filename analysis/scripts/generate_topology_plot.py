#!/usr/bin/env python3
"""
VECTOR — Static 30-Node Topology PNG
Renders a publication-quality static PNG of the 30-node De Bruijn topology
with HEED cluster heads and ultimate leader highlighted (dark theme).

Output: analysis/plots/network_topology.png
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim_engine import Simulator, SimConfig

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NUM_NODES = 30
SEED = 42
AREA = 1000.0
WIRELESS_RANGE = 200.0
Y_OFFSET = 150.0

PLOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plots")
OUTPUT_FILE = os.path.join(PLOT_DIR, "network_topology.png")

# Dark theme colors (consistent with generate_network_animations.py)
BG_COLOR = "#0d1117"
NODE_COLOR = "#58a6ff"        # blue - MEMBER
CH_COLOR = "#f0c808"          # amber - cluster head
ULTIMATE_LEADER_COLOR = "#ff7b72"   # red - ultimate leader
EDGE_COLOR = "#30363d"        # subtle topology edges
TEXT_COLOR = "#c9d1d9"        # off-white text


def main():
    os.makedirs(PLOT_DIR, exist_ok=True)

    cfg = SimConfig(
        num_nodes=NUM_NODES, seed=SEED,
        area_width=AREA, area_height=AREA,
        wireless_range=WIRELESS_RANGE,
    )
    sim = Simulator(cfg, seed=SEED)
    sim.setup_network()

    nodes = sim.nodes
    adj = sim.adj
    positions = np.array([[n.x, n.y + Y_OFFSET] for n in nodes])

    # Cluster heads via HEED
    heed_clustering = __import__("sim_engine", fromlist=["heed_clustering"]).heed_clustering
    chs, assign = heed_clustering(nodes, adj, cfg, sim.rng)
    ch_set = set(chs)
    if len(ch_set) < 3:
        for i in range(NUM_NODES):
            if i not in ch_set:
                ch_set.add(i)
                if len(ch_set) >= 3:
                    break

    # Ultimate Leader: cluster head with highest residual energy
    leader_idx = max(ch_set, key=lambda i: nodes[i].energy) if ch_set else 0

    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(-50, AREA + 100)
    ax.set_ylim(-50 + Y_OFFSET, AREA + 100 + Y_OFFSET)
    ax.set_aspect("equal")
    ax.axis("off")

    title = ax.text(
        0.5, 0.97,
        "VECTOR — 30-Node De Bruijn Topology (Dark Theme)",
        transform=ax.transAxes, ha="center", va="top",
        color=TEXT_COLOR, fontsize=15, fontweight="bold",
    )

    subtitle = ax.text(
        0.5, 0.925,
        f"HEED clustering | Ultimate Leader: Node {leader_idx} | {len(ch_set)} cluster heads",
        transform=ax.transAxes, ha="center", va="top",
        color=TEXT_COLOR, fontsize=10,
    )

    # Draw topology edges
    for i in range(NUM_NODES):
        for j in adj[i]:
            if j > i:
                x1, y1 = positions[i]
                x2, y2 = positions[j]
                ax.plot(
                    [x1, x2], [y1, y2],
                    color=EDGE_COLOR, linewidth=1.0, alpha=0.45, zorder=1,
                )

    # Draw member nodes (non-CH, non-leader)
    member_idx = [i for i in range(NUM_NODES) if i not in ch_set and i != leader_idx]
    if member_idx:
        mpos = positions[member_idx]
        ax.scatter(
            mpos[:, 0], mpos[:, 1],
            s=110, c=NODE_COLOR, edgecolors="white", linewidths=1.2,
            zorder=3, alpha=0.9,
        )

    # Draw cluster heads
    if ch_set:
        ch_idx = [i for i in sorted(ch_set) if i != leader_idx]
        if ch_idx:
            chpos = positions[ch_idx]
            ax.scatter(
                chpos[:, 0], chpos[:, 1],
                s=300, c=CH_COLOR, marker="*", edgecolors="white", linewidths=1.5,
                zorder=4, label="Cluster Head",
            )

    # Draw ultimate leader
    lpos = positions[leader_idx]
    ax.scatter(
        [lpos[0]], [lpos[1]],
        s=450, c=ULTIMATE_LEADER_COLOR, marker="D", edgecolors="white", linewidths=2,
        zorder=6, label="Ultimate Leader",
    )

    # Role labels
    for i in range(NUM_NODES):
        x, y = positions[i]
        if i == leader_idx:
            label = f"UL {i}"
            color = ULTIMATE_LEADER_COLOR
            fontsize = 10
            fontweight = "bold"
        elif i in ch_set:
            label = f"CH {i}"
            color = CH_COLOR
            fontsize = 9
            fontweight = "bold"
        else:
            label = str(i)
            color = NODE_COLOR
            fontsize = 8
            fontweight = "normal"
        ax.text(
            x, y + 16, label, ha="center", va="bottom",
            color=color, fontsize=fontsize, fontweight=fontweight, zorder=5,
        )

    # Legend
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label='Member',
               markerfacecolor=NODE_COLOR, markeredgecolor='white', markersize=10),
        Line2D([0], [0], marker='*', color='w', label='Cluster Head',
               markerfacecolor=CH_COLOR, markeredgecolor='white', markersize=14),
        Line2D([0], [0], marker='D', color='w', label='Ultimate Leader',
               markerfacecolor=ULTIMATE_LEADER_COLOR, markeredgecolor='white', markersize=12),
    ]
    ax.legend(
        handles=legend_elements, loc="lower left", frameon=True,
        facecolor="#1f2328", edgecolor=TEXT_COLOR, labelcolor=TEXT_COLOR,
        fontsize=9,
    )

    # Footer
    ax.text(
        0.99, 0.01, "VECTOR — De Bruijn structured routing + HEED clustering",
        transform=ax.transAxes, ha="right", va="bottom",
        color=TEXT_COLOR, fontsize=8, alpha=0.6,
    )

    plt.tight_layout()
    fig.savefig(OUTPUT_FILE, dpi=300, facecolor=BG_COLOR)
    plt.close(fig)
    print(f"Saved {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
