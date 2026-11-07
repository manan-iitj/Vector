#!/usr/bin/env python3
"""
VECTOR — Leader Election: Battery-Driven CH → UL Formation
Renders a single MP4 video showing:
- Random battery assignment (20-100%) to all nodes, continuous drain
- HEED (from sim_engine) elects Cluster Heads based on battery + connectivity
- Member→CH topology edges form progressively (one by one)
- Max-battery CH becomes Ultimate Leader
- CH→UL connection forms when UL elected
- CH and UL drain faster after election (penalties)
- No re-election phase

Output: analysis/videos/leader_election.mp4
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
import random

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
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "leader_election.mp4")

# Dark theme colors
BG_COLOR = "#0d1117"
NODE_COLOR = "#58a6ff"        # blue - MEMBER
CH_COLOR = "#f0c808"          # amber - cluster head
ULTIMATE_LEADER_COLOR = "#ff7b72"   # red - ultimate leader
EDGE_COLOR = "#30363d"        # subtle topology edges
DEAD_COLOR = "#444455"        # dark gray - dead node
TEXT_COLOR = "#c9d1d9"        # off-white text
BATTERY_GOOD = "#3fb950"      # green >50%
BATTERY_LOW = "#f0c808"       # yellow 20-50%
BATTERY_CRITICAL = "#ff7b72"  # red <20%

# Drain rates per frame
DRAIN_NORMAL = (0.05, 0.15)    # normal member
DRAIN_CH = (0.2, 0.4)          # CH penalty
DRAIN_UL = (0.5, 0.8)          # UL penalty (heaviest)

# Phase frame ranges (inclusive end)
PHASE_INIT = (0, 25)
PHASE_CH_ELECTION = (26, 60)
PHASE_UL_ELECTION = (61, 95)
PHASE_BATTERY_DRAIN = (96, 130)
PHASE_FINAL = (131, 180)

# Energy bar dimensions
BAR_W = 40.0
BAR_H = 7.0


def battery_color(ratio):
    if ratio > 0.5:
        return BATTERY_GOOD
    if ratio > 0.2:
        return BATTERY_LOW
    return BATTERY_CRITICAL


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
    # Shift nodes down well below heading/subheading at top
    NODE_Y_SHIFT = 700.0
    positions = np.array([[n.x, n.y + Y_OFFSET - NODE_Y_SHIFT] for n in nodes])

    # --- Assign random initial battery (20-100%) to each node ---
    for i in range(NUM_NODES):
        nodes[i].energy = random.uniform(20.0, 100.0)
        nodes[i].initial_energy = nodes[i].energy

    # --- Track node roles and topology ---
    ul_idx = None
    ch_set = set()
    member_ch_assign = {}
    topology_edges = []           # list of (line, member, ch)
    ul_edge_lines = []            # CH→UL edge lines
    ul_edge_drawn = False

    # --- Select UL from CHs ---
    def select_ul():
        if not ch_set:
            return None
        alive_chs = [i for i in ch_set if nodes[i].alive]
        if not alive_chs:
            return None
        return max(alive_chs, key=lambda i: nodes[i].energy)

    # -------------------------------------------------------------------
    # Figure setup
    # -------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(-50, AREA + 100)
    ax.set_ylim(-50 + Y_OFFSET - NODE_Y_SHIFT, AREA + 200 + Y_OFFSET - NODE_Y_SHIFT)
    ax.set_aspect("equal")
    ax.axis("off")

    title = ax.text(
        0.5, 0.965,
        "VECTOR — Leader Election: Battery-Driven CH → UL",
        transform=ax.transAxes, ha="center", va="top",
        color=TEXT_COLOR, fontsize=16, fontweight="bold",
    )

    phase_text = ax.text(
        0.5, 0.88, "", transform=ax.transAxes,
        ha="center", va="top", color=TEXT_COLOR, fontsize=13,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#2a2a4a", alpha=0.95, edgecolor=TEXT_COLOR),
    )

    # Draw all nodes (scatter - we update colors/sizes per frame)
    node_scatter = ax.scatter(
        positions[:, 0], positions[:, 1],
        s=120, c=NODE_COLOR, edgecolors="white", linewidths=2,
        zorder=3, alpha=0.9,
    )

    # Energy bars (one per node, initially hidden/zero)
    battery_bars = []
    battery_bgs = []
    battery_labels = []
    for i in range(NUM_NODES):
        x, y = positions[i]
        bg = Rectangle(
            (x - BAR_W / 2, y + 35), BAR_W, BAR_H,
            fill=True, color="#1f2328", alpha=0.0, zorder=6,
        )
        bar = Rectangle(
            (x - BAR_W / 2, y + 35), 0.0, BAR_H,
            fill=True, color=BATTERY_GOOD, alpha=0.0, zorder=7,
        )
        lbl = ax.text(
            x, y + 35 + BAR_H + 4, "", ha="center", va="bottom",
            color=TEXT_COLOR, fontsize=7, fontweight="bold", alpha=0.0, zorder=8,
        )
        ax.add_patch(bg)
        ax.add_patch(bar)
        battery_bgs.append(bg)
        battery_bars.append(bar)
        battery_labels.append(lbl)

    # Role labels (updated per frame)
    node_labels = []
    for i in range(NUM_NODES):
        x, y = positions[i]
        txt = ax.text(
            x, y + 18, str(i), ha="center", va="bottom",
            color=NODE_COLOR, fontsize=8, fontweight="normal", zorder=5, alpha=0.0,
        )
        node_labels.append(txt)

    # UL highlight ring (appears when UL elected)
    ul_ring = Circle((0, 0), 45, fill=False, color=ULTIMATE_LEADER_COLOR,
                     linewidth=3, alpha=0.0, zorder=7)
    ax.add_patch(ul_ring)

    # State
    state = {
        "uls_idx": None,
        "ch_elected": False,
        "ul_elected": False,
    }

    def get_phase(frame):
        if frame <= PHASE_INIT[1]:
            return "init"
        if frame <= PHASE_CH_ELECTION[1]:
            return "ch_election"
        if frame <= PHASE_UL_ELECTION[1]:
            return "ul_election"
        if frame <= PHASE_BATTERY_DRAIN[1]:
            return "battery_drain"
        return "final"

    def apply_battery_drain(phase):
        """Drain battery for all nodes based on phase and role."""
        for i in range(NUM_NODES):
            if not nodes[i].alive:
                continue
            if phase == "init":
                drain = sim.rng.uniform(*DRAIN_NORMAL)
            elif phase in ("ch_election", "ul_election", "battery_drain", "final"):
                if i == state["uls_idx"]:
                    drain = sim.rng.uniform(*DRAIN_UL)
                elif i in ch_set:
                    drain = sim.rng.uniform(*DRAIN_CH)
                else:
                    drain = sim.rng.uniform(*DRAIN_NORMAL)
            else:
                drain = sim.rng.uniform(*DRAIN_NORMAL)
            nodes[i].consume(drain)

    def update(frame):
        nonlocal ul_edge_lines, ul_edge_drawn
        phase = get_phase(frame)

        # Apply battery drain every frame
        apply_battery_drain(phase)

        # ---- Phase labels ----
        phase_labels = {
            "init": "Phase 1: Random battery — all members, no connections",
            "ch_election": "Phase 2: HEED elects Cluster Heads — topology forms",
            "ul_election": "Phase 3: Ultimate Leader elected — max battery CH",
            "battery_drain": "Phase 4: Battery drain — UL & CH penalties active",
            "final": "Phase 5: Network stable — Leader: {}".format(
                state["uls_idx"] if state["uls_idx"] is not None else "none"
            ),
        }
        phase_text.set_text(phase_labels[phase])

        # ---- CH election via sim_engine.heed_clustering (runs once) ----
        if phase == "ch_election" and not state["ch_elected"]:
            chs, assign = heed_clustering(nodes, adj, cfg, sim.rng)
            ch_set.clear()
            ch_set.update(chs)
            # Ensure at least 4 CHs are visible for the animation
            if len(ch_set) < 4:
                alive = [i for i in range(NUM_NODES) if nodes[i].alive]
                alive_sorted = sorted(alive, key=lambda i: nodes[i].energy, reverse=True)
                for i in alive_sorted:
                    if i not in ch_set:
                        ch_set.add(i)
                    if len(ch_set) >= 4:
                        break
            # Re-assign members to nearest CH (includes forced CHs) - connect ALL members
            member_ch_assign.clear()
            for i in range(NUM_NODES):
                if i in ch_set or not nodes[i].alive:
                    continue
                best_ch = -1
                best_dist = float("inf")
                for ch in ch_set:
                    if not nodes[ch].alive:
                        continue
                    d = math.hypot(nodes[i].x - nodes[ch].x, nodes[i].y - nodes[ch].y)
                    if d < best_dist:
                        best_dist = d
                        best_ch = ch
                if best_ch != -1:
                    member_ch_assign[i] = best_ch
            state["ch_elected"] = True

        # ---- UL election logic (runs once at start of ul_election) ----
        if phase == "ul_election" and not state["ul_elected"]:
            state["uls_idx"] = select_ul()
            state["ul_elected"] = True

        cur_ul = state["uls_idx"]

        # ---- Compute node colors and sizes based on phase progression ----
        node_colors = []
        node_sizes = []
        for i in range(NUM_NODES):
            ratio = nodes[i].energy / 100.0
            if not nodes[i].alive:
                node_colors.append(DEAD_COLOR)
                node_sizes.append(60)
            elif phase == "init":
                # All nodes are blue members initially
                node_colors.append(NODE_COLOR)
                node_sizes.append(int(80 + 320 * ratio))
            elif i == cur_ul:
                node_colors.append(ULTIMATE_LEADER_COLOR)
                node_sizes.append(int(300 + 150 * ratio))
            elif i in ch_set:
                node_colors.append(CH_COLOR)
                node_sizes.append(int(240 + 120 * ratio))
            else:
                node_colors.append(NODE_COLOR)
                node_sizes.append(int(80 + 320 * ratio))
        node_scatter.set_color(node_colors)
        node_scatter.set_sizes(node_sizes)

        # ---- Update energy bars and labels ----
        for i in range(NUM_NODES):
            ratio = nodes[i].energy / 100.0
            # Bar
            battery_bars[i].set_width(BAR_W * ratio)
            battery_bars[i].set_color(battery_color(ratio) if nodes[i].alive else DEAD_COLOR)
            battery_bars[i].set_alpha(0.9 if nodes[i].alive else 0.0)
            battery_bgs[i].set_alpha(0.9 if nodes[i].alive else 0.0)
            # Label
            if nodes[i].alive:
                if i == cur_ul:
                    lbl_text = f"UL {i}: {int(ratio*100)}%"
                    lbl_color = ULTIMATE_LEADER_COLOR
                elif i in ch_set:
                    lbl_text = f"CH {i}: {int(ratio*100)}%"
                    lbl_color = CH_COLOR
                else:
                    lbl_text = f"{i}: {int(ratio*100)}%"
                    lbl_color = NODE_COLOR
                battery_labels[i].set_text(lbl_text)
                battery_labels[i].set_color(lbl_color)
                battery_labels[i].set_alpha(0.9)
                node_labels[i].set_text(lbl_text.split(": ")[0])
                node_labels[i].set_color(lbl_color)
                node_labels[i].set_alpha(0.9)
            else:
                battery_labels[i].set_alpha(0.0)
                node_labels[i].set_alpha(0.0)

        # ---- Progressive member→CH edge drawing during ch_election ----
        if phase == "ch_election" and state["ch_elected"]:
            edge_draw_duration = float(PHASE_CH_ELECTION[1] - PHASE_CH_ELECTION[0])
            frame_in_phase = frame - PHASE_CH_ELECTION[0]
            if member_ch_assign and len(topology_edges) < len(member_ch_assign):
                sorted_edges = sorted(member_ch_assign.items())
                edges_to_draw = int((frame_in_phase / edge_draw_duration) * len(sorted_edges))
                edges_to_draw = min(edges_to_draw, len(sorted_edges))
                while len(topology_edges) < edges_to_draw:
                    idx = len(topology_edges)
                    member, ch = sorted_edges[idx]
                    x1, y1 = positions[member]
                    x2, y2 = positions[ch]
                    line, = ax.plot(
                        [x1, x2], [y1, y2],
                        color=EDGE_COLOR, linewidth=1.5, alpha=0.5, zorder=1,
                    )
                    topology_edges.append((line, member, ch))

        # ---- CH→UL edge formation during ul_election ----
        if phase == "ul_election" and cur_ul is not None and not ul_edge_drawn:
            ch_edge_lines = []
            for ch in ch_set:
                if ch == cur_ul or not nodes[ch].alive:
                    continue
                x1, y1 = positions[ch]
                x2, y2 = positions[cur_ul]
                line, = ax.plot(
                    [x1, x2], [y1, y2],
                    color=EDGE_COLOR, linewidth=2.0, alpha=0.6, zorder=1,
                )
                ch_edge_lines.append(line)
            ul_edge_lines.extend(ch_edge_lines)
            ul_edge_drawn = True

        # ---- UL ring ----
        if cur_ul is not None and nodes[cur_ul].alive:
            x, y = positions[cur_ul]
            ul_ring.center = (x, y)
            ul_ring.set_alpha(0.8)
        else:
            ul_ring.set_alpha(0.0)

        all_lines = [line for line, _, _ in topology_edges]
        all_lines.extend(ul_edge_lines)

        artists = [
            node_scatter, ul_ring, phase_text,
        ] + node_labels + battery_bars + battery_bgs + battery_labels + all_lines
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
