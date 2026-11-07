#!/usr/bin/env python3
"""
VECTOR — Search Route Discovery Animation
Renders a single MP4 video showing SEARCH-based route discovery over the
De Bruijn network following the members → CH → UL hierarchy:

    Source Member → Source CH → CH-to-CH → Dest CH → Dest Member

All intermediate hops between source and dest are Cluster Heads (CHs).
The discovered path is drawn as bold orange arrows with a moving data packet.

Output: analysis/videos/search_discovery.mp4
"""
import os
import sys
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import FancyArrowPatch
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim_engine import Simulator, SimConfig, heed_clustering

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NUM_NODES = 30
SEED = 42
FPS = 15
TOTAL_FRAMES = 180
AREA = 1000.0
WIRELESS_RANGE = 200.0
Y_OFFSET = 150.0

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "videos")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "search_discovery.mp4")

# Dark theme colors
BG_COLOR = "#0d1117"
NODE_COLOR = "#58a6ff"        # blue - MEMBER
CH_COLOR = "#f0c808"          # amber - cluster head
ULTIMATE_LEADER_COLOR = "#ff7b72"   # red - ultimate leader
EDGE_COLOR = "#30363d"        # subtle topology edges
SEARCH_COLOR = "#79c0ff"      # light blue - search packet
SEARCH_VISITED = "#8b949e"    # gray - visited by search
ROUTE_COLOR = "#d29922"       # orange - discovered route path (bold)
TEXT_COLOR = "#c9d1d9"        # off-white text
SOURCE_COLOR = "#ff7b72"      # red - source member
DEST_COLOR = "#d29922"        # orange - destination member

# Phase frame ranges (inclusive end)
PHASE_ESTABLISHED = (0, 30)
PHASE_SEARCH_INIT = (31, 55)
PHASE_SEARCH_FANOUT = (56, 105)
PHASE_ROUTE_FOUND = (106, 130)
PHASE_DATA_FLOW = (131, 180)


def bfs_layers(adj, src, dst, alive):
    """BFS returning layers and parent map for full graph."""
    layers = []
    parent = {src: -1}
    visited = {src}
    current = [src]
    found = (src == dst)
    while current and not found:
        layers.append(list(current))
        nxt = []
        for u in current:
            for v in adj[u]:
                if alive[v] and v not in visited:
                    visited.add(v)
                    parent[v] = u
                    nxt.append(v)
                    if v == dst:
                        found = True
        current = nxt
    path = None
    if dst in parent:
        path = []
        at = dst
        while at != -1:
            path.append(at)
            at = parent[at]
        path.reverse()
    return layers, path


def bfs_ch_only(adj, src_ch, dst_ch, alive, ch_set):
    """BFS restricted to CH nodes only. Path: src_ch -> ... -> dst_ch."""
    if src_ch == dst_ch:
        return [src_ch]
    parent = {src_ch: -1}
    visited = {src_ch}
    current = [src_ch]
    while current:
        nxt = []
        for u in current:
            for v in adj[u]:
                if v not in visited and v in ch_set and alive[v]:
                    visited.add(v)
                    parent[v] = u
                    if v == dst_ch:
                        path = []
                        at = v
                        while at != -1:
                            path.append(at)
                            at = parent[at]
                        path.reverse()
                        return path
                    nxt.append(v)
        current = nxt
    return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

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
    alive_flags = sim.alive_flags()

    # Cluster heads via HEED - ensure at least 4 CHs for visible topology
    chs, assign = heed_clustering(nodes, adj, cfg, sim.rng)
    ch_set = set(chs)
    if len(ch_set) < 4:
        alive = [i for i in range(NUM_NODES) if nodes[i].alive]
        alive_sorted = sorted(alive, key=lambda i: nodes[i].energy, reverse=True)
        for i in alive_sorted:
            if i not in ch_set:
                ch_set.add(i)
            if len(ch_set) >= 4:
                break

    # Source and destination: plain MEMBER nodes (not UL or CH)
    leader_idx = max(ch_set, key=lambda i: nodes[i].energy) if ch_set else 0
    member_idxs = [i for i in range(NUM_NODES) if i not in ch_set and i != leader_idx]
    if len(member_idxs) < 2:
        member_idxs = [i for i in range(NUM_NODES) if i != leader_idx]
    source_idx = member_idxs[0]
    dists_from_source = np.linalg.norm(positions - positions[source_idx], axis=1)
    dest_idx = max(member_idxs, key=lambda i: dists_from_source[i])

    # Map source/dest to their nearest CHs
    source_ch = assign.get(source_idx, -1)
    dest_ch = assign.get(dest_idx, -1)
    if source_ch == -1 or source_ch not in ch_set:
        source_ch = min(ch_set, key=lambda c: np.linalg.norm(positions[source_idx] - positions[c]))
    if dest_ch == -1 or dest_ch not in ch_set:
        dest_ch = min(ch_set, key=lambda c: np.linalg.norm(positions[dest_idx] - positions[c]))

    # CH-to-CH path (only cluster heads as intermediate nodes)
    ch_path = bfs_ch_only(adj, source_ch, dest_ch, alive_flags, ch_set)

    # Build full end-to-end route: Source Member -> Source CH -> CH-to-CH -> Dest CH -> Dest Member
    if ch_path:
        route = [source_idx] + ch_path + [dest_idx]
    elif source_ch == dest_ch:
        route = [source_idx, source_ch, dest_idx]
    else:
        route = [source_idx, source_ch, dest_ch, dest_idx]

    # CH fanout layers for SEARCH visualization
    ch_layers, _ = bfs_layers(adj, source_ch, dest_ch, alive_flags)
    ch_layers_filtered = []
    for layer in ch_layers:
        ch_layer = [v for v in layer if v in ch_set]
        if ch_layer:
            ch_layers_filtered.append(ch_layer)

    fanout_start = PHASE_SEARCH_FANOUT[0]
    fanout_end = PHASE_SEARCH_FANOUT[1]
    fanout_duration = float(fanout_end - fanout_start)
    num_layers = len(ch_layers_filtered)

    # -------------------------------------------------------------------
    # Figure setup
    # -------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(-50, AREA + 220)
    ax.set_ylim(-50 + Y_OFFSET, AREA + 220 + Y_OFFSET)
    ax.set_aspect("equal")
    ax.axis("off")

    title = ax.text(
        0.5, 0.985,
        "VECTOR — SEARCH Route Discovery (De Bruijn)",
        transform=ax.transAxes, ha="center", va="top",
        color=TEXT_COLOR, fontsize=14, fontweight="bold",
    )

    phase_text = ax.text(
        0.5, 0.935, "", transform=ax.transAxes,
        ha="center", va="top", color=TEXT_COLOR, fontsize=11,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#2a2a4a", alpha=0.95, edgecolor=TEXT_COLOR),
    )

    stats_text = ax.text(
        0.98, 0.86, "", transform=ax.transAxes,
        ha="right", va="top", color=TEXT_COLOR, fontsize=10,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#2a2a4a", alpha=0.95, edgecolor=TEXT_COLOR),
    )

    # Draw existing De Bruijn topology edges
    for i in range(NUM_NODES):
        for j in adj[i]:
            if j > i:
                x1, y1 = positions[i]
                x2, y2 = positions[j]
                ax.plot(
                    [x1, x2], [y1, y2],
                    color=EDGE_COLOR, linewidth=1.0, alpha=0.35, zorder=1,
                )

    # Draw existing nodes
    node_scatter = ax.scatter(
        positions[:, 0], positions[:, 1],
        s=120, c=NODE_COLOR, edgecolors="white", linewidths=1.5,
        zorder=3, alpha=0.9,
    )

    # Highlight cluster heads as amber stars
    if ch_set:
        ch_pos = positions[sorted(ch_set)]
    else:
        ch_pos = np.empty((0, 2))
    ch_scatter = ax.scatter(
        ch_pos[:, 0], ch_pos[:, 1],
        s=300, c=CH_COLOR, marker="*", edgecolors="white", linewidths=1.5,
        zorder=4, label="Cluster Head",
    )

    # Ultimate Leader
    leader_idx = max(ch_set, key=lambda i: nodes[i].energy) if ch_set else 0
    leader_pos = positions[leader_idx]
    leader_scatter = ax.scatter(
        [leader_pos[0]], [leader_pos[1]],
        s=400, c=ULTIMATE_LEADER_COLOR, marker="D", edgecolors="white", linewidths=2,
        zorder=6, label="Ultimate Leader",
    )

    # Role labels
    node_labels = []
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
        txt = ax.text(
            x, y + 18, label, ha="center", va="bottom",
            color=color, fontsize=fontsize, fontweight=fontweight,
            zorder=5,
        )
        node_labels.append(txt)

    # Source and destination markers
    source_scatter = ax.scatter(
        [positions[source_idx][0]], [positions[source_idx][1]],
        s=220, c=SOURCE_COLOR, edgecolors="white", linewidths=2.5,
        zorder=7, marker="o",
    )
    dest_scatter = ax.scatter(
        [positions[dest_idx][0]], [positions[dest_idx][1]],
        s=220, c=DEST_COLOR, edgecolors="white", linewidths=2.5,
        zorder=7, marker="o",
    )
    source_label = ax.text(
        positions[source_idx][0], positions[source_idx][1] + 18, "SOURCE",
        ha="center", va="bottom", color=SOURCE_COLOR, fontsize=9,
        fontweight="bold", zorder=8,
    )
    dest_label = ax.text(
        positions[dest_idx][0], positions[dest_idx][1] + 18, "DEST",
        ha="center", va="bottom", color=DEST_COLOR, fontsize=9,
        fontweight="bold", zorder=8,
    )

    # Search packet marker (moves during fanout)
    search_scatter = ax.scatter(
        [], [], s=100, c=SEARCH_COLOR, edgecolors="white", linewidths=1.5,
        zorder=6, marker="o", alpha=0.0,
    )

    # Data packet marker moving along route (large, bold)
    data_scatter = ax.scatter(
        [], [], s=200, c=ROUTE_COLOR, edgecolors="white", linewidths=3,
        zorder=9, marker="o", alpha=0.0,
    )

    # Route edge lines (bold orange arrows)
    route_edge_lines = []

    def get_phase(frame):
        if frame <= PHASE_ESTABLISHED[1]:
            return "established"
        if frame <= PHASE_SEARCH_INIT[1]:
            return "search_init"
        if frame <= PHASE_SEARCH_FANOUT[1]:
            return "search_fanout"
        if frame <= PHASE_ROUTE_FOUND[1]:
            return "route_found"
        return "data_flow"

    def update(frame):
        phase = get_phase(frame)
        state = {"visited": set()}

        phase_labels = {
            "established": "Phase 1: Established De Bruijn network (30 nodes)",
            "search_init": "Phase 2: Source initiates SEARCH for route to DEST",
            "search_fanout": "Phase 3: SEARCH packets fan out (CH-to-CH waves)",
            "route_found": "Phase 4: Route discovered — path highlighted",
            "data_flow": "Phase 5: Data flows along CH-routed path",
        }
        phase_text.set_text(phase_labels[phase])

        # Stats text
        if phase == "data_flow":
            stats_text.set_text(
                f"Nodes: {NUM_NODES}\nStatus: ROUTE ACTIVE\nRoute: CHs only\n"
                f"CH hops: {len(ch_path) - 1 if ch_path else 0}"
            )
        else:
            stats_text.set_text(
                f"Nodes: {NUM_NODES}\nStatus: ESTABLISHED\nTopology: De Bruijn\nCHs: {len(ch_set)}"
            )

        # ---- Node coloring ----
        node_colors = [NODE_COLOR] * NUM_NODES
        node_sizes = [120] * NUM_NODES
        node_colors[source_idx] = SOURCE_COLOR
        node_sizes[source_idx] = 220
        node_colors[dest_idx] = DEST_COLOR
        node_sizes[dest_idx] = 220

        # CHs on route get amber + size bump
        if phase in ("route_found", "data_flow") and ch_path:
            for v in ch_path:
                node_colors[v] = CH_COLOR
                node_sizes[v] = 300

        # SEARCH visited CHs get dimmed during fanout
        if phase == "search_fanout":
            for v in state["visited"]:
                if v not in (source_idx, dest_idx):
                    if v not in ch_set:
                        node_colors[v] = SEARCH_VISITED
                        node_sizes[v] = 140

        node_scatter.set_color(node_colors)
        node_scatter.set_sizes(node_sizes)

        # ---- Phase-specific animation ----
        if phase == "established":
            search_scatter.set_offsets(np.empty((0, 2)))
            search_scatter.set_alpha(0.0)
            data_scatter.set_offsets(np.empty((0, 2)))
            data_scatter.set_alpha(0.0)
            for line in route_edge_lines:
                line.remove()
            route_edge_lines.clear()

        elif phase == "search_init":
            search_scatter.set_offsets([[positions[source_idx][0], positions[source_idx][1]]])
            search_scatter.set_color(SEARCH_COLOR)
            search_scatter.set_alpha(0.9)
            data_scatter.set_alpha(0.0)
            data_scatter.set_offsets(np.empty((0, 2)))
            for line in route_edge_lines:
                line.remove()
            route_edge_lines.clear()

        elif phase == "search_fanout":
            # Advance visited CH layer by layer
            t = (frame - fanout_start) / fanout_duration
            active_layer = min(int(t * num_layers), num_layers - 1)
            state["visited"] = set()
            for li in range(active_layer + 1):
                state["visited"].update(ch_layers_filtered[li])

            # Position search packet at frontier of current CH layer
            frontier = ch_layers_filtered[active_layer] if active_layer < num_layers else []
            if frontier:
                pulse_idx = int((frame * 3) % len(frontier))
                sp = positions[frontier[pulse_idx]]
                search_scatter.set_offsets([[sp[0], sp[1]]])
                pulse = 0.4 + 0.6 * abs(math.sin(frame * 0.8))
                search_scatter.set_alpha(pulse)
            else:
                search_scatter.set_alpha(0.0)

            data_scatter.set_alpha(0.0)
            data_scatter.set_offsets(np.empty((0, 2)))
            for line in route_edge_lines:
                line.remove()
            route_edge_lines.clear()

        elif phase == "route_found":
            search_scatter.set_alpha(0.0)
            data_scatter.set_alpha(0.0)
            data_scatter.set_offsets(np.empty((0, 2)))
            # Draw bold orange arrows for full route: Member → CH → CH → Member
            full_route = [source_idx] + ch_path + [dest_idx] if ch_path else None
            if full_route and len(full_route) >= 2:
                for line in route_edge_lines:
                    line.remove()
                route_edge_lines.clear()
                for k in range(len(full_route) - 1):
                    a = positions[full_route[k]]
                    b = positions[full_route[k + 1]]
                    arr = FancyArrowPatch(
                        (a[0], a[1]), (b[0], b[1]),
                        arrowstyle="->", mutation_scale=28, color=ROUTE_COLOR,
                        linewidth=6.0, alpha=0.95, zorder=3,
                    )
                    ax.add_patch(arr)
                    route_edge_lines.append(arr)

        else:  # data_flow
            search_scatter.set_alpha(0.0)
            search_scatter.set_offsets(np.empty((0, 2)))
            # Redraw bold orange arrows every frame so they persist
            full_route = [source_idx] + ch_path + [dest_idx] if ch_path else None
            if full_route and len(full_route) >= 2:
                for line in route_edge_lines:
                    line.remove()
                route_edge_lines.clear()
                for k in range(len(full_route) - 1):
                    a = positions[full_route[k]]
                    b = positions[full_route[k + 1]]
                    arr = FancyArrowPatch(
                        (a[0], a[1]), (b[0], b[1]),
                        arrowstyle="->", mutation_scale=28, color=ROUTE_COLOR,
                        linewidth=6.0, alpha=0.95, zorder=3,
                    )
                    ax.add_patch(arr)
                    route_edge_lines.append(arr)

            # Move data packet along full CH-routed path
            data_duration = float(PHASE_DATA_FLOW[1] - PHASE_DATA_FLOW[0])
            df = frame - PHASE_DATA_FLOW[0]
            prog = min(1.0, df / data_duration)
            full_route_len = len(full_route) - 1 if full_route else 1
            hop_index = int(prog * full_route_len)
            hop_index = min(hop_index, full_route_len)
            if full_route and hop_index < len(full_route):
                dp = positions[full_route[hop_index]]
                data_scatter.set_offsets([[dp[0], dp[1]]])
                pulse = 0.5 + 0.5 * abs(math.sin(frame * 1.0))
                data_scatter.set_alpha(pulse)
            else:
                data_scatter.set_alpha(0.0)
                data_scatter.set_offsets(np.empty((0, 2)))

        artists = [
            node_scatter, ch_scatter, leader_scatter, source_scatter, dest_scatter,
            source_label, dest_label, search_scatter, data_scatter,
            phase_text, stats_text,
        ] + node_labels + route_edge_lines
        return artists

    anim = animation.FuncAnimation(
        fig, update, frames=TOTAL_FRAMES,
        interval=1000.0 / FPS, blit=False,
    )

    writer = animation.FFMpegWriter(fps=FPS, codec="libx264", bitrate=1800)
    anim.save(OUTPUT_FILE, writer=writer)
    plt.close(fig)
    print(f"Saved {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
