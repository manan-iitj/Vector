#!/usr/bin/env python3
"""
VECTOR Comparative Analysis Plots
Generates PNG visualizations comparing VECTOR (debruijn+HEED+mbedTLS)
against baselines using ns-3 standalone simulator metrics.
"""
import json, os, glob
import numpy as np
import matplotlib.pyplot as plt

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "experiments", "results")
PLOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "plots")

os.makedirs(PLOTS_DIR, exist_ok=True)

# Style
plt.style.use('seaborn-v0_8')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['grid.alpha'] = 0.3

COLORS = {
    'VECTOR': '#1f77b4',      # blue
    'Baseline1': '#ff7f0e',   # orange
    'Baseline2': '#d62728',   # red
    'Baseline3': '#2ca02c',   # green
}

LABELS = {
    'VECTOR': 'VECTOR (De Bruijn+HEED+mbedTLS)',
    'Baseline1': 'Baseline 1 (Ring+LEACH)',
    'Baseline2': 'Baseline 2 (Chordal+LEACH)',
    'Baseline3': 'Baseline 3 (Random+Direct)',
}

def load_metrics(path):
    with open(path) as f:
        return json.load(f)

def load_all(prefix):
    """Load all metrics files matching prefix_*.json"""
    data = {}
    for f in sorted(glob.glob(os.path.join(RESULTS_DIR, f"{prefix}_*.json"))):
        m = load_metrics(f)
        n = m['nNodes']
        data[n] = m
    return dict(sorted(data.items()))

def extract_series(data_dict, key):
    """Extract (x, y) pairs from data dict"""
    xs = []
    ys = []
    for n, m in sorted(data_dict.items()):
        xs.append(n)
        ys.append(m.get(key, 0))
    return xs, ys

# Load all data
vector_data = load_all("vector")
b1_data = load_all("b1")
b2_data = load_all("b2")
b3_data = load_all("b3")

print("Data loaded successfully")
print(f"VECTOR: {len(vector_data)} configs, Baseline1: {len(b1_data)}, Baseline2: {len(b2_data)}, Baseline3: {len(b3_data)}")

# ============================================================
# Plot 1: PDR vs Network Size
# ============================================================
fig, ax = plt.subplots()
xs_v, ys_v = extract_series(vector_data, 'pdr')
xs_b1, ys_b1 = extract_series(b1_data, 'pdr')
xs_b2, ys_b2 = extract_series(b2_data, 'pdr')
xs_b3, ys_b3 = extract_series(b3_data, 'pdr')

ax.plot(xs_v, ys_v, 'o-', color=COLORS['VECTOR'], label=LABELS['VECTOR'], linewidth=2.5, markersize=8)
ax.plot(xs_b1, ys_b1, 's-', color=COLORS['Baseline1'], label=LABELS['Baseline1'], linewidth=2, markersize=7)
ax.plot(xs_b2, ys_b2, '^-', color=COLORS['Baseline2'], label=LABELS['Baseline2'], linewidth=2, markersize=7)
ax.plot(xs_b3, ys_b3, 'd-', color=COLORS['Baseline3'], label=LABELS['Baseline3'], linewidth=2, markersize=7)

ax.set_xlabel('Network Size (nodes)')
ax.set_ylabel('Packet Delivery Ratio (%)')
ax.set_title('PDR vs Network Size: VECTOR vs Baselines')
ax.legend(loc='best')
ax.grid(True, alpha=0.3)
ax.set_ylim(40, 105)
ax.set_xticks(xs_v)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'comp_pdr_vs_size.png'), dpi=300)
plt.close()

# ============================================================
# Plot 2: Latency vs Network Size
# ============================================================
fig, ax = plt.subplots()
xs_v, ys_v = extract_series(vector_data, 'avgLatency')
xs_b1, ys_b1 = extract_series(b1_data, 'avgLatency')
xs_b2, ys_b2 = extract_series(b2_data, 'avgLatency')
xs_b3, ys_b3 = extract_series(b3_data, 'avgLatency')

ax.plot(xs_v, ys_v, 'o-', color=COLORS['VECTOR'], label=LABELS['VECTOR'], linewidth=2.5, markersize=8)
ax.plot(xs_b1, ys_b1, 's-', color=COLORS['Baseline1'], label=LABELS['Baseline1'], linewidth=2, markersize=7)
ax.plot(xs_b2, ys_b2, '^-', color=COLORS['Baseline2'], label=LABELS['Baseline2'], linewidth=2, markersize=7)
ax.plot(xs_b3, ys_b3, 'd-', color=COLORS['Baseline3'], label=LABELS['Baseline3'], linewidth=2, markersize=7)

ax.set_xlabel('Network Size (nodes)')
ax.set_ylabel('Average Latency (s)')
ax.set_title('End-to-End Latency vs Network Size')
ax.legend(loc='best')
ax.grid(True, alpha=0.3)
ax.set_xticks(xs_v)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'comp_latency_vs_size.png'), dpi=300)
plt.close()

# ============================================================
# Plot 3: Energy per Delivered Packet vs Network Size
# ============================================================
fig, ax = plt.subplots()
xs_v, ys_v = extract_series(vector_data, 'energyPerDeliveredPacket')
xs_b1, ys_b1 = extract_series(b1_data, 'energyPerDeliveredPacket')
xs_b2, ys_b2 = extract_series(b2_data, 'energyPerDeliveredPacket')
xs_b3, ys_b3 = extract_series(b3_data, 'energyPerDeliveredPacket')

ax.plot(xs_v, ys_v, 'o-', color=COLORS['VECTOR'], label=LABELS['VECTOR'], linewidth=2.5, markersize=8)
ax.plot(xs_b1, ys_b1, 's-', color=COLORS['Baseline1'], label=LABELS['Baseline1'], linewidth=2, markersize=7)
ax.plot(xs_b2, ys_b2, '^-', color=COLORS['Baseline2'], label=LABELS['Baseline2'], linewidth=2, markersize=7)
ax.plot(xs_b3, ys_b3, 'd-', color=COLORS['Baseline3'], label=LABELS['Baseline3'], linewidth=2, markersize=7)

ax.set_xlabel('Network Size (nodes)')
ax.set_ylabel('Energy per Delivered Packet (J)')
ax.set_title('Energy Efficiency vs Network Size')
ax.legend(loc='best')
ax.grid(True, alpha=0.3)
ax.set_xticks(xs_v)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'comp_energy_per_packet.png'), dpi=300)
plt.close()



# ============================================================
# Plot 6: Key Derivation Time (mbedTLS vs pure-C++)
# ============================================================
fig, ax = plt.subplots()
xs_v, ys_v = extract_series(vector_data, 'keyDerivationTimeMs')
xs_b1, ys_b1 = extract_series(b1_data, 'keyDerivationTimeMs')
xs_b2, ys_b2 = extract_series(b2_data, 'keyDerivationTimeMs')
xs_b3, ys_b3 = extract_series(b3_data, 'keyDerivationTimeMs')

ax.plot(xs_v, ys_v, 'o-', color=COLORS['VECTOR'], label='mbedTLS (VECTOR)', linewidth=2.5, markersize=8)
ax.plot(xs_b1, ys_b1, 's-', color=COLORS['Baseline1'], label='Pure-C++ (Baseline)', linewidth=2, markersize=7)
ax.plot(xs_b2, ys_b2, '^-', color=COLORS['Baseline2'], label='Pure-C++ (Baseline)', linewidth=2, markersize=7, alpha=0.7)
ax.plot(xs_b3, ys_b3, 'd-', color=COLORS['Baseline3'], label='Pure-C++ (Baseline)', linewidth=2, markersize=7, alpha=0.7)

ax.set_xlabel('Network Size (nodes)')
ax.set_ylabel('Avg Key Derivation Time (ms)')
ax.set_title('Crypto Performance: mbedTLS vs Pure-C++')
ax.legend(loc='best')
ax.grid(True, alpha=0.3)
ax.set_xticks(xs_v)
ax.set_yscale('log')
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'comp_key_derivation_time.png'), dpi=300)
plt.close()



# ============================================================
# Plot 9: Avg Hop Count vs Network Size
# ============================================================
fig, ax = plt.subplots()
xs_v, ys_v = extract_series(vector_data, 'avgHopCount')
xs_b1, ys_b1 = extract_series(b1_data, 'avgHopCount')
xs_b2, ys_b2 = extract_series(b2_data, 'avgHopCount')
xs_b3, ys_b3 = extract_series(b3_data, 'avgHopCount')

ax.plot(xs_v, ys_v, 'o-', color=COLORS['VECTOR'], label=LABELS['VECTOR'], linewidth=2.5, markersize=8)
ax.plot(xs_b1, ys_b1, 's-', color=COLORS['Baseline1'], label=LABELS['Baseline1'], linewidth=2, markersize=7)
ax.plot(xs_b2, ys_b2, '^-', color=COLORS['Baseline2'], label=LABELS['Baseline2'], linewidth=2, markersize=7)
ax.plot(xs_b3, ys_b3, 'd-', color=COLORS['Baseline3'], label=LABELS['Baseline3'], linewidth=2, markersize=7)

ax.set_xlabel('Network Size (nodes)')
ax.set_ylabel('Average Hop Count')
ax.set_title('Routing Efficiency: Avg Hop Count vs Network Size')
ax.legend(loc='best')
ax.grid(True, alpha=0.3)
ax.set_xticks(xs_v)
plt.tight_layout()
plt.savefig(os.path.join(PLOTS_DIR, 'comp_hop_count.png'), dpi=300)
plt.close()


print(f"All 5 comparative plots saved to {PLOTS_DIR}/")
for f in sorted(os.listdir(PLOTS_DIR)):
    if f.endswith('.png'):
        print(f"  {f}")
