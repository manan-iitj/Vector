#!/usr/bin/env python3
"""
VECTOR — TurboBlom 3-Message Authentication (Two-Node Focus)
Renders a single MP4 video showing just two nodes (A and B) performing the
TurboBlom 3-message authentication handshake with color-coded phases and
proper pulsing arrows. No secret values or key material is revealed.

Output: analysis/videos/handshake.mp4
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

# Add scripts directory to path for mbedtls_wrapper and sim_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim_engine import TurboBlom
from mbedtls_wrapper import MbedTLSCtx, hmac_sha256

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FPS = 15
TOTAL_FRAMES = 180

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "videos")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "handshake.mp4")

# Dark theme colors
BG_COLOR = "#0d1117"
NODE_INIT_COLOR = "#58a6ff"      # blue - INIT / PROVISION
NODE_PROV_COLOR = "#ab63fa"      # purple - TurboBlom provisioned
NODE_A_COLOR = "#ff7b72"         # red - node A during handshake
NODE_B_COLOR = "#d29922"         # orange - node B during handshake
NODE_AUTH_COLOR = "#3fb950"      # green - authenticated
MSG1_COLOR = "#79c0ff"           # light blue - Msg 1 arrow
MSG2_COLOR = "#ff7b72"           # red - Msg 2 arrow
MSG3_COLOR = "#3fb950"           # green - Msg 3 arrow
AUTH_LINK_COLOR = "#3fb950"      # green - authenticated link
TEXT_COLOR = "#c9d1d9"           # off-white text
ARROW_COLOR = "#f0c808"          # amber arrows

# Phase frame ranges (inclusive end)
PHASE_INIT = (0, 30)
PHASE_PROVISION = (31, 60)
PHASE_HANDSHAKE = (61, 120)
PHASE_AUTHENTICATED = (121, 180)

# Fixed node positions (center-left and center-right, positioned low)
NODE_A_POS = np.array([200.0, -120.0])
NODE_B_POS = np.array([800.0, -120.0])


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- TurboBlom provisioning with mbedTLS CTR_DRBG ---
    tb = TurboBlom(k=4, t=2, field_bits=128, seed=42)
    tb.provision(1)  # Node A
    tb.provision(2)  # Node B
    session_key = tb.derive_key(1, 2)  # Shared session key
    session_key_bytes = session_key.to_bytes(16, "big")

    # Generate nonces using mbedTLS CTR_DRBG
    tb_ctx = MbedTLSCtx(seed=b"VECTOR_HANDSHAKE_NONCES")
    nonce_a = tb_ctx.random_bytes(8)
    nonce_b = tb_ctx.random_bytes(8)
    tb_ctx.close()

    # Pre-compute MACs using mbedTLS HMAC-SHA256
    # Msg 2: MAC_B = HMAC-SHA256(session_key, ID_B || nonce_B)
    msg2_mac = hmac_sha256(session_key_bytes, b"ID_B" + nonce_b)
    # Msg 3: MAC_A = HMAC-SHA256(session_key, ID_A || nonce_A)
    msg3_mac = hmac_sha256(session_key_bytes, b"ID_A" + nonce_a)

    # Format MACs for display (first 8 hex chars)
    msg2_mac_str = msg2_mac[:4].hex()
    msg3_mac_str = msg3_mac[:4].hex()

    # -------------------------------------------------------------------
    # Figure setup — focused on just 2 nodes
    # -------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(0, 1000)
    ax.set_ylim(-250, 250)
    ax.set_aspect("equal")
    ax.axis("off")

    title = ax.text(
        0.5, 0.965,
        "VECTOR — TurboBlom 3-Message Authentication",
        transform=ax.transAxes, ha="center", va="top",
        color=TEXT_COLOR, fontsize=16, fontweight="bold",
    )

    phase_text = ax.text(
        0.5, 0.82, "", transform=ax.transAxes,
        ha="center", va="top", color=TEXT_COLOR, fontsize=13,
        fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#2a2a4a", alpha=0.95, edgecolor=TEXT_COLOR),
    )

    stats_text = None

    # --- Node A (center-left) ---
    node_a_scatter = ax.scatter(
        [NODE_A_POS[0]], [NODE_A_POS[1]],
        s=1000, c=NODE_INIT_COLOR, edgecolors="white", linewidths=3,
        zorder=6, marker="o",
    )
    node_a_label = ax.text(
        NODE_A_POS[0], NODE_A_POS[1] + 55, "A",
        ha="center", va="bottom", color=TEXT_COLOR, fontsize=18,
        fontweight="bold", zorder=7, alpha=1.0,
    )

    # --- Node B (center-right) ---
    node_b_scatter = ax.scatter(
        [NODE_B_POS[0]], [NODE_B_POS[1]],
        s=1000, c=NODE_INIT_COLOR, edgecolors="white", linewidths=3,
        zorder=6, marker="o",
    )
    node_b_label = ax.text(
        NODE_B_POS[0], NODE_B_POS[1] + 55, "B",
        ha="center", va="bottom", color=TEXT_COLOR, fontsize=18,
        fontweight="bold", zorder=7, alpha=1.0,
    )

    # --- Handshake arrows (3, one active at a time) ---
    handshake_arrows = []
    for _ in range(3):
        arr = FancyArrowPatch(
            (0, 0), (0, 0),
            arrowstyle="->", mutation_scale=20, color=ARROW_COLOR,
            linewidth=4, alpha=0.0, zorder=8,
        )
        ax.add_patch(arr)
        handshake_arrows.append(arr)

    # --- Message label (center) ---
    msg_label = ax.text(
        500, 60, "", ha="center", va="center",
        color=TEXT_COLOR, fontsize=12, fontweight="bold", alpha=0.0, zorder=9,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#2a2a4a", alpha=0.95, edgecolor=ARROW_COLOR),
    )

    # --- Authenticated link (solid green line) ---
    auth_link_line, = ax.plot(
        [], [], color=AUTH_LINK_COLOR, linewidth=5.0, alpha=0.0, zorder=5,
    )

    # State
    state = {"auth_link_drawn": False}

    def get_phase(frame):
        if frame <= PHASE_INIT[1]:
            return "init"
        if frame <= PHASE_PROVISION[1]:
            return "provision"
        if frame <= PHASE_HANDSHAKE[1]:
            return "handshake"
        return "authenticated"

    def update(frame):
        phase = get_phase(frame)

        phase_labels = {
            "init": "Phase 1: Nodes A & B — Initial State",
            "provision": "Phase 2: TurboBlom Secret Provisioning",
            "handshake": "Phase 3: 3-Message Authentication Handshake",
            "authenticated": "Phase 4: Authenticated — Secure Link Established",
        }
        phase_text.set_text(phase_labels[phase])

        # ---- Node coloring ----
        if phase == "init":
            node_a_scatter.set_color(NODE_INIT_COLOR)
            node_b_scatter.set_color(NODE_INIT_COLOR)
            node_a_scatter.set_sizes([1000])
            node_b_scatter.set_sizes([1000])
        elif phase == "provision":
            node_a_scatter.set_color(NODE_PROV_COLOR)
            node_b_scatter.set_color(NODE_PROV_COLOR)
            node_a_scatter.set_sizes([1100])
            node_b_scatter.set_sizes([1100])
        elif phase == "handshake":
            node_a_scatter.set_color(NODE_A_COLOR)
            node_b_scatter.set_color(NODE_B_COLOR)
            node_a_scatter.set_sizes([1200])
            node_b_scatter.set_sizes([1200])
        else:  # authenticated
            node_a_scatter.set_color(NODE_AUTH_COLOR)
            node_b_scatter.set_color(NODE_AUTH_COLOR)
            node_a_scatter.set_sizes([1000])
            node_b_scatter.set_sizes([1000])

        # ---- Phase-specific animation ----
        if phase == "init":
            for arr in handshake_arrows:
                arr.set_alpha(0.0)
            msg_label.set_alpha(0.0)
            msg_label.set_text("")
            auth_link_line.set_alpha(0.0)
            state["auth_link_drawn"] = False

        elif phase == "provision":
            for arr in handshake_arrows:
                arr.set_alpha(0.0)
            msg_label.set_alpha(0.0)
            msg_label.set_text("")
            auth_link_line.set_alpha(0.0)
            state["auth_link_drawn"] = False

        elif phase == "handshake":
            hs_frame = frame - PHASE_HANDSHAKE[0]
            hs_duration = float(PHASE_HANDSHAKE[1] - PHASE_HANDSHAKE[0])
            msg_duration = hs_duration / 3.0

            messages = [
                (f"Msg 1: ID_A, nonce_A={nonce_a[:4].hex()}", NODE_A_POS, NODE_B_POS, MSG1_COLOR),
                (f"Msg 2: ID_B, nonce_B={nonce_b[:4].hex()}, MAC={msg2_mac_str}", NODE_B_POS, NODE_A_POS, MSG2_COLOR),
                (f"Msg 3: MAC={msg3_mac_str}", NODE_A_POS, NODE_B_POS, MSG3_COLOR),
            ]

            shown = False
            for i, (label, src, dst, col) in enumerate(messages):
                msg_start = i * msg_duration
                msg_end = (i + 1) * msg_duration
                if msg_start <= hs_frame < msg_end:
                    for j, arr in enumerate(handshake_arrows):
                        if j == i:
                            arr.set_color(col)
                            pulse = 0.4 + 0.6 * abs(math.sin(hs_frame * 0.8))
                            arr.set_alpha(pulse)
                            arr.set_positions(src, dst)
                        else:
                            arr.set_alpha(0.0)
                    msg_label.set_position(((src[0] + dst[0]) / 2.0, -200.0))
                    msg_label.set_text(label)
                    msg_label.set_color(col)
                    msg_label.set_alpha(1.0)
                    msg_label.get_bbox_patch().set_edgecolor(col)
                    shown = True
                    break
            if not shown:
                for arr in handshake_arrows:
                    arr.set_alpha(0.0)
                msg_label.set_alpha(0.0)
                msg_label.set_text("")

            auth_link_line.set_alpha(0.0)
            state["auth_link_drawn"] = False

        else:  # authenticated
            for arr in handshake_arrows:
                arr.set_alpha(0.0)
            msg_label.set_alpha(0.0)
            msg_label.set_text("")

            # Draw authenticated link once
            if not state["auth_link_drawn"]:
                auth_link_line.set_data([NODE_A_POS[0], NODE_B_POS[0]],
                                        [NODE_A_POS[1], NODE_B_POS[1]])
                auth_link_line.set_color(AUTH_LINK_COLOR)
                auth_link_line.set_alpha(0.95)
                state["auth_link_drawn"] = True

        artists = [
            node_a_scatter, node_b_scatter, node_a_label, node_b_label,
            msg_label, auth_link_line, phase_text,
        ] + handshake_arrows
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
