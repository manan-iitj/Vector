#!/usr/bin/env python3
"""
VECTOR — Network Joining Animation
Renders a single MP4 video showing a new node approaching an established
De Bruijn network, performing the 3-message TurboBlom handshake, and joining.

Output: analysis/videos/network_joining.mp4
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

# Reuse VECTOR simulation engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim_engine import Simulator, SimConfig, generate_debruijn, heed_clustering

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NUM_NODES = 30
SEED = 42
FPS = 15
TOTAL_FRAMES = 180
AREA = 1000.0
WIRELESS_RANGE = 200.0
Y_OFFSET = 150.0  # shift entire network upward

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "videos")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "network_joining.mp4")

# Dark theme colors (consistent with existing generate_plots.py)
BG_COLOR = "#0d1117"        # dark navy background
NODE_COLOR = "#58a6ff"      # blue - MEMBER
CH_COLOR = "#f0c808"        # amber - cluster head
ULTIMATE_LEADER_COLOR = "#ff7b72"   # red - ultimate leader
NEW_NODE_COLOR = "#8b949e"  # gray - NEW_NODE
JOINING_COLOR = "#d29922"   # orange - JOINING
AUTH_COLOR = "#3fb950"      # green - AUTHENTICATED
EDGE_COLOR = "#30363d"      # subtle topology edges
NEW_EDGE_COLOR = "#79c0ff"  # light blue new edges
TEXT_COLOR = "#c9d1d9"      # off-white text
ARROW_COLOR = "#f0c808"     # amber arrows

# Phase frame ranges (inclusive end)
PHASE_ESTABLISHED = (0, 30)
PHASE_APPROACH = (31, 60)
PHASE_HANDSHAKE = (61, 105)
PHASE_AUTHENTICATED = (106, 135)
PHASE_MEMBER = (136, 180)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Build the network with deterministic seed
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
    alive_idx = list(range(NUM_NODES))
    chs, assign = heed_clustering(nodes, adj, cfg, sim.rng)
    ch_set = set(chs)
    # Ensure at least 3 cluster heads are clearly visible in the video
    if len(ch_set) < 3:
        for i in range(NUM_NODES):
            if i not in ch_set:
                ch_set.add(i)
                if len(ch_set) >= 3:
                    break

    # New node approaches from bottom-right toward network center
    approach_start = np.array([AREA + 150.0, AREA + 150.0 + Y_OFFSET])
    approach_target = np.array([AREA / 2.0, AREA / 2.0 + Y_OFFSET])

    # Nearest CLUSTER HEAD to the approach target (join target must be a CH)
    ch_positions = positions[sorted(ch_set)]
    distances_to_target = np.linalg.norm(ch_positions - approach_target, axis=1)
    nearest_ch_local = int(np.argmin(distances_to_target))
    nearest_ch_idx = sorted(ch_set)[nearest_ch_local]
    nearest_pos = positions[nearest_ch_idx]

    # Second-nearest node (for forming a second logical link after join)
    dists = np.linalg.norm(positions - nearest_pos, axis=1)
    dists[nearest_ch_idx] = float("inf")
    second_idx = int(np.argmin(dists))
    second_pos = positions[second_idx]

    # Offset for new node relative to nearest cluster head once it arrives
    join_offset = np.array([45.0, -45.0])
    join_pos = nearest_pos + join_offset

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
        "VECTOR — Network Joining (De Bruijn + TurboBlom Handshake)",
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

    # Draw existing nodes
    node_scatter = ax.scatter(
        positions[:, 0], positions[:, 1],
        s=120, c=NODE_COLOR, edgecolors="white", linewidths=1.5,
        zorder=3, alpha=0.9,
    )

    # Highlight cluster heads as yellow stars
    if ch_set:
        ch_pos = positions[sorted(ch_set)]
    else:
        ch_pos = np.empty((0, 2))
    ch_scatter = ax.scatter(
        ch_pos[:, 0], ch_pos[:, 1],
        s=300, c=CH_COLOR, marker="*", edgecolors="white", linewidths=1.5,
        zorder=4, label="Cluster Head",
    )

    # Select Ultimate Leader: the cluster head with highest residual energy
    if ch_set:
        leader_idx = max(ch_set, key=lambda i: nodes[i].energy)
    else:
        leader_idx = 0
    leader_pos = positions[leader_idx]
    leader_scatter = ax.scatter(
        [leader_pos[0]], [leader_pos[1]],
        s=400, c=ULTIMATE_LEADER_COLOR, marker="D", edgecolors="white", linewidths=2,
        zorder=6, label="Ultimate Leader",
    )

    # Role labels for every existing node
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

    # New node (starts off-screen)
    new_node_scatter = ax.scatter(
        [approach_start[0]], [approach_start[1]],
        s=160, c=NEW_NODE_COLOR, edgecolors="white", linewidths=2,
        zorder=5, marker="o",
    )

    # New node label (role progression shown beside it)
    new_node_label = ax.text(
        approach_start[0], approach_start[1] + 18, "", ha="center", va="bottom",
        color=NEW_NODE_COLOR, fontsize=9, fontweight="bold", zorder=6,
    )

    # Trajectory arrow for approaching node
    traj_arrow = FancyArrowPatch(
        approach_start, approach_start,
        arrowstyle="->", mutation_scale=15, color=NODE_COLOR,
        linewidth=2, alpha=0.0, zorder=2,
    )
    ax.add_patch(traj_arrow)

    # Handshake arrows (between new node and nearest neighbor)
    handshake_arrows = []
    for _ in range(3):
        arr = FancyArrowPatch(
            (0, 0), (0, 0),
            arrowstyle="->", mutation_scale=14, color=ARROW_COLOR,
            linewidth=2.5, alpha=0.0, zorder=6,
        )
        ax.add_patch(arr)
        handshake_arrows.append(arr)

    # Handshake message label
    msg_label = ax.text(
        0.5, 0.5, "", transform=ax.transAxes,
        ha="center", va="center", color=ARROW_COLOR, fontsize=11,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#2a2a4a", alpha=0.95, edgecolor=ARROW_COLOR),
    )

    # New logical edges (drawn after authentication)
    new_edge_lines = []

    # State carried across frames
    state = {"new_edges_drawn": False}

    def get_phase(frame):
        if frame <= PHASE_ESTABLISHED[1]:
            return "established"
        if frame <= PHASE_APPROACH[1]:
            return "approach"
        if frame <= PHASE_HANDSHAKE[1]:
            return "handshake"
        if frame <= PHASE_AUTHENTICATED[1]:
            return "authenticated"
        return "member"

    def update(frame):
        phase = get_phase(frame)

        phase_labels = {
            "established": "Phase 1: Established De Bruijn network (30 nodes)",
            "approach": "Phase 2: New node approaching the network",
            "handshake": "Phase 3: 3-message TurboBlom authentication handshake",
            "authenticated": "Phase 4: Authentication accepted — forming logical links",
            "member": "Phase 5: Node joined as full MEMBER",
        }
        phase_text.set_text(phase_labels[phase])

        if phase == "member":
            stats_text.set_text(
                f"Nodes: {NUM_NODES + 1}\nStatus: JOINED\nTopology: De Bruijn"
            )
        else:
            stats_text.set_text(
                f"Nodes: {NUM_NODES}\nStatus: ESTABLISHED\nTopology: De Bruijn"
            )

        # ---- Animate new node position ----
        if phase == "established":
            new_node_scatter.set_offsets([[approach_start[0], approach_start[1]]])
            new_node_scatter.set_color(NEW_NODE_COLOR)
            new_node_scatter.set_sizes([160])
            new_node_label.set_position((approach_start[0], approach_start[1] + 18))
            new_node_label.set_text("")
            new_node_label.set_color(NEW_NODE_COLOR)
            traj_arrow.set_positions(approach_start, approach_start)
            traj_arrow.set_alpha(0.0)

            for arr in handshake_arrows:
                arr.set_alpha(0.0)
            msg_label.set_text("")

            for line in new_edge_lines:
                line.remove()
            new_edge_lines.clear()
            state["new_edges_drawn"] = False

        elif phase == "approach":
            t = (frame - PHASE_APPROACH[0]) / float(PHASE_APPROACH[1] - PHASE_APPROACH[0])
            t = min(1.0, t)
            pos = approach_start + t * (nearest_pos - approach_start)
            new_node_scatter.set_offsets([[pos[0], pos[1]]])
            new_node_scatter.set_color(NEW_NODE_COLOR)
            new_node_scatter.set_sizes([160])
            new_node_label.set_position((pos[0], pos[1] + 18))
            new_node_label.set_text("NEW_NODE")
            new_node_label.set_color(NEW_NODE_COLOR)
            traj_arrow.set_positions(approach_start, pos)
            traj_arrow.set_alpha(0.7)

            for arr in handshake_arrows:
                arr.set_alpha(0.0)
            msg_label.set_text("")

            for line in new_edge_lines:
                line.remove()
            new_edge_lines.clear()
            state["new_edges_drawn"] = False

        elif phase == "handshake":
            new_node_scatter.set_offsets([[join_pos[0], join_pos[1]]])
            new_node_scatter.set_color(JOINING_COLOR)
            new_node_scatter.set_sizes([180])
            new_node_label.set_position((join_pos[0], join_pos[1] + 18))
            new_node_label.set_text("JOINING")
            new_node_label.set_color(JOINING_COLOR)
            traj_arrow.set_alpha(0.0)

            hs_frame = frame - PHASE_HANDSHAKE[0]
            hs_duration = float(PHASE_HANDSHAKE[1] - PHASE_HANDSHAKE[0])
            msg_duration = hs_duration / 3.0

            messages = [
                ("Msg 1: ID_A, nonce_A", join_pos, nearest_pos),
                ("Msg 2: ID_B, nonce_B, MAC", nearest_pos, join_pos),
                ("Msg 3: MAC (session key)", join_pos, nearest_pos),
            ]

            shown = False
            for i, (label, src, dst) in enumerate(messages):
                msg_start = i * msg_duration
                msg_end = (i + 1) * msg_duration
                if msg_start <= hs_frame < msg_end:
                    for j, arr in enumerate(handshake_arrows):
                        if j == i:
                            pulse = 0.4 + 0.6 * abs(math.sin(hs_frame * 0.6))
                            arr.set_alpha(pulse)
                            arr.set_positions(src, dst)
                        else:
                            arr.set_alpha(0.0)
                    msg_label.set_position(((src[0] + dst[0]) / 2.0, (src[1] + dst[1]) / 2.0 + 30.0))
                    msg_label.set_text(label)
                    shown = True
                    break
            if not shown:
                for arr in handshake_arrows:
                    arr.set_alpha(0.0)
                msg_label.set_text("")

            for line in new_edge_lines:
                line.remove()
            new_edge_lines.clear()
            state["new_edges_drawn"] = False

        elif phase == "authenticated":
            new_node_scatter.set_offsets([[join_pos[0], join_pos[1]]])
            new_node_scatter.set_color(AUTH_COLOR)
            new_node_scatter.set_sizes([180])
            new_node_label.set_position((join_pos[0], join_pos[1] + 18))
            new_node_label.set_text("AUTHENTICATED")
            new_node_label.set_color(AUTH_COLOR)
            traj_arrow.set_alpha(0.0)
            for arr in handshake_arrows:
                arr.set_alpha(0.0)
            msg_label.set_text("")

            if not state["new_edges_drawn"]:
                for line in new_edge_lines:
                    line.remove()
                new_edge_lines.clear()
                for nb_pos in (nearest_pos, second_pos):
                    line, = ax.plot(
                        [join_pos[0], nb_pos[0]], [join_pos[1], nb_pos[1]],
                        color=NEW_EDGE_COLOR, linewidth=2.0, alpha=0.85, zorder=2,
                    )
                    new_edge_lines.append(line)
                state["new_edges_drawn"] = True

        else:  # member
            new_node_scatter.set_offsets([[join_pos[0], join_pos[1]]])
            new_node_scatter.set_color(NODE_COLOR)
            new_node_scatter.set_sizes([160])
            new_node_label.set_position((join_pos[0], join_pos[1] + 18))
            new_node_label.set_text("MEMBER")
            new_node_label.set_color(NODE_COLOR)
            traj_arrow.set_alpha(0.0)
            for arr in handshake_arrows:
                arr.set_alpha(0.0)
            msg_label.set_text("")

            if not state["new_edges_drawn"]:
                for line in new_edge_lines:
                    line.remove()
                new_edge_lines.clear()
                for nb_pos in (nearest_pos, second_pos):
                    line, = ax.plot(
                        [join_pos[0], nb_pos[0]], [join_pos[1], nb_pos[1]],
                        color=NEW_EDGE_COLOR, linewidth=2.0, alpha=0.85, zorder=2,
                    )
                    new_edge_lines.append(line)
                state["new_edges_drawn"] = True

        artists = [
            node_scatter, ch_scatter, leader_scatter, new_node_scatter, new_node_label, traj_arrow,
            phase_text, stats_text, msg_label,
        ] + handshake_arrows + node_labels
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
