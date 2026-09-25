"""
metrics.py
----------
Metric computation, statistical aggregation, and paired comparison functions
for the water-distribution simulation experiments.

Metrics:
1. Allocation Efficiency:
   Fraction of active demand successfully met by allocated water:
       Efficiency = sum(min(x_i, d_i)) / sum(d_i)

2. Jain's Fairness Index:
   Measures uniformity of relative satisfaction ratios r_i = min(x_i, d_i) / d_i:
       J(r) = (sum(r_i))^2 / (n * sum(r_i^2))
   Note: Jain's Index measures equality of relative satisfaction among active node
   agents; it does not measure historical caste, landholding, or social equity.

3. Graceful Performance Degradation:
   Percentage performance drop vs unconstrained baseline (referred to as resilience):
       Drop (%) = (M_baseline - M_stress) / M_baseline * 100
"""

from __future__ import annotations

import math
from typing import Literal, Any


# ---------------------------------------------------------------------------
# Per-round metric computation
# ---------------------------------------------------------------------------

def compute_metrics(
    results: dict,
    system:  Literal["A", "B", "C"],
) -> dict[str, float]:
    """
    Compute efficiency and Jain's fairness index for one simulation round.

    Parameters
    ----------
    results : dict
        Snapshot output from SimulationState.get_results().
    system : "A" | "B"

    Returns
    -------
    dict with "efficiency" and "fairness"
    """
    alloc_key = f"allocation_{system.lower()}"
    active_nodes = [row for row in results["nodes"] if row["active"]]

    if not active_nodes:
        return {"efficiency": 0.0, "fairness": 1.0}

    total_demand = sum(row["demand"] for row in active_nodes)
    total_satisfied = sum(
        min(row[alloc_key], row["demand"]) for row in active_nodes
    )

    efficiency = total_satisfied / total_demand if total_demand > 0 else 0.0

    # Satisfaction ratios per active node
    sat_ratios = [
        min(row[alloc_key], row["demand"]) / row["demand"]
        if row["demand"] > 0 else 0.0
        for row in active_nodes
    ]

    n  = len(sat_ratios)
    s1 = sum(sat_ratios)
    s2 = sum(r ** 2 for r in sat_ratios)

    fairness = (s1 ** 2) / (n * s2) if s2 > 0 and n > 0 else 1.0

    return {"efficiency": efficiency, "fairness": fairness}


# ---------------------------------------------------------------------------
# Resilience / Performance Degradation
# ---------------------------------------------------------------------------

def compute_resilience(
    baseline_records: list[dict],
    stress_records:   list[dict],
    metric_key:       Literal["efficiency", "fairness"],
) -> list[float]:
    """
    Compute per-round percentage performance degradation vs. baseline.
    """
    degradation = []
    for base, stress in zip(baseline_records, stress_records):
        base_val   = base[metric_key]
        stress_val = stress[metric_key]
        if base_val > 1e-9:
            drop = (base_val - stress_val) / base_val * 100.0
        else:
            drop = 0.0
        degradation.append(drop)
    return degradation


# ---------------------------------------------------------------------------
# Statistical Summaries & Paired Testing
# ---------------------------------------------------------------------------

def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = mean(values)
    var = sum((v - mu) ** 2 for v in values) / (len(values) - 1)  # sample variance
    return math.sqrt(var)


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    sorted_v = sorted(values)
    n = len(sorted_v)
    mid = n // 2
    if n % 2 == 1:
        return sorted_v[mid]
    return (sorted_v[mid - 1] + sorted_v[mid]) / 2.0


def compute_stats_summary(values: list[float]) -> dict[str, float]:
    """
    Compute comprehensive summary statistics for a list of values.
    """
    if not values:
        return {
            "n": 0, "mean": 0.0, "std": 0.0, "median": 0.0,
            "min": 0.0, "max": 0.0, "ci_95_lower": 0.0, "ci_95_upper": 0.0,
        }

    n = len(values)
    m = mean(values)
    s = std(values)
    med = median(values)
    vmin = min(values)
    vmax = max(values)

    # 95% Confidence Interval using normal / t approx (1.96 * s / sqrt(n))
    margin = (1.96 * s / math.sqrt(n)) if n > 1 else 0.0

    return {
        "n": n,
        "mean": m,
        "std": s,
        "median": med,
        "min": vmin,
        "max": vmax,
        "ci_95_lower": m - margin,
        "ci_95_upper": m + margin,
    }


def compute_paired_comparison(
    values_a: list[float],
    values_b: list[float],
) -> dict[str, Any]:
    """
    Compute paired difference statistics (Delta = A - B) across seeds.
    """
    if len(values_a) != len(values_b) or not values_a:
        return {}

    diffs = [a - b for a, b in zip(values_a, values_b)]
    stats_diff = compute_stats_summary(diffs)

    p_value = None
    try:
        from scipy import stats
        # Use Wilcoxon signed-rank test or paired t-test
        # If all diffs are 0, p-value is 1.0
        if all(abs(d) < 1e-9 for d in diffs):
            p_value = 1.0
        else:
            try:
                stat, p_val = stats.wilcoxon(diffs)
                p_value = float(p_val)
            except Exception:
                stat, p_val = stats.ttest_rel(values_a, values_b)
                p_value = float(p_val)
    except ImportError:
        p_value = None

    return {
        "mean_diff": stats_diff["mean"],
        "std_diff": stats_diff["std"],
        "median_diff": stats_diff["median"],
        "ci_95_lower": stats_diff["ci_95_lower"],
        "ci_95_upper": stats_diff["ci_95_upper"],
        "p_value": p_value,
        "diffs": diffs,
    }
