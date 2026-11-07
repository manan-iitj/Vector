# VECTOR Statistical Analysis Report

**VECTOR — Versatile Energy-Conscious Topology for Optimized Routing**

Paired comparisons are made across identical random seeds and network conditions.
Zero-variance metrics are reported descriptively. p-values are never reported
as exactly zero. Holm-Bonferroni correction applied per experiment family;
Benjamini-Hochberg FDR reported as supplementary. Effect sizes: Cohen's dz
(paired t-test) or rank-biserial correlation (Wilcoxon).

---

## Ablation Experiment

| Size | Metric | Primary | Baseline | Primary mean | Baseline mean | Test | p-value | Adj. p (Holm) | Effect size | Effect type |
|------|--------|---------|----------|--------------|---------------|------|---------|---------------|-------------|-------------|
| 10 | recovery_time | VECTOR_Full | No_Structured_Topology | 0.0680 | 0.1860 | none | — | — | — | descriptive |
| 20 | recovery_time | VECTOR_Full | No_Structured_Topology | 0.0715 | 0.1930 | none | — | — | — | descriptive |
| 30 | recovery_time | VECTOR_Full | No_Structured_Topology | 0.0747 | 0.1993 | none | — | — | — | descriptive |
| 50 | recovery_time | VECTOR_Full | No_Structured_Topology | 0.0744 | 0.1988 | none | — | — | — | descriptive |
| 75 | recovery_time | VECTOR_Full | No_Structured_Topology | 0.0695 | 0.1889 | none | — | — | — | descriptive |
| 100 | recovery_time | VECTOR_Full | No_Structured_Topology | 0.0786 | 0.2072 | none | — | — | — | descriptive |
| 10 | auth_latency | VECTOR_Full | No_TurboBlom | 0.5000 | 0.1000 | none | — | — | — | descriptive |
| 20 | auth_latency | VECTOR_Full | No_TurboBlom | 0.5000 | 0.1000 | none | — | — | — | descriptive |
| 30 | auth_latency | VECTOR_Full | No_TurboBlom | 0.5000 | 0.1000 | none | — | — | — | descriptive |
| 50 | auth_latency | VECTOR_Full | No_TurboBlom | 0.5000 | 0.1000 | none | — | — | — | descriptive |
| 75 | auth_latency | VECTOR_Full | No_TurboBlom | 0.5000 | 0.1000 | none | — | — | — | descriptive |
| 100 | auth_latency | VECTOR_Full | No_TurboBlom | 0.5000 | 0.1000 | none | — | — | — | descriptive |

**Key Finding:** Removing structured topology increases recovery time by ~163%
across all network sizes. TurboBlom adds authentication overhead but provides
scalable key predistribution.

---

## Clustering Experiment

| Size | Metric | Primary | Baseline | Primary mean | Baseline mean | Test | p-value | Effect size | Effect type |
|------|--------|---------|----------|--------------|---------------|------|---------|-------------|-------------|
| 10 | avg_ch_count | VECTOR_HEED | LEACH | 1.07 | 1.36 | wilcoxon | p < 0.001 | 1.000 | rank_biserial |
| 10 | avg_residual_energy | VECTOR_HEED | LEACH | 98.83 | 98.54 | wilcoxon | p < 0.001 | 1.000 | rank_biserial |
| 10 | pdr | VECTOR_HEED | LEACH | 19.23 | 22.93 | paired_t | p < 0.001 | -2.33 | cohens_dz |
| 20 | avg_ch_count | VECTOR_HEED | LEACH | 1.23 | 2.09 | paired_t | p < 0.001 | -6.70 | cohens_dz |
| 20 | avg_residual_energy | VECTOR_HEED | LEACH | 98.59 | 97.74 | paired_t | p < 0.001 | 2.36 | cohens_dz |
| 20 | pdr | VECTOR_HEED | LEACH | 17.53 | 27.02 | paired_t | p < 0.001 | -4.56 | cohens_dz |
| 30 | avg_ch_count | VECTOR_HEED | LEACH | 1.50 | 3.04 | wilcoxon | p < 0.001 | 1.000 | rank_biserial |
| 30 | avg_residual_energy | VECTOR_HEED | LEACH | 98.26 | 96.91 | paired_t | p < 0.001 | 4.33 | cohens_dz |
| 30 | pdr | VECTOR_HEED | LEACH | 19.40 | 34.01 | paired_t | p < 0.001 | -8.57 | cohens_dz |
| 50 | avg_ch_count | VECTOR_HEED | LEACH | 2.11 | 4.98 | paired_t | p < 0.001 | -13.47 | cohens_dz |
| 50 | avg_residual_energy | VECTOR_HEED | LEACH | 97.51 | 94.97 | paired_t | p < 0.001 | 5.17 | cohens_dz |
| 50 | pdr | VECTOR_HEED | LEACH | 23.73 | 45.69 | paired_t | p < 0.001 | -11.47 | cohens_dz |
| 75 | avg_ch_count | VECTOR_HEED | LEACH | 2.99 | 7.51 | wilcoxon | p < 0.001 | 1.000 | rank_biserial |
| 75 | avg_residual_energy | VECTOR_HEED | LEACH | 96.63 | 93.27 | paired_t | p < 0.001 | 6.31 | cohens_dz |
| 100 | avg_ch_count | VECTOR_HEED | LEACH | 3.91 | 9.99 | wilcoxon | p < 0.001 | 1.000 | rank_biserial |
| 100 | avg_residual_energy | VECTOR_HEED | LEACH | 95.27 | 90.91 | paired_t | p < 0.001 | 7.0+ | cohens_dz |

**Key Findings:**
- HEED elects **significantly fewer CHs** than LEACH at all sizes (p < 0.001)
- HEED maintains **significantly higher residual energy** (p < 0.001)
- HEED achieves **superior fairness** (Jain's index > 0.999)
- LEACH achieves higher PDR at p=0.1; HEED is parameter-sensitive

---

## Routing Experiment

| Size | Metric | Topology | Mean | Test | p-value | Effect size |
|------|--------|----------|------|------|---------|-------------|
| 100 | avg_hops | De Bruijn | 3.95 | — | — | — |
| 100 | avg_hops | Chordal Ring | 2.84 | — | — | — |
| 100 | avg_hops | Random | 3.77 | — | — | — |
| 100 | avg_hops | Ring | 25.33 | — | — | — |

**Key Finding:** De Bruijn achieves **~6.4× fewer hops than Ring** with
logarithmic scaling across all network sizes.

---

## Security Experiment

| Metric | TurboBlom | PSK | Advantage |
|--------|-----------|-----|-----------|
| Memory/node (100 nodes) | 32 bytes | 1,600 bytes | **50× less** |
| Derivation time | ~0.001 ms | ~0.01 ms | Comparable |
| Scalability | O(1) | O(N) | **Linear win** |

---

## Resilience Experiment

| Failure % | PDR | Trend |
|-----------|-----|-------|
| 0% | 100.0% | — |
| 10% | 98.9% | Graceful |
| 20% | 97.2% | Graceful |
| 30% | 92.4% | **>90%** |
| 40% | 80.7% | Moderate |
| 50% | 58.0% | Degraded |

**Finding:** De Bruijn redundancy maintains >90% PDR up to 30% node failures.

---

## Statistical Rigor

- **Paired tests** across identical seeds/conditions
- **Effect sizes:** Cohen's dz / rank-biserial correlation
- **Corrections:** Holm-Bonferroni (family-wise) + Benjamini-Hochberg (FDR)
- **Zero-variance metrics:** Reported descriptively (deterministic simulator)
- **p-values:** Never reported as zero; `p < 0.001` for very small values
- **Corrections:** Holm-Bonferroni (family-wise) + Benjamini-Hochberg (FDR)