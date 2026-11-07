#!/usr/bin/env python3
"""
VECTOR — CH Failure → Orphaned Members → Reassignment Animation
Renders a single MP4 video showing a cluster head (CH) completely dying,
its member nodes becoming orphaned, then reassigning to surviving CHs,
and finally SEARCH healing the broken links.

Output: analysis/videos/network_breaking.mp4
"""
import os
import sys
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, Circle
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim_engine import Simulator, SimConfig, heed_clustering, _assign_to_chs, bfs_shortest_path

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
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "network_breaking.mp4")

# Dark theme colors (consistent with generate_network_animations.py)
BG_COLOR = "#0d1117"
NODE_COLOR = "#58a6ff"        # blue - MEMBER
CH_COLOR = "#f0c808"          # amber - cluster head
ULTIMATE_LEADER_COLOR = "#ff7b72"   # red - ultimate leader
EDGE_COLOR = "#30363d"        # subtle topology edges
FAILED_COLOR = "#444455"      # dark gray - failed node
FAILED_EDGE_COLOR = "#1f2328" # broken edge
SEARCH_COLOR = "#79c0ff"      # light blue - search packet
RECOVERED_COLOR = "#3fb950"   # green - recovered / re-linked
NEW_LINK_COLOR = "#58a6ff"    # blue - new link
ORPHAN_COLOR = "#8b949e"      # dim gray - orphaned member
ORPHAN_HIGHLIGHT = "#ff7b72"  # red ring - orphaned member highlight
REASSIGN_COLOR = "#79c0ff"    # light blue - reassignment dashed line
REASSIGN_DONE_COLOR = "#3fb950"  # green - reassigned member
TEXT_COLOR = "#c9d1d9"        # off-white text
ARROW_COLOR = "#f0c808"       # amber arrows
BREAK_COLOR = "#ff7b72"       # red - breaking link
BATTERY_GOOD = "#3fb950"
BATTERY_LOW = "#f0c808"
BATTERY_CRITICAL = "#ff7b72"

# Phase frame ranges (inclusive end)
PHASE_ESTABLISHED = (0, 25)
PHASE_CH_FAILURE = (26, 50)
PHASE_LINK_BREAK = (51, 75)
PHASE_ORPHANED = (76, 100)
PHASE_REASSIGN = (101, 140)
PHASE_RELINKED = (141, 180)


def battery_color(ratio):
    if ratio > 0.5:
        return BATTERY_GOOD
    if ratio > 0.2:
        return BATTERY_LOW
    return BATTERY_CRITICAL


def bfs_layers(adj, src, dst, alive):
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
    """BFS restricted to CH nodes only (src_ch and dst_ch are CHs).
    Path: src_ch -> ... -> dst_ch, traversing only cluster heads."""
    if src_ch == dst_ch:
        return [src_ch]
    parent = {src_ch: -1}
    visited = {src_ch}
    current = [src_ch]
    while current:
        nxt = []
        for u in current:
            for v in adj[u]:
                # Only traverse CH nodes (and allow dst_ch as termination)
                if v not in visited and v in ch_set and alive[v]:
                    visited.add(v)
                    parent[v] = u
                    if v == dst_ch:
                        # reconstruct path
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

    # Cluster heads via HEED
    chs, assign = heed_clustering(nodes, adj, cfg, sim.rng)
    ch_set = set(chs)

    # Ensure at least 3 cluster heads are visible; re-run assignment so all
    # members belong to a real CH in ch_set.
    chs_list = list(chs)
    if len(chs_list) < 3:
        for i in range(NUM_NODES):
            if i not in ch_set:
                chs_list.append(i)
                ch_set.add(i)
                if len(chs_list) >= 3:
                    break
        assign = _assign_to_chs(nodes, adj, list(range(NUM_NODES)), chs_list, cfg.wireless_range)

    # Pick a cluster head that HAS members to fail (so there are orphans)
    chs_with_members = [c for c in chs_list if any(a == c for a in assign.values()) and c in ch_set]
    if chs_with_members:
        fail_idx = max(chs_with_members, key=lambda i: len(adj[i]))
    elif chs_list:
        fail_idx = chs_list[0]
    else:
        fail_idx = sim.rng.randrange(NUM_NODES)
    fail_pos = positions[fail_idx]

    # Members under the failing CH (orphan candidates)
    orphan_members = [i for i, ch in assign.items() if ch == fail_idx and i != fail_idx]

    # Pick two neighbors of the failed node as source/dest for the recovery search
    neighbors = [j for j in adj[fail_idx] if alive_flags[j] and j != fail_idx]
    if len(neighbors) < 2:
        candidates = [i for i in range(NUM_NODES) if alive_flags[i] and i != fail_idx]
        source_idx = candidates[0] if candidates else 0
        dest_idx = candidates[1] if len(candidates) > 1 else (fail_idx + 1) % NUM_NODES
    else:
        source_idx = neighbors[0]
        dest_idx = neighbors[1]

    # Links incident to the failed node that will be broken
    break_edges = []
    for j in neighbors:
        edge_key = (fail_idx, j) if fail_idx < j else (j, fail_idx)
        break_edges.append(edge_key)

    # Surviving cluster heads for reassignment targets
    surviving_chs = [i for i in chs_list if i != fail_idx and alive_flags[i]]

    # Source/dest CHs (which CH each endpoint belongs to, after reassignment)
    # Must be real surviving cluster heads (not self-assigned orphans out of range)
    source_ch = assign.get(source_idx, -1)
    if source_ch == fail_idx or source_ch == -1 or source_ch not in ch_set:
        source_ch = surviving_chs[0] if surviving_chs else -1
    dest_ch = assign.get(dest_idx, -1)
    if dest_ch == fail_idx or dest_ch == -1 or dest_ch not in ch_set:
        dest_ch = surviving_chs[-1] if surviving_chs else -1

    # Precompute nearest surviving CH for each orphan (no range limit for reassignment)
    orphan_new_ch = {}
    for m in orphan_members:
        best_ch = -1
        best_dist = float("inf")
        for ch in surviving_chs:
            d = float(np.linalg.norm(positions[m] - positions[ch]))
            if d < best_dist:
                best_dist = d
                best_ch = ch
        orphan_new_ch[m] = best_ch

    # Update assign to reflect orphan reassignment (so source_ch/dest_ch are correct)
    for m, new_ch in orphan_new_ch.items():
        if new_ch != -1:
            assign[m] = new_ch

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
        "VECTOR — CH Failure → Orphaned Members → Reassignment",
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
    edge_lines = []
    edge_map = {}
    for i in range(NUM_NODES):
        for j in adj[i]:
            if j > i:
                x1, y1 = positions[i]
                x2, y2 = positions[j]
                line, = ax.plot(
                    [x1, x2], [y1, y2],
                    color=EDGE_COLOR, linewidth=1.0, alpha=0.5, zorder=1,
                )
                edge_lines.append(line)
                edge_map[(i, j)] = line

    # Draw existing nodes
    node_scatter = ax.scatter(
        positions[:, 0], positions[:, 1],
        s=120, c=NODE_COLOR, edgecolors="white", linewidths=1.5,
        zorder=3, alpha=0.9,
    )

    # Highlight cluster heads as yellow stars
    ch_pos = positions[sorted(ch_set)]
    ch_scatter = ax.scatter(
        ch_pos[:, 0], ch_pos[:, 1],
        s=300, c=CH_COLOR, marker="*", edgecolors="white", linewidths=1.5,
        zorder=4, label="Cluster Head",
    )

    # Select Ultimate Leader
    leader_idx = max(ch_set, key=lambda i: nodes[i].energy) if ch_set else 0
    leader_pos = positions[leader_idx]
    leader_scatter = ax.scatter(
        [leader_pos[0]], [leader_pos[1]],
        s=400, c=ULTIMATE_LEADER_COLOR, marker="D", edgecolors="white", linewidths=2,
        zorder=6, label="Ultimate Leader",
    )

    # Role labels for every existing node (dynamic text updated per phase)
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

    # Endpoint markers of the broken link (subtle rings)
    source_scatter = ax.scatter(
        [positions[source_idx][0]], [positions[source_idx][1]],
        s=180, c="none", edgecolors=TEXT_COLOR, linewidths=1.5,
        zorder=7, marker="o", alpha=0.5,
    )
    dest_scatter = ax.scatter(
        [positions[dest_idx][0]], [positions[dest_idx][1]],
        s=180, c="none", edgecolors=TEXT_COLOR, linewidths=1.5,
        zorder=7, marker="o", alpha=0.5,
    )
    source_label = ax.text(
        positions[source_idx][0], positions[source_idx][1] + 18, "A",
        ha="center", va="bottom", color=TEXT_COLOR, fontsize=8,
        fontweight="bold", zorder=8, alpha=0.6,
    )
    dest_label = ax.text(
        positions[dest_idx][0], positions[dest_idx][1] + 18, "B",
        ha="center", va="bottom", color=TEXT_COLOR, fontsize=8,
        fontweight="bold", zorder=8, alpha=0.6,
    )

    # Failed node highlight (ring around failed node)
    fail_ring = Circle(
        (fail_pos[0], fail_pos[1]), 34, fill=False,
        color=FAILED_COLOR, linewidth=2.5, alpha=0.0, zorder=5,
    )
    ax.add_patch(fail_ring)
    fail_label = ax.text(
        fail_pos[0], fail_pos[1] + 18, "", ha="center", va="bottom",
        color=FAILED_COLOR, fontsize=9, fontweight="bold", zorder=8, alpha=0.0,
    )

    # Energy bar above the failing CH (depletes 100% -> 0%)
    bar_w = 50.0
    bar_h = 7.0
    energy_bg = Rectangle(
        (fail_pos[0] - bar_w / 2, fail_pos[1] + 34), bar_w, bar_h,
        fill=True, color="#1f2328", alpha=0.9, zorder=6,
    )
    energy_bar = Rectangle(
        (fail_pos[0] - bar_w / 2, fail_pos[1] + 34), bar_w, bar_h,
        fill=True, color=BATTERY_GOOD, alpha=0.95, zorder=7,
    )
    energy_label = ax.text(
        fail_pos[0], fail_pos[1] + 34 + bar_h + 4, "100%", ha="center", va="bottom",
        color=TEXT_COLOR, fontsize=7, fontweight="bold", zorder=8, alpha=0.0,
    )
    ax.add_patch(energy_bg)
    ax.add_patch(energy_bar)

    # Orphan highlight rings (one per orphan member, pulsed when orphaned)
    orphan_rings = []
    for m in orphan_members:
        ring = Circle(
            (positions[m][0], positions[m][1]), 30, fill=False,
            color=ORPHAN_HIGHLIGHT, linewidth=2.0, alpha=0.0, zorder=5,
        )
        ax.add_patch(ring)
        orphan_rings.append(ring)

    # Search packet marker
    search_scatter = ax.scatter(
        [], [], s=100, c=SEARCH_COLOR, edgecolors="white", linewidths=1.5,
        zorder=6, marker="o", alpha=0.0,
    )

    # New (recovery) link lines (SEARCH result)
    recovery_lines = []

    # Reassignment dashed lines (orphan -> new CH)
    reassign_lines = []

    # State
    state = {
        "failed": False,
        "edges_broken": False,
        "break_idx": 0,
        "orphans_dimmed": False,
        "reassign_step": 0,
        "recovered": False,
        "visited": set(),
        "new_route": None,
    }

    def get_phase(frame):
        if frame <= PHASE_ESTABLISHED[1]:
            return "established"
        if frame <= PHASE_CH_FAILURE[1]:
            return "ch_failure"
        if frame <= PHASE_LINK_BREAK[1]:
            return "link_break"
        if frame <= PHASE_ORPHANED[1]:
            return "orphaned"
        if frame <= PHASE_REASSIGN[1]:
            return "reassign"
        return "relinked"

    def update(frame):
        phase = get_phase(frame)

        phase_labels = {
            "established": "Phase 1: Established De Bruijn network (30 nodes)",
            "ch_failure": "Phase 2: Cluster head battery drains — CH goes offline",
            "link_break": "Phase 3: Links to failed CH break (red flash)",
            "orphaned": "Phase 4: Members under dead CH become orphaned",
            "reassign": "Phase 5: Orphans reassign to nearest surviving CH",
            "relinked": "Phase 6: SEARCH finds alternate path — network healed",
        }
        phase_text.set_text(phase_labels[phase])

        # ---- Stats text ----
        if phase == "established":
            stats_text.set_text(
                f"Nodes: {NUM_NODES}\nCHs: {len(ch_set)}\nStatus: STABLE"
            )
        elif phase == "ch_failure":
            t = (frame - PHASE_CH_FAILURE[0]) / float(PHASE_CH_FAILURE[1] - PHASE_CH_FAILURE[0])
            energy_pct = int((1.0 - t) * 100)
            stats_text.set_text(
                f"Nodes: {NUM_NODES}\nCH {fail_idx}: OFFLINE\nEnergy: {energy_pct}%\nOrphans: {len(orphan_members)}"
            )
        elif phase == "link_break":
            stats_text.set_text(
                f"Nodes: {NUM_NODES}\nCH {fail_idx}: OFFLINE\nLinks broken: {state['break_idx'] + 1}/{len(break_edges)}\nOrphans: {len(orphan_members)}"
            )
        elif phase == "orphaned":
            stats_text.set_text(
                f"Nodes: {NUM_NODES}\nCH {fail_idx}: OFFLINE\nOrphans: {len(orphan_members)} (disconnected)\nStatus: ORPHANED"
            )
        elif phase == "reassign":
            done = state.get("reassign_step", 0)
            stats_text.set_text(
                f"Nodes: {NUM_NODES}\nCH {fail_idx}: OFFLINE\nReassigning: {done}/{len(orphan_members)}\nOrphans: {len(orphan_members)}"
            )
        else:  # relinked
            stats_text.set_text(
                f"Nodes: {NUM_NODES}\nCH {fail_idx}: OFFLINE\nAll orphans reassigned\nStatus: RELINKED (healed)"
            )

        # ---- Node coloring (base) ----
        node_colors = [NODE_COLOR] * NUM_NODES
        node_sizes = [120] * NUM_NODES
        for i in ch_set:
            if i == fail_idx:
                node_colors[i] = FAILED_COLOR
                node_sizes[i] = 130
            else:
                node_colors[i] = CH_COLOR
                node_sizes[i] = 300
        if fail_idx == leader_idx:
            node_colors[fail_idx] = FAILED_COLOR

        # Orphan dimming / reassigned coloring
        if phase in ("orphaned", "reassign", "relinked"):
            for m in orphan_members:
                node_colors[m] = ORPHAN_COLOR
                node_sizes[m] = 140
        node_scatter.set_facecolor(node_colors)
        node_scatter.set_sizes(node_sizes)

        # ---- Phase-specific animation ----
        if phase == "established":
            fail_ring.set_alpha(0.0)
            fail_label.set_alpha(0.0)
            fail_label.set_text("")
            energy_bg.set_alpha(0.0)
            energy_bar.set_alpha(0.0)
            energy_label.set_alpha(0.0)
            search_scatter.set_offsets(np.empty((0, 2)))
            search_scatter.set_alpha(0.0)
            for line in recovery_lines:
                line.remove()
            recovery_lines.clear()
            for line in reassign_lines:
                line.remove()
            reassign_lines.clear()
            state.update({
                "failed": False, "edges_broken": False, "break_idx": 0,
                "orphans_dimmed": False, "recovered": False,
                "visited": set(), "new_route": None,
            })
            # restore all edges
            for line in edge_lines:
                line.set_alpha(0.5)
                line.set_color(EDGE_COLOR)
                line.set_linewidth(1.0)
            # reset node labels
            for i, txt in enumerate(node_labels):
                if i == leader_idx:
                    txt.set_text(f"UL {i}")
                    txt.set_color(ULTIMATE_LEADER_COLOR)
                    txt.set_fontweight("bold")
                    txt.set_fontsize(10)
                elif i in ch_set:
                    txt.set_text(f"CH {i}")
                    txt.set_color(CH_COLOR)
                    txt.set_fontweight("bold")
                    txt.set_fontsize(9)
                else:
                    txt.set_text(str(i))
                    txt.set_color(NODE_COLOR)
                    txt.set_fontweight("normal")
                    txt.set_fontsize(8)
            # reset orphan rings
            for ring in orphan_rings:
                ring.set_alpha(0.0)

        elif phase == "ch_failure":
            t = (frame - PHASE_CH_FAILURE[0]) / float(PHASE_CH_FAILURE[1] - PHASE_CH_FAILURE[0])
            t = min(1.0, t)
            fail_ring.set_alpha(0.3 + 0.7 * t)
            fail_label.set_alpha(t)
            fail_label.set_text("CH OFFLINE")
            energy_bg.set_alpha(0.9)
            energy_bar.set_alpha(0.95)
            energy_label.set_alpha(1.0)
            energy_pct = int((1.0 - t) * 100)
            energy_bar.set_width(bar_w * max(0.0, 1.0 - t))
            energy_bar.set_color(battery_color(max(0.0, 1.0 - t)))
            energy_label.set_text(f"{energy_pct}%")
            energy_label.set_color(battery_color(max(0.0, 1.0 - t)))
            if t >= 0.6 and not state["failed"]:
                state["failed"] = True
            # CH star fades as it dies
            ch_scatter.set_alpha(1.0 - t)
            search_scatter.set_alpha(0.0)
            for line in recovery_lines:
                line.remove()
            recovery_lines.clear()
            for line in reassign_lines:
                line.remove()
            reassign_lines.clear()
            # restore edges
            for line in edge_lines:
                line.set_alpha(0.5)
                line.set_color(EDGE_COLOR)
                line.set_linewidth(1.0)
            # reset orphan rings
            for ring in orphan_rings:
                ring.set_alpha(0.0)

        elif phase == "link_break":
            fail_ring.set_alpha(0.9)
            fail_label.set_alpha(0.95)
            fail_label.set_text("CH OFFLINE")
            energy_bg.set_alpha(0.9)
            energy_bar.set_alpha(0.0)
            energy_label.set_alpha(0.0)
            ch_scatter.set_alpha(0.0)

            break_duration = float(PHASE_LINK_BREAK[1] - PHASE_LINK_BREAK[0])
            num_break = max(1, len(break_edges))
            per_edge = break_duration / num_break
            frame_in_phase = frame - PHASE_LINK_BREAK[0]
            current_edge_index = int(frame_in_phase / per_edge)
            current_edge_index = min(current_edge_index, num_break - 1)

            for ei, edge_key in enumerate(break_edges):
                line = edge_map.get(edge_key)
                if line is None:
                    continue
                if ei < current_edge_index:
                    line.set_color(FAILED_EDGE_COLOR)
                    line.set_alpha(0.15)
                    line.set_linewidth(1.0)
                elif ei == current_edge_index:
                    t = (frame_in_phase - ei * per_edge) / per_edge
                    t = min(1.0, t)
                    pulse = 1.0 + 1.0 * abs(math.sin(t * math.pi * 3))
                    line.set_color(BREAK_COLOR)
                    line.set_alpha(0.3 + 0.7 * t)
                    line.set_linewidth(3.0 + pulse * 2.0)
                else:
                    line.set_color(EDGE_COLOR)
                    line.set_alpha(0.5)
                    line.set_linewidth(1.0)

            # mark all other edges incident to failed node as broken
            for (i, j), line in edge_map.items():
                if (i == fail_idx or j == fail_idx) and (i, j) not in break_edges and (j, i) not in break_edges:
                    line.set_color(FAILED_EDGE_COLOR)
                    line.set_alpha(0.2)
                    line.set_linewidth(1.0)

            state["break_idx"] = current_edge_index
            state["edges_broken"] = True
            search_scatter.set_alpha(0.0)
            for line in recovery_lines:
                line.remove()
            recovery_lines.clear()
            for line in reassign_lines:
                line.remove()
            reassign_lines.clear()
            state["visited"] = set()

        elif phase == "orphaned":
            fail_ring.set_alpha(0.9)
            fail_label.set_alpha(0.95)
            fail_label.set_text("CH OFFLINE")
            energy_bg.set_alpha(0.0)
            energy_bar.set_alpha(0.0)
            energy_label.set_alpha(0.0)
            ch_scatter.set_alpha(0.0)
            # keep broken edges broken
            for (i, j), line in edge_map.items():
                if i == fail_idx or j == fail_idx:
                    line.set_color(FAILED_EDGE_COLOR)
                    line.set_alpha(0.15)
                    line.set_linewidth(1.0)
            # Color orphaned members distinctly + pulse red ring
            for k, m in enumerate(orphan_members):
                node_colors[m] = ORPHAN_COLOR
                node_sizes[m] = 140
                pulse = 0.4 + 0.6 * abs(math.sin((frame - PHASE_ORPHANED[0] + k * 5) * 0.5))
                orphan_rings[k].set_alpha(pulse)
                orphan_rings[k].center = (positions[m][0], positions[m][1])
                # orphan label
                node_labels[m].set_text("ORPHAN")
                node_labels[m].set_color(ORPHAN_COLOR)
                node_labels[m].set_fontweight("bold")
                node_labels[m].set_fontsize(9)
            node_scatter.set_facecolor(node_colors)
            node_scatter.set_sizes(node_sizes)
            search_scatter.set_alpha(0.0)
            for line in recovery_lines:
                line.remove()
            recovery_lines.clear()
            for line in reassign_lines:
                line.remove()
            reassign_lines.clear()
            state["visited"] = set()

        elif phase == "reassign":
            fail_ring.set_alpha(0.9)
            fail_label.set_alpha(0.95)
            fail_label.set_text("CH OFFLINE")
            # keep broken edges broken
            for (i, j), line in edge_map.items():
                if i == fail_idx or j == fail_idx:
                    line.set_color(FAILED_EDGE_COLOR)
                    line.set_alpha(0.15)
                    line.set_linewidth(1.0)

            # Clear old reassignment lines and redraw for current step
            for line in reassign_lines:
                line.remove()
            reassign_lines.clear()

            # Sequential orphan reassignment: one orphan at a time
            num_orphans = len(orphan_members)
            if num_orphans > 0:
                reassign_duration = float(PHASE_REASSIGN[1] - PHASE_REASSIGN[0])
                per_orphan = reassign_duration / num_orphans
                frame_in_phase = frame - PHASE_REASSIGN[0]
                current_step = int(frame_in_phase / per_orphan)
                current_step = min(current_step, num_orphans - 1)
                state["reassign_step"] = current_step + 1

                # Draw dashed lines for orphans already reassigned
                for si in range(current_step + 1):
                    m = orphan_members[si]
                    new_ch = orphan_new_ch.get(m, -1)
                    if new_ch != -1:
                        # dashed line from orphan to new CH
                        line, = ax.plot(
                            [positions[m][0], positions[new_ch][0]],
                            [positions[m][1], positions[new_ch][1]],
                            color=REASSIGN_COLOR, linewidth=2.5, alpha=0.8,
                            linestyle="--", zorder=2,
                        )
                        reassign_lines.append(line)
                        # Color the orphan green = reassigned
                        node_colors[m] = REASSIGN_DONE_COLOR
                        node_sizes[m] = 150
                        # Label showing which CH it joined
                        node_labels[m].set_text(f"→CH {new_ch}")
                        node_labels[m].set_color(REASSIGN_DONE_COLOR)
                        node_labels[m].set_fontweight("bold")
                        node_labels[m].set_fontsize(8)
                        # Turn off the orphan ring for reassigned orphans
                        orphan_rings[si].set_alpha(0.0)

                # Orphans not yet reassigned: still orphaned with pulsing ring
                for si in range(current_step + 1, num_orphans):
                    m = orphan_members[si]
                    node_colors[m] = ORPHAN_COLOR
                    node_sizes[m] = 140
                    pulse = 0.4 + 0.6 * abs(math.sin((frame - PHASE_REASSIGN[0] + si * 5) * 0.5))
                    orphan_rings[si].set_alpha(pulse)
                    orphan_rings[si].center = (positions[m][0], positions[m][1])
                    node_labels[m].set_text("ORPHAN")
                    node_labels[m].set_color(ORPHAN_COLOR)
                    node_labels[m].set_fontweight("bold")
                    node_labels[m].set_fontsize(9)

            node_scatter.set_facecolor(node_colors)
            node_scatter.set_sizes(node_sizes)

            search_scatter.set_alpha(0.0)
            for line in recovery_lines:
                line.remove()
            recovery_lines.clear()
            state["visited"] = set()

        else:  # relinked
            fail_ring.set_alpha(0.9)
            fail_label.set_alpha(0.95)
            fail_label.set_text("CH OFFLINE")
            # keep broken edges broken
            for (i, j), line in edge_map.items():
                if i == fail_idx or j == fail_idx:
                    line.set_color(FAILED_EDGE_COLOR)
                    line.set_alpha(0.15)
                    line.set_linewidth(1.0)
            # Keep reassigned members green, orphan rings off
            for m in orphan_members:
                new_ch = orphan_new_ch.get(m, -1)
                if new_ch != -1:
                    node_colors[m] = REASSIGN_DONE_COLOR
                    node_sizes[m] = 150
                    node_labels[m].set_text(f"→CH {new_ch}")
                    node_labels[m].set_color(REASSIGN_DONE_COLOR)
                    node_labels[m].set_fontweight("bold")
                    node_labels[m].set_fontsize(8)
                else:
                    node_colors[m] = ORPHAN_COLOR
                    node_sizes[m] = 140
                    node_labels[m].set_text("ORPHAN")
                    node_labels[m].set_color(ORPHAN_COLOR)
            for ring in orphan_rings:
                ring.set_alpha(0.0)
            node_scatter.set_facecolor(node_colors)
            node_scatter.set_sizes(node_sizes)
            search_scatter.set_alpha(0.0)
            for line in reassign_lines:
                line.remove()
            reassign_lines.clear()

            # SEARCH: find CH-routed alternate path from source to dest avoiding failed CH
            if not state["recovered"]:
                alive_recovery = list(alive_flags)
                alive_recovery[fail_idx] = False

                # CH-to-CH path (only cluster heads as intermediate nodes)
                ch_path = None
                if source_ch != -1 and dest_ch != -1:
                    ch_path = bfs_ch_only(adj, source_ch, dest_ch, alive_recovery, set(surviving_chs))

                # Build full end-to-end path: source_member -> ...CH path... -> dest_member
                full_path = None
                if ch_path:
                    full_path = [source_idx] + ch_path + [dest_idx]
                else:
                    # Safety net: fall back to all-node BFS
                    layers, new_route = bfs_layers(adj, source_idx, dest_idx, alive_recovery)
                    if new_route:
                        full_path = new_route

                if full_path:
                    for line in recovery_lines:
                        line.remove()
                    recovery_lines.clear()
                    for k in range(len(full_path) - 1):
                        a = positions[full_path[k]]
                        b = positions[full_path[k + 1]]
                        line, = ax.plot(
                            [a[0], b[0]], [a[1], b[1]],
                            color=NEW_LINK_COLOR, linewidth=3.0, alpha=0.9, zorder=2,
                        )
                        recovery_lines.append(line)
                    state["new_route"] = full_path
                    # Display CH-routed path in stats
                    path_str = " → ".join(
                        f"CH {n}" if n in chs_list else str(n) for n in full_path
                    )
                    stats_text.set_text(
                        f"Nodes: {NUM_NODES}\nCH {fail_idx}: OFFLINE\nPath: {path_str}\nVia Cluster Heads"
                    )
                state["recovered"] = True

        artists = [
            node_scatter, ch_scatter, leader_scatter, source_scatter, dest_scatter,
            source_label, dest_label, fail_ring, fail_label, search_scatter,
            energy_bg, energy_bar, energy_label, phase_text, stats_text,
        ] + node_labels + edge_lines + recovery_lines + reassign_lines + orphan_rings
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
