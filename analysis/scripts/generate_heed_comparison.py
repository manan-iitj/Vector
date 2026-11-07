#!/usr/bin/env python3
"""
Generate HEED clustering comparison plots.
Compares VECTOR_HEED vs LEACH vs RANDOM_DIRECT.
"""

import csv
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PLOTS_DIR = os.path.join(PROJECT_ROOT, "analysis", "plots")
CLUSTERING_FILE = os.path.join(PROJECT_ROOT, "analysis", "experiments", "processed_data", "clustering", "aggregated.csv")

os.makedirs(PLOTS_DIR, exist_ok=True)


def parse_clustering_csv(csv_path):
    """Parse clustering aggregated CSV."""
    data = {}
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            algo = row['algorithm']
            size = int(row['num_nodes'])
            if algo not in data:
                data[algo] = {}
            data[algo][size] = {
                'avg_residual_energy': float(row['avg_residual_energy_mean']),
                'avg_residual_energy_std': float(row['avg_residual_energy_std']),
                'total_energy_consumed': float(row['total_energy_consumed_mean']),
                'total_energy_consumed_std': float(row['total_energy_consumed_std']),
                'pdr': float(row['pdr_mean']),
                'pdr_std': float(row['pdr_std']),
                'energy_per_delivered_packet': float(row['energy_per_delivered_packet_mean']),
                'energy_per_delivered_packet_std': float(row['energy_per_delivered_packet_std']),
                'jains_fairness': float(row['jains_fairness_mean']),
                'jains_fairness_std': float(row['jains_fairness_std']),
                'final_alive': float(row['final_alive_mean']),
                'final_alive_std': float(row['final_alive_std']),
                'avg_ch_count': float(row['avg_ch_count_mean']),
                'avg_ch_count_std': float(row['avg_ch_count_std']),
                'fnd': float(row['fnd_mean']),
                'fnd_std': float(row['fnd_std']),
                'hnd': float(row['hnd_mean']),
                'hnd_std': float(row['hnd_std']),
                'lnd': float(row['lnd_mean']),
                'lnd_std': float(row['lnd_std']),
            }
    return data


def plot_heed_comparison(data, output_dir):
    """Generate HEED clustering comparison plots."""
    algorithms = sorted(data.keys())
    sizes = sorted(set().union(*[data[a].keys() for a in algorithms]))

    print(f"Algorithms: {algorithms}")
    print(f"Sizes: {sizes}")

    colors = {"VECTOR_HEED": "#58a6ff", "LEACH": "#ff7b72", "RANDOM_DIRECT": "#3fb950"}
    labels = {"VECTOR_HEED": "VECTOR HEED", "LEACH": "LEACH (p=0.1)", "RANDOM_DIRECT": "Random/Direct"}

    # Create 2x3 panel plots
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle("HEED Clustering Comparison: VECTOR_HEED vs LEACH vs Random/Direct", 
                 fontsize=15, fontweight="bold", y=1.02)

    metrics = [
        ("avg_residual_energy", "Avg Residual Energy (J)", "Residual Energy (J)", False),
        ("pdr", "Packet Delivery Ratio (%)", "PDR (%)", False),
        ("energy_per_delivered_packet", "Energy per Delivered Packet (J)", "Energy/Packet (J)", True),
        ("jains_fairness", "Jain's Fairness Index", "Fairness", False),
        ("avg_ch_count", "Average Cluster Heads", "CH Count", False),
        ("total_energy_consumed", "Total Energy Consumed (J)", "Total Energy (J)", False),
    ]

    for idx, (metric, label, ylabel, log_y) in enumerate(metrics):
        ax = axes[idx // 3, idx % 3]

        for algo in algorithms:
            x_vals = []
            y_vals = []
            y_errs = []
            for size in sizes:
                if size in data.get(algo, {}):
                    x_vals.append(size)
                    y_vals.append(data[algo][size][metric])
                    y_errs.append(data[algo][size][f"{metric}_std"])

            if x_vals:
                # Handle infinite energy per packet for RANDOM_DIRECT
                if metric == "energy_per_delivered_packet":
                    y_vals = [v if np.isfinite(v) else None for v in y_vals]
                    valid = [(x, y, e) for x, y, e in zip(x_vals, y_vals, y_errs) if y is not None]
                    if not valid:
                        continue
                    x_vals, y_vals, y_errs = zip(*valid)
                    x_vals, y_vals, y_errs = list(x_vals), list(y_vals), list(y_errs)

                ax.errorbar(x_vals, y_vals, yerr=y_errs, fmt='o-', 
                           label=labels[algo],
                           linewidth=2.5, markersize=8, capsize=4,
                           color=colors[algo], alpha=0.9)

        ax.set_xlabel("Network Size (nodes)", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(label, fontsize=13, fontweight="bold")
        ax.legend(fontsize=9, loc='best')
        ax.grid(True, alpha=0.3, which='both')
        ax.set_xscale('log')
        ax.set_xticks([10, 20, 30, 50, 75, 100])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        
        if log_y:
            ax.set_yscale('log')
            ax.set_yticks([0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000])
            ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

    plt.tight_layout()
    png_path = os.path.join(output_dir, "clustering_heed_comparison.png")
    pdf_path = os.path.join(output_dir, "clustering_heed_comparison.pdf")
    plt.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.close()
    print(f"Saved {png_path}")
    print(f"Saved {pdf_path}")


def main():
    print("Loading clustering data...")
    data = parse_clustering_csv(CLUSTERING_FILE)
    for algo, sizes in data.items():
        print(f"  {algo}: {len(sizes)} sizes")
    
    print("Generating HEED comparison plots...")
    plot_heed_comparison(data, PLOTS_DIR)
    print("Done.")


if __name__ == "__main__":
    main()