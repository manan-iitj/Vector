#!/usr/bin/env python3
"""VECTOR Statistical Analysis (corrected).

Reads per-seed raw results and performs paired statistical comparisons
between VECTOR variants and their baselines for every experiment family.

Statistical handling:
- Zero-variance metrics: test_status = "zero_variance", no fabricated p-value
  or effect size; observed difference reported descriptively only.
- p-values never reported as exactly zero; small values reported as p < 0.001
  when mathematically justified.
- Multiple-comparison correction: Holm-Bonferroni (primary, per experiment
  family) and Benjamini-Hochberg FDR (optional).
- Effect sizes: Cohen's dz for paired t-tests; rank-biserial correlation for
  Wilcoxon signed-rank tests. Undefined when variance is zero.
- Paired comparisons aligned by (seed, num_nodes, failure_fraction where
  applicable).
- Confidence intervals: paired CI for the mean difference (paired t-test) or
  bootstrap CI (Wilcoxon, fixed resampling seed).
"""

import csv
import os
import sys
from collections import defaultdict

import numpy as np
from scipy import stats

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "analysis")
RAW_DIR = os.path.join(ANALYSIS_DIR, "experiments", "raw_data")
REPORT_DIR = os.path.join(ANALYSIS_DIR, "reports")

# ---------------------------------------------------------------------------
# Experiment family definitions: which algorithms to compare against which.
# Each entry: experiment name -> list of (primary, baseline_label) pairs.
# ---------------------------------------------------------------------------
BASELINE_PAIRS = {
    "clustering": [
        ("VECTOR_HEED", "LEACH"),
        ("VECTOR_HEED", "RANDOM_DIRECT"),
        ("LEACH", "RANDOM_DIRECT"),
    ],
    "routing": [
        ("debruijn", "ring"),
        ("debruijn", "chordal_ring"),
        ("debruijn", "random"),
    ],
    "security": [
        ("TurboBlom", "PairwisePreSharedKeys"),
    ],
    "election": [
        ("VECTOR_BatteryAware", "MaxConsensus_Unaware"),
        ("VECTOR_BatteryAware", "Random"),
        ("MaxConsensus_Unaware", "Random"),
    ],
    "resilience": [
        # Resilience has a single topology (debruijn) across failure fractions;
        # comparisons are within-experiment across failure fractions, not
        # cross-baseline. Reported as descriptive trend only.
    ],
    "ablation": [
        ("VECTOR_Full", "No_Energy_Awareness"),
        ("VECTOR_Full", "No_Clustering"),
        ("VECTOR_Full", "No_Structured_Topology"),
        ("VECTOR_Full", "No_TurboBlom"),
    ],
}

# Metrics to skip for statistical testing when they are inherently constant
# or undefined for a given experiment.
SKIP_METRICS = {
    "resilience": {"failure_fraction", "avg_hops"},
    "ablation": {"memory_overhead"},
}

# Fixed (non-metric) columns in raw CSV
FIXED_COLS = {
    "run_id", "experiment", "algorithm", "topology", "seed", "num_nodes",
    "area_width", "area_height", "wireless_range", "simulation_time",
    "initial_energy", "packet_size_bits", "topology_type", "status",
    "error", "timestamp",
}


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def ci95(vals):
    """95% confidence interval for a sample mean (Student's t)."""
    n = len(vals)
    if n < 2:
        return (float("nan"), float("nan"))
    m = float(np.mean(vals))
    se = float(stats.sem(vals))
    if se == 0 or np.isnan(se):
        return (m, m)
    h = float(se * stats.t.ppf(0.975, n - 1))
    return (m - h, m + h)


def paired_ci95(diff):
    """95% CI for paired mean difference."""
    n = len(diff)
    if n < 2:
        return (float("nan"), float("nan"))
    md = float(np.mean(diff))
    sd = float(np.std(diff, ddof=1))
    if sd == 0 or np.isnan(sd):
        return (md, md)
    se = sd / np.sqrt(n)
    h = float(se * stats.t.ppf(0.975, n - 1))
    return (md - h, md + h)


def bootstrap_ci(diff, n_boot=2000, seed=42):
    """Bootstrap CI for paired median difference (fixed resampling seed)."""
    n = len(diff)
    if n < 2:
        return (float("nan"), float("nan"))
    rng = np.random.RandomState(seed)
    diff = np.asarray(diff)
    boots = []
    for _ in range(n_boot):
        sample = rng.choice(diff, size=n, replace=True)
        boots.append(np.median(sample))
    lo = float(np.percentile(boots, 2.5))
    hi = float(np.percentile(boots, 97.5))
    return (lo, hi)


def rank_biserial(w_stat, n):
    """Rank-biserial correlation for Wilcoxon signed-rank test."""
    if n < 2:
        return float("nan")
    return float(1.0 - (2.0 * w_stat) / (n * (n + 1)))


def cohens_dz(diff):
    """Cohen's dz for paired t-test (standardized mean difference)."""
    n = len(diff)
    if n < 2:
        return float("nan")
    sd = float(np.std(diff, ddof=1))
    if sd == 0 or np.isnan(sd):
        return float("nan")
    return float(np.mean(diff) / sd)


def is_normal(vals):
    """Shapiro-Wilk normality check. Returns False for n < 3."""
    if len(vals) < 3:
        return False
    _, p = stats.shapiro(vals)
    return bool(p > 0.05)


def paired_test(a, b):
    """Paired test across aligned seeds.

    Returns dict with:
      test, statistic, p_value, effect_size, effect_size_type, test_status,
      paired_diff_mean, paired_diff_ci, paired_diff_ci_bootstrap
    """
    n = min(len(a), len(b))
    result = {
        "test": None,
        "statistic": None,
        "p_value": None,
        "effect_size": None,
        "effect_size_type": None,
        "test_status": "invalid_input",
        "paired_diff_mean": None,
        "paired_diff_ci": None,
        "paired_diff_ci_bootstrap": None,
    }

    if n < 2:
        result["test_status"] = "insufficient_samples"
        return result

    a = np.asarray(a[:n], dtype=float)
    b = np.asarray(b[:n], dtype=float)
    diff = a - b

    result["paired_diff_mean"] = float(np.mean(diff))
    result["paired_diff_ci"] = paired_ci95(diff)
    result["paired_diff_ci_bootstrap"] = bootstrap_ci(diff)

    # Zero-variance handling (tolerance-based to catch floating-point noise)
    VAR_TOLERANCE = 1e-12
    var_a = float(np.var(a, ddof=1)) if n > 1 else 0.0
    var_b = float(np.var(b, ddof=1)) if n > 1 else 0.0
    var_diff = float(np.var(diff, ddof=1)) if n > 1 else 0.0

    if var_diff < VAR_TOLERANCE or var_a < VAR_TOLERANCE or var_b < VAR_TOLERANCE:
        # All paired differences effectively identical, or one group has
        # effectively zero variance. Conventional tests are not meaningful.
        if var_a < VAR_TOLERANCE and var_b < VAR_TOLERANCE:
            if abs(result["paired_diff_mean"]) < 1e-12:
                result["test_status"] = "zero_variance_identical"
            else:
                result["test_status"] = "zero_variance_different_constants"
        else:
            result["test_status"] = "zero_variance_one_group"
        # No conventional test; report descriptive difference only.
        result["test"] = "none"
        result["statistic"] = None
        result["p_value"] = None
        result["effect_size"] = None
        result["effect_size_type"] = None
        return result

    # Normality check
    normal_a = is_normal(a)
    normal_b = is_normal(b)

    if normal_a and normal_b:
        stat, p = stats.ttest_rel(a, b)
        result["test"] = "paired_t_test"
        result["statistic"] = float(stat)
        result["p_value"] = float(p)
        result["effect_size"] = cohens_dz(diff)
        result["effect_size_type"] = "cohens_dz"
        result["test_status"] = "valid"
    else:
        # Wilcoxon signed-rank
        try:
            stat, p = stats.wilcoxon(a, b)
        except ValueError:
            result["test_status"] = "test_not_applicable"
            return result
        result["test"] = "wilcoxon_signed_rank"
        result["statistic"] = float(stat)
        result["p_value"] = float(p)
        result["effect_size"] = rank_biserial(float(stat), n)
        result["effect_size_type"] = "rank_biserial"
        result["test_status"] = "valid"

    return result


def fmt_p(p):
    """Format p-value; never report exactly 0."""
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "undefined"
    if p == 0.0:
        return "p < 0.001"
    if p < 0.001:
        return f"p < 0.001 (raw: {p:.2e})"
    return f"{p:.4g}"


def holm_bonferroni(p_values, alpha=0.05):
    """Holm-Bonferroni step-down correction. Returns list of adjusted p-values."""
    n = len(p_values)
    if n == 0:
        return []
    # Sort by p-value ascending, keep original indices
    ordered = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n
    for rank, (orig_idx, p) in enumerate(ordered, start=1):
        # Holm: p_adj = min(1, (n - rank + 1) * p)
        adj = min(1.0, (n - rank + 1) * p)
        # Holm adjusted p-value must never be smaller than the raw p-value
        adj = max(adj, p)
        adjusted[orig_idx] = adj
    return adjusted


def benjamini_hochberg(p_values, alpha=0.05):
    """Benjamini-Hochberg FDR correction. Returns list of adjusted p-values."""
    n = len(p_values)
    if n == 0:
        return []
    ordered = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n
    for rank, (orig_idx, p) in enumerate(ordered, start=1):
        adj = min(1.0, (n / rank) * p)
        # BH adjusted p-value must never be smaller than the raw p-value
        adj = max(adj, p)
        adjusted[orig_idx] = adj
    # Enforce monotonicity (non-decreasing with rank)
    for i in range(n - 2, -1, -1):
        adjusted[i] = min(adjusted[i], adjusted[i + 1])
        adjusted[i] = max(adjusted[i], p_values[i])  # never below raw
    return adjusted


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_raw(experiment):
    path = os.path.join(RAW_DIR, experiment, "raw.csv")
    if not os.path.exists(path):
        return []
    return list(csv.DictReader(open(path)))


def numeric(vals):
    out = []
    for v in vals:
        if v in (None, ""):
            continue
        try:
            f = float(v)
        except (ValueError, TypeError):
            continue
        if np.isinf(f) or np.isnan(f):
            continue
        out.append(f)
    return out


def main() -> None:
    os.makedirs(REPORT_DIR, exist_ok=True)
    lines = []
    lines.append("# VECTOR Statistical Analysis Report (corrected)")
    lines.append("")
    lines.append("Paired comparisons are made across identical random seeds and network "
                 "conditions. Zero-variance metrics are reported descriptively "
                 "without fabricated p-values or effect sizes. p-values are never "
                 "reported as exactly zero. Holm-Bonferroni correction is applied "
                 "per experiment family; Benjamini-Hochberg FDR is reported as "
                 "supplementary. Effect sizes: Cohen's dz (paired t-test) or "
                 "rank-biserial correlation (Wilcoxon).")
    lines.append("")

    all_tests = []  # collect for multiple-comparison correction

    for exp in sorted(os.listdir(RAW_DIR)):
        exp_dir = os.path.join(RAW_DIR, exp)
        if not os.path.isdir(exp_dir):
            continue
        rows = load_raw(exp)
        if not rows:
            continue

        metric_cols = [c for c in rows[0].keys() if c not in FIXED_COLS]
        skip = SKIP_METRICS.get(exp, set())
        metric_cols = [m for m in metric_cols if m not in skip]

        # Build grouping key: (algorithm, num_nodes, failure_fraction_if_present)
        groups = defaultdict(list)
        for r in rows:
            ff = r.get("failure_fraction", "")
            key = (r["algorithm"], int(r["num_nodes"]), ff)
            groups[key].append(r)

        lines.append(f"## {exp.title()} Experiment")
        lines.append("")

        pairs = BASELINE_PAIRS.get(exp, [])
        if not pairs:
            lines.append("*No cross-baseline statistical comparisons defined for this experiment.*")
            lines.append("")
            continue

        lines.append("| Size | Failure Fraction | Metric | Primary | Baseline | Primary mean (n) | Baseline mean (n) | Test | p-value | Adj. p-value (Holm) | Adj. p-value (BH) | Effect size | Effect type | Test status | 95% CI (paired diff) |")
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

        # Collect all p-values for this experiment family (for Holm-Bonferroni)
        exp_tests = []

        sizes = sorted(set(k[1] for k in groups))

        for size in sizes:
            # Get unique failure fractions for this size
            ffs = sorted(set(k[2] for k in groups if k[1] == size))
            for ff in ffs:
                for primary_name, baseline_name in pairs:
                    pkey = (primary_name, size, ff)
                    bkey = (baseline_name, size, ff)
                    if pkey not in groups or bkey not in groups:
                        continue
                    prows = groups[pkey]
                    brows = groups[bkey]

                    # Align by seed
                    pmap = {int(r["seed"]): r for r in prows}
                    bmap = {int(r["seed"]): r for r in brows}
                    common_seeds = sorted(set(pmap) & set(bmap))
                    if not common_seeds:
                        continue

                    for m in sorted(metric_cols):
                        pv = numeric([pmap[s].get(m, "") for s in common_seeds])
                        bv = numeric([bmap[s].get(m, "") for s in common_seeds])
                        if not pv or not bv:
                            continue

                        res = paired_test(pv, bv)
                        pm = float(np.mean(pv))
                        bm = float(np.mean(bv))

                        test_status = res["test_status"]
                        p_val = res["p_value"]
                        eff = res["effect_size"]
                        eff_type = res["effect_size_type"]
                        test_name = res["test"]

                        # p-value formatting
                        if p_val is None or (isinstance(p_val, float) and np.isnan(p_val)):
                            p_str = "undefined"
                            p_sort = 1.0  # for sorting; undefined goes last
                        else:
                            p_str = fmt_p(p_val)
                            p_sort = p_val

                        ci = res["paired_diff_ci"]
                        ci_str = f"[{ci[0]:.4f}, {ci[1]:.4f}]" if not (np.isnan(ci[0]) or np.isnan(ci[1])) else "undefined"

                        eff_str = f"{eff:.4f}" if eff is not None and not np.isnan(eff) else "undefined"

                        ff_display = ff if ff else "—"

                        lines.append(
                            f"| {size} | {ff_display} | {m} | {primary_name} | {baseline_name} | "
                            f"{pm:.4f} ({len(pv)}) | {bm:.4f} ({len(bv)}) | {test_name} | "
                            f"{p_str} | | | {eff_str} | {eff_type} | {test_status} | {ci_str} |"
                        )

                        exp_tests.append({
                            "exp": exp, "size": size, "ff": ff, "metric": m,
                            "primary": primary_name, "baseline": baseline_name,
                            "p_value": p_sort, "p_str": p_str,
                        })

        # Apply Holm-Bonferroni and Benjamini-Hochberg per experiment
        p_vals = [t["p_value"] for t in exp_tests if isinstance(t["p_value"], float) and not np.isnan(t["p_value"])]
        # Need to map back: only tests with valid p-values get correction
        valid_test_indices = [i for i, t in enumerate(exp_tests) if isinstance(t["p_value"], float) and not np.isnan(t["p_value"])]
        if valid_test_indices:
            valid_p_vals = [exp_tests[i]["p_value"] for i in valid_test_indices]
            holm_adj = holm_bonferroni(valid_p_vals)
            bh_adj = benjamini_hochberg(valid_p_vals)
            for rank_i, orig_i in enumerate(valid_test_indices):
                exp_tests[orig_i]["holm_adj"] = holm_adj[rank_i]
                exp_tests[orig_i]["bh_adj"] = bh_adj[rank_i]

        # Rewrite lines with adjusted p-values (we stored placeholders "| | |")
        # Simpler: regenerate the table rows with corrections. Rebuild table.
        # (The placeholder approach above left empty adj columns; we now fill them.)
        # Re-emit the experiment section with corrections applied.
        # To avoid complexity, we store rows and re-emit after correction.
        lines.pop()  # remove trailing blank
        lines.pop()  # remove last header-ish line if needed

        # Actually, let's restructure: collect rows first, then apply corrections,
        # then emit the full table. Rebuild the experiment section from scratch.

    # The above inline approach is getting complex; rebuild cleanly below.
    # Rewrite the entire file output with corrected two-pass approach.
    lines2 = []
    lines2.append("# VECTOR Statistical Analysis Report (corrected)")
    lines2.append("")
    lines2.append("Paired comparisons are made across identical random seeds and network "
                  "conditions. Zero-variance metrics are reported descriptively "
                  "without fabricated p-values or effect sizes. p-values are never "
                  "reported as exactly zero. Holm-Bonferroni correction is applied "
                 "per experiment family; Benjamini-Hochberg FDR is reported as "
                 "supplementary. Effect sizes: Cohen's dz (paired t-test) or "
                 "rank-biserial correlation (Wilcoxon).")
    lines2.append("")

    for exp in sorted(os.listdir(RAW_DIR)):
        exp_dir = os.path.join(RAW_DIR, exp)
        if not os.path.isdir(exp_dir):
            continue
        rows = load_raw(exp)
        if not rows:
            continue

        metric_cols = [c for c in rows[0].keys() if c not in FIXED_COLS]
        skip = SKIP_METRICS.get(exp, set())
        metric_cols = [m for m in metric_cols if m not in skip]

        groups = defaultdict(list)
        for r in rows:
            ff = r.get("failure_fraction", "")
            key = (r["algorithm"], int(r["num_nodes"]), ff)
            groups[key].append(r)

        lines2.append(f"## {exp.title()} Experiment")
        lines2.append("")

        pairs = BASELINE_PAIRS.get(exp, [])
        if not pairs:
            lines2.append("*No cross-baseline statistical comparisons defined for this experiment.*")
            lines2.append("")
            continue

        lines2.append("| Size | Failure Fraction | Metric | Primary | Baseline | Primary mean (n) | Baseline mean (n) | Test | p-value | Adj. p-value (Holm) | Adj. p-value (BH) | Effect size | Effect type | Test status | 95% CI (paired diff) |")
        lines2.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

        table_rows = []
        sizes = sorted(set(k[1] for k in groups))
        for size in sizes:
            ffs = sorted(set(k[2] for k in groups if k[1] == size))
            for ff in ffs:
                for primary_name, baseline_name in pairs:
                    pkey = (primary_name, size, ff)
                    bkey = (baseline_name, size, ff)
                    if pkey not in groups or bkey not in groups:
                        continue
                    prows = groups[pkey]
                    brows = groups[bkey]
                    pmap = {int(r["seed"]): r for r in prows}
                    bmap = {int(r["seed"]): r for r in brows}
                    common_seeds = sorted(set(pmap) & set(bmap))
                    if not common_seeds:
                        continue
                    for m in sorted(metric_cols):
                        pv = numeric([pmap[s].get(m, "") for s in common_seeds])
                        bv = numeric([bmap[s].get(m, "") for s in common_seeds])
                        if not pv or not bv:
                            continue
                        res = paired_test(pv, bv)
                        pm = float(np.mean(pv))
                        bm = float(np.mean(bv))
                        table_rows.append({
                            "size": size, "ff": ff, "metric": m,
                            "primary": primary_name, "baseline": baseline_name,
                            "pm": pm, "pv_n": len(pv), "bm": bm, "bv_n": len(bv),
                            "res": res,
                        })

        # Multiple-comparison correction on this experiment's table rows
        p_list = [r["res"]["p_value"] for r in table_rows if r["res"]["p_value"] is not None and not np.isnan(r["res"]["p_value"])]
        valid_idx = [i for i, r in enumerate(table_rows) if r["res"]["p_value"] is not None and not np.isnan(r["res"]["p_value"])]
        if valid_idx:
            holm_adj = holm_bonferroni([table_rows[i]["res"]["p_value"] for i in valid_idx])
            bh_adj = benjamini_hochberg([table_rows[i]["res"]["p_value"] for i in valid_idx])
            for adj_i, row_i in enumerate(valid_idx):
                table_rows[row_i]["holm_adj"] = holm_adj[adj_i]
                table_rows[row_i]["bh_adj"] = bh_adj[adj_i]

        for tr in table_rows:
            res = tr["res"]
            p_val = res["p_value"]
            if p_val is None or (isinstance(p_val, float) and np.isnan(p_val)):
                p_str = "undefined"
                holm_str = "—"
                bh_str = "—"
            else:
                p_str = fmt_p(p_val)
                ha = tr.get("holm_adj")
                bh = tr.get("bh_adj")
                holm_str = fmt_p(ha) if ha is not None and not np.isnan(ha) else "—"
                bh_str = fmt_p(bh) if bh is not None and not np.isnan(bh) else "—"

            eff = res["effect_size"]
            eff_str = f"{eff:.4f}" if eff is not None and not np.isnan(eff) else "undefined"
            eff_type = res["effect_size_type"] or "—"
            test_name = res["test"] or "none"
            test_status = res["test_status"]

            ci = res["paired_diff_ci"]
            ci_str = f"[{ci[0]:.4f}, {ci[1]:.4f}]" if not (np.isnan(ci[0]) or np.isnan(ci[1])) else "undefined"

            ff_display = tr["ff"] if tr["ff"] else "—"

            lines2.append(
                f"| {tr['size']} | {ff_display} | {tr['metric']} | {tr['primary']} | {tr['baseline']} | "
                f"{tr['pm']:.4f} ({tr['pv_n']}) | {tr['bm']:.4f} ({tr['bv_n']}) | {test_name} | "
                f"{p_str} | {holm_str} | {bh_str} | {eff_str} | {eff_type} | {test_status} | {ci_str} |"
            )

        lines2.append("")

    report_path = os.path.join(REPORT_DIR, "STATISTICAL_ANALYSIS.md")
    with open(report_path, "w") as f:
        f.write("\n".join(lines2))
    print(f"[STATS] Report written to {report_path}")


if __name__ == "__main__":
    main()
