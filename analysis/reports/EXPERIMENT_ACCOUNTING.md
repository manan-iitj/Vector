# Experiment Accounting — VECTOR Comparative Analysis

**Date:** 2026-11-08  
**Status:** Verified — 4,140 runs completed successfully

---

## 1. Complete Experiment Accounting

Verified by inspecting all raw CSV files in `analysis/experiments/raw_data/*/raw.csv`.

| Experiment | Algorithms/Baselines | Network Sizes | Seeds | Additional Dimension | Runs per Config | Total Runs |
|------------|---------------------|---------------|-------|---------------------|-----------------|------------|
| Clustering | VECTOR_HEED, LEACH, RANDOM_DIRECT (3) | 10, 20, 30, 50, 75, 100 (6) | 30 | — | 30 | **540** |
| Routing | debruijn, ring, chordal_ring, random (4) | 10, 20, 30, 50, 75, 100 (6) | 30 | — | 30 | **720** |
| Security | TurboBlom, PairwisePreSharedKeys (2) | 10, 20, 30, 50, 75, 100 (6) | 30 | — | 30 | **360** |
| Election | VECTOR_BatteryAware, MaxConsensus_Unaware, Random (3) | 10, 20, 30, 50, 75, 100 (6) | 30 | — | 30 | **540** |
| Resilience | debruijn (1) | 10, 20, 30, 50, 75, 100 (6) | 30 | Failure: 0.0–0.5 (6) | 30 | **1,080** |
| Ablation | VECTOR_Full, No_Energy, No_Clustering, No_Topo, No_Turbo (5) | 10, 20, 30, 50, 75, 100 (6) | 30 | — | 30 | **900** |
| **Total** | | | | | | **4,140** |

---

## 2. Verified Run Counts

| Experiment | Data Rows | Expected | Match |
|------------|-----------|----------|-------|
| clustering | 540 | 540 | ✓ |
| routing | 720 | 720 | ✓ |
| security | 360 | 360 | ✓ |
| election | 540 | 540 | ✓ |
| resilience | 1,080 | 1,080 | ✓ |
| ablation | 900 | 900 | ✓ |
| **Grand Total** | **4,140** | **4,140** | **✓** |

---

## 3. Run Definition

One run = a single `Simulator` execution with:
- Specific algorithm/topology
- Specific network size (10–100 nodes)
- Specific random seed (0–29)
- For resilience: specific failure fraction (0.0–0.5)
- Full simulation over 1000 s in 10 s intervals
- All metrics recorded at end of run

Each run produces one row with:
- Run ID (UUID), experiment, algorithm, topology, seed
- Configuration parameters
- All measured metrics (PDR, latency, energy, fairness, etc.)

---

## 3. Quality Assurance

- **Zero failed runs:** All 4,140 rows have `status = "completed"`
- **Zero skipped runs:** Every configured combination executed
- **Deterministic results:** Identical numerics across reruns for clustering, routing, resilience, ablation
- **Statistical robustness:** 30 seeds × 6 sizes × multiple baselines per experiment

---

## 4. Reproduction Verification

```bash
# Full pipeline verification
cd VECTOR
python3 analysis/scripts/run_experiments.py --all --seeds 30
python3 analysis/scripts/process_results.py
python3 analysis/scripts/statistical_analysis.py
python3 analysis/scripts/generate_plots.py
```

**Result:** All 4,140 runs reproduce byte-identical numeric measurements
(clustering, routing, resilience, ablation). Security/election show timing
variations due to `time.perf_counter()` — numeric metrics are identical.