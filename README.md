# VECTOR — Versatile Energy-Conscious Topology for Optimized Routing

**VECTOR** is a distributed wireless network architecture for energy-constrained, resource-constrained networks (drone swarms, IoT, sensor networks). It combines **HEED** (Hybrid Energy-Efficient Distributed clustering) for energy-aware cluster-head selection with **De Bruijn graph-based structured communication** for efficient routing, discovery, and recovery.

---

## Architecture Overview

```
VECTOR/
├── CMakeLists.txt          # CMake build configuration
├── README.md               # This file
├── config/                 # YAML configuration files
│   ├── network_config.yaml
│   ├── security_config.yaml
│   └── simulation_config.yaml
├── include/                # C++ headers
│   ├── clustering/         # HEED, LEACH
│   ├── election/           # Leader election
│   ├── energy/             # Energy model
│   ├── joining/            # Node joining protocol
│   ├── metrics/            # Metrics collector
│   ├── network/            # Node, network manager
│   ├── recovery/           # SEARCH link recovery
│   ├── security/           # TurboBlom, authentication, crypto
│   ├── simulation/         # VectorSimulation
│   └── topology/           # De Bruijn, chordal-ring, routing engine
├── src/                    # C++ source (matching include structure)
├── tests/                  # C++ unit tests
├── analysis/               # Python simulation, experiments, analysis
│   ├── scripts/            # Python experiment scripts
│   │   ├── sim_engine.py       # Discrete-event simulator
│   │   ├── run_experiments.py  # Experiment runner
│   │   ├── process_results.py  # CSV aggregation
│   │   ├── generate_plots.py   # Plot generation (PNG)
│   │   └── statistical_analysis.py  # Statistical analysis
│   ├── experiments/
│   │   └── processed_data/     # Aggregated CSVs
│   ├── plots/                  # 7 figures (PNG 300 DPI)
│   └── reports/                # PERFORMANCE_ANALYSIS.md, STATISTICAL_ANALYSIS.md,
│                                 # EXPERIMENT_ACCOUNTING.md, REPRODUCIBILITY_REPORT.md
```

---

## Core Innovations

### 🎯 HEED Clustering — Energy-Aware Cluster Head Selection

HEED (Hybrid Energy-Efficient Distributed clustering) implements probabilistic,
distributed cluster-head selection where each node computes a cluster-head
probability based on its residual energy and proximity to neighbors:

```
P_CH = p * (E_residual / E_max)^α * (distance_factor)^β
```

Nodes exceeding the threshold become cluster heads (CHs). Non-CH nodes associate
with the nearest reachable CH. CHs aggregate and forward traffic, reducing
overall network energy consumption.

**Implementation:** `include/clustering/heed.h`, `src/clustering/heed.cpp`

### 🌐 De Bruijn Structured Topology — Logarithmic-Diameter Routing

Nodes are mapped 1:1 to vertices of a De Bruijn-like graph (out-degree 2,
constructed via mod-n index wrapping: node i connects to 2i mod n and 2i+1 mod n).
The graph provides short logical paths with diameter ~log₂ n. Routing uses BFS
shortest-path over the alive subgraph, delivering **O(log n) hop scaling** vs
O(n) for ring topologies.

**Verified by:** `tests/vector_debruijn_test` (out-degree = 2, routing validity,
hop-count bound → PASSED)

**Implementation:** `include/topology/topology_manager.h`,
                  `src/topology/debruijn_topology.cpp`

### 🔐 TurboBlom Key Predistribution — Scalable Security

TurboBlom implements a Blom symmetric key predistribution scheme providing:
- **Pairwise key agreement** (K_AB = K_BA derived independently)
- **t-resilience** (tolerates up to t compromised nodes)
- **No key clustering** (compromise of one key doesn't reveal others)
- **Constant memory overhead** (32 bytes/node regardless of network size)

**Implementation:** `include/security/turboblom.h`, `src/security/turboblom.cpp`

### 🔒 Pure-C++ Cryptography — Zero External Dependencies

Complete cryptographic suite implemented in pure C++20:
- **SHA-256** (FIPS 180-4 compliant)
- **HMAC-SHA256** (RFC 2104)
- **HKDF-like key derivation**
- **Secure random** (std::random_device + mt19937_64)
- **Constant-time comparison** (timing side-channel resistant)
- **Secure key cleanup** (memory zeroing)

Optional mbedTLS backend available for hardware-accelerated SHA-256/HMAC.

---

## Dual Simulation Framework

### 🐍 Python Discrete-Event Simulator (Primary)

Full-featured discrete-event simulator (`analysis/scripts/sim_engine.py`)
reimplementing VECTOR components with baseline comparisons:

| Feature | Implementation |
|---------|----------------|
| HEED Clustering | Energy-aware CH selection + nearest-CH association |
| LEACH Baseline | Probabilistic CH selection (p=0.1) |
| Topologies | De Bruijn, Ring, Chordal Ring, Random Geometric |
| Radio Model | E_elec = 50 nJ/bit, E_amp = 100 pJ/bit/m² |
| Traffic | 1 packet/node/round, 1000 bits |
| Baselines | LEACH, Ring, Chordal Ring, Random, Direct |

### 📦 ns-3 Packet-Level Module (Optional)

Optional ns-3 module (`src/vector/`) for packet-level validation:
- All-pairs routing (each source → 5 random destinations)
- De Bruijn, Chordal Ring, Ring topologies
- JSON metrics output for cross-simulator comparison
- Built with `-DVECTOR_USE_NS3=ON` (requires ns-3 3.49)

---

## Experimental Results — 4,140 Reproducible Runs

| Parameter | Value |
|-----------|-------|
| Network sizes | 10, 20, 30, 50, 75, 100 nodes |
| Seeds per config | 30 (seeds 0–29) |
| Total runs | **4,140** |
| Experiments | 6 (clustering, routing, security, election, resilience, ablation) |

### Key Findings

#### 📊 Clustering — HEED vs LEACH
- **Residual Energy (100 nodes):** HEED 95.3 J vs LEACH 90.9 J
- **Cluster Heads (100 nodes):** HEED ~4 (3.9%) vs LEACH ~10 (10%)
- **Energy per Delivered Packet:** HEED 0.131 J vs LEACH 0.136 J
- **Fairness (Jain's Index):** HEED 0.999 vs LEACH 0.994

#### 🌐 Routing — De Bruijn vs Structured Topologies
| Topology | Latency @100 | Hops @100 | Scaling |
|----------|-------------|-----------|---------|
| **De Bruijn** | **0.040 s** | **3.95** | **O(log n)** |
| Chordal Ring | 0.029 s | 2.84 | O(√n) |
| Random Geometric | 0.039 s | 3.77 | Density-dependent |
| Ring | 0.255 s | 25.4 | O(n) |

**Key Result:** De Bruijn achieves **~6.4× fewer hops than Ring** at 100 nodes,
with logarithmic scaling maintained across all network sizes.

#### 🛡️ Security — TurboBlom vs Pre-Shared Keys
- **Per-node memory:** TurboBlom 32 bytes (constant) vs PSK 1,600 bytes (scales with N)
- **Derivation time:** Sub-millisecond for both
- **Scalability:** TurboBlom memory advantage grows linearly with network size

#### 🔄 Resilience — Graceful Degradation
- PDR maintained >90% up to 30% node failures
- 58% PDR at 50% node failure
- Graceful degradation characteristic of De Bruijn redundancy

#### 🔬 Ablation Study — Component Impact
- **Structured topology** is the largest contributor to fast recovery (+163% recovery time without De Bruijn)
- **TurboBlom** provides constant memory at modest auth overhead
- **Clustering** reduces relay overhead but parameter-sensitive

---

## Generated Visualizations (7 Publication-Quality Plots)

All plots in `analysis/plots/` (300 DPI PNG):

| Plot | Insight |
|------|---------|
| `crypto_comparison_provisioning.png` | Key provisioning: Pure C++ vs mbedTLS |
| `crypto_comparison_derivation.png` | **10⁴× faster** Pure C++ derivation |
| `crypto_comparison_handshake.png` | Handshake authentication comparison |
| `crypto_comparison_all.png` | Combined crypto performance |
| `ns3_topology_comparison.png` | De Bruijn vs Chordal vs Ring (3 metrics) |
| `ns3_vs_python_debruijn_comparison.png` | Cross-simulator De Bruijn validation |
| `clustering_heed_comparison.png` | HEED vs LEACH vs Direct (6-panel) |

---

## Build & Run

### Prerequisites
- C++20 compiler (Clang/GCC/MSVC)
- CMake 3.21+
- Python 3: `numpy`, `matplotlib`, `scipy`
- Optional: ns-3 3.49, mbedTLS

### Core Build
```bash
git clone <repository-url>
cd VECTOR
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc) vector vector_debruijn_test
./tests/vector_debruijn_test
# Expected: === All De Bruijn tests PASSED ===
```

### ns-3 Module (Optional)
```bash
cmake .. -DVECTOR_USE_NS3=ON -DCMAKE_BUILD_TYPE=Release
make -j$(nproc) vector_ns3_sim
./src/vector/vector_ns3_sim --numNodes=30 --topology=debruijn
```

### Python Experiments
```bash
cd ..
python3 analysis/scripts/run_experiments.py --all --seeds 30
python3 analysis/scripts/process_results.py
python3 analysis/scripts/generate_plots.py
python3 analysis/scripts/statistical_analysis.py
```

Outputs: `analysis/experiments/processed_data/*.csv`, `analysis/plots/*.png`, `analysis/reports/`

---

## Reports

| Report | Description |
|--------|-------------|
| `PERFORMANCE_ANALYSIS.md` | Detailed metrics, comparisons, findings |
| `STATISTICAL_ANALYSIS.md` | Paired tests, effect sizes, Holm-Bonferroni |
| `EXPERIMENT_ACCOUNTING.md` | 4,140 runs verified, zero failures |
| `REPRODUCIBILITY_REPORT.md` | Deterministic pipeline verified |

---

## Reproducibility

- **4,140 deterministic runs** (clustering 540, routing 720, security 360, election 540, resilience 1,080, ablation 900)
- **Zero failed runs** — all 4,140 completed successfully
- **Byte-identical numerics** across reruns (clustering, routing, resilience, ablation)
- **30 seeds × 6 sizes × multiple baselines** = statistically robust

---

## Citation

```bibtex
@misc{vector2026,
  author = {Manan Jain},
  title = {VECTOR: Versatile Energy-Conscious Topology for Optimized Routing},
  year = {2026},
  organization = {Home-based Development}
}
```

---

## License

MIT License — see `LICENSE` file for details.