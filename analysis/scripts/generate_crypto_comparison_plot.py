#!/usr/bin/env python3
"""
generate_crypto_comparison_plot.py

Reads JSON benchmark results from crypto_benchmark.cpp and generates
comparison plots showing mbedTLS vs pure C++ cryptographic performance.

Output:
  analysis/plots/crypto_comparison_provisioning.png
  analysis/plots/crypto_comparison_derivation.png
  analysis/plots/crypto_comparison_handshake.png
  analysis/plots/crypto_comparison_all.png
"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE = os.path.join(SCRIPT_DIR, "crypto_benchmark_results.json")
PLOT_DIR = os.path.join(SCRIPT_DIR, "..", "plots")


def load_results(json_path):
    """Load benchmark results from JSON file."""
    with open(json_path, "r") as f:
        data = json.load(f)
    return data


def plot_provisioning(results, output_path):
    """Bar chart: provisioning time comparison."""
    nodes = [r["nodes"] for r in results]
    pure_cpp = [r["pure_cpp_prov_ms"] for r in results]
    mbedtls = [r["mbedtls_prov_ms"] for r in results]

    x = np.arange(len(nodes))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width / 2, pure_cpp, width, label="Pure C++", color="#58a6ff", alpha=0.8)
    bars2 = ax.bar(x + width / 2, mbedtls, width, label="mbedTLS", color="#f0c808", alpha=0.8)

    ax.set_xlabel("Number of Nodes", fontsize=11)
    ax.set_ylabel("Time (ms)", fontsize=11)
    ax.set_title("Key Provisioning Time: Pure C++ vs mbedTLS", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(nodes)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    ax.set_yscale("log")

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.4f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_derivation(results, output_path):
    """Bar chart: key derivation time comparison."""
    nodes = [r["nodes"] for r in results]
    pure_cpp = [r["pure_cpp_deriv_ms"] for r in results]
    mbedtls = [r["mbedtls_deriv_ms"] for r in results]

    x = np.arange(len(nodes))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width / 2, pure_cpp, width, label="Pure C++", color="#58a6ff", alpha=0.8)
    bars2 = ax.bar(x + width / 2, mbedtls, width, label="mbedTLS", color="#f0c808", alpha=0.8)

    ax.set_xlabel("Number of Nodes", fontsize=11)
    ax.set_ylabel("Time (ms)", fontsize=11)
    ax.set_title("Pairwise Key Derivation Time: Pure C++ vs mbedTLS", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(nodes)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    ax.set_yscale("log")

    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.4f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_handshake(results, output_path):
    """Bar chart: handshake auth time comparison."""
    nodes = [r["nodes"] for r in results]
    pure_cpp = [r["pure_cpp_handshake_ms"] for r in results]
    mbedtls = [r["mbedtls_handshake_ms"] for r in results]

    x = np.arange(len(nodes))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width / 2, pure_cpp, width, label="Pure C++", color="#58a6ff", alpha=0.8)
    bars2 = ax.bar(x + width / 2, mbedtls, width, label="mbedTLS", color="#f0c808", alpha=0.8)

    ax.set_xlabel("Number of Nodes", fontsize=11)
    ax.set_ylabel("Time (ms)", fontsize=11)
    ax.set_title("Handshake Auth Time: Pure C++ vs mbedTLS", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(nodes)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f"{height:.4f}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def plot_combined(results, output_path):
    """Combined plot: all metrics side by side."""
    nodes = [r["nodes"] for r in results]
    metrics = ["prov_ms", "deriv_ms", "handshake_ms"]
    metric_labels = ["Provisioning", "Key Derivation", "Handshake Auth"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    for idx, (metric, label) in enumerate(zip(metrics, metric_labels)):
        pure_cpp = [r[f"pure_cpp_{metric}"] for r in results]
        mbedtls = [r[f"mbedtls_{metric}"] for r in results]

        x = np.arange(len(nodes))
        width = 0.35

        ax = axes[idx]
        bars1 = ax.bar(x - width / 2, pure_cpp, width, label="Pure C++", color="#58a6ff", alpha=0.8)
        bars2 = ax.bar(x + width / 2, mbedtls, width, label="mbedTLS", color="#f0c808", alpha=0.8)

        ax.set_xlabel("Nodes", fontsize=9)
        ax.set_ylabel("Time (ms)", fontsize=9)
        ax.set_title(label, fontsize=10, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(nodes)
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)
        ax.set_yscale("log")

    plt.suptitle("mbedTLS vs Pure C++ Crypto Performance Comparison", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()


def main():
    # Try to load existing results, or run benchmark
    results_file = os.path.join(SCRIPT_DIR, "crypto_benchmark_results.json")

    if os.path.exists(results_file):
        print(f"Loading existing results from {results_file}")
        with open(results_file, "r") as f:
            data = json.load(f)
    else:
        print("No results file found. Please run crypto_benchmark first.")
        print("  python3 analysis/scripts/crypto_benchmark.py --nodes 30,100,500 --trials 3")
        return

    results = data["results"]
    config = data["config"]

    os.makedirs(PLOT_DIR, exist_ok=True)

    # Generate individual plots
    plot_provisioning(results, os.path.join(PLOT_DIR, "crypto_comparison_provisioning.png"))
    plot_derivation(results, os.path.join(PLOT_DIR, "crypto_comparison_derivation.png"))
    plot_handshake(results, os.path.join(PLOT_DIR, "crypto_comparison_handshake.png"))

    # Generate combined plot
    plot_combined(results, os.path.join(PLOT_DIR, "crypto_comparison_all.png"))

    print("Comparison plots generated:")
    print(f"  {os.path.join(PLOT_DIR, 'crypto_comparison_provisioning.png')}")
    print(f"  {os.path.join(PLOT_DIR, 'crypto_comparison_derivation.png')}")
    print(f"  {os.path.join(PLOT_DIR, 'crypto_comparison_handshake.png')}")
    print(f"  {os.path.join(PLOT_DIR, 'crypto_comparison_all.png')}")


if __name__ == "__main__":
    main()
