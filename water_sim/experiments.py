"""
experiments.py
--------------
Experiment runner and stress suite for the water-distribution simulation.

Conditions Suite:
1. Baseline:
   - normal (110% supply)

2. Dynamic Hydrological Drought:
   - drought (cumulative 5%/round reduction from round 15)

3. Information Telemetry Sweep (Missing data: 0% to 70%):
   - missing_0, missing_10, missing_20, missing_30,
     missing_40, missing_50, missing_60, missing_70

4. Controlled Water Scarcity Sweep (Supply: 110% down to 50%):
   - supply_110, supply_100, supply_90, supply_80,
     supply_70, supply_60, supply_50

5. Node Failure Stress:
   - failure_10, failure_30

6. Localized Demand Spikes:
   - demand_shock (3x-5x spike in rounds 10-13)

7. Combined Disturbance Regimes:
   - drought_missing_30       (70% supply + 30% missing telemetry)
   - severe_drought_missing_50 (60% supply + 50% missing telemetry)
   - drought_failure_20       (70% supply + 20% node failure)
   - drought_shock            (70% supply + 4x demand shock)
   - combined_stress          (60% supply + 30% missing + 20% failure + 3.5x shock)

Execution:
Supports single-seed execution (default 42 for exact replication) and
multi-seed Monte Carlo evaluation (e.g., 50 seeds from 42 to 91).
"""

from __future__ import annotations

import random
from typing import Any, Literal
from pathlib import Path

import networkx as nx
import pandas as pd

from .network import (
    build_network,
    compute_demand_for_round,
    compute_total_supply,
    NUM_NODES,
    NUM_ROUNDS,
    SUPPLY_DEMAND_RATIO,
)
from .simulation_state import SimulationState
from .system_a import SystemA
from .system_b import SystemB
from .system_c import SystemC
from .metrics import (
    compute_metrics,
    compute_resilience,
    compute_stats_summary,
    compute_paired_comparison,
)


# ---------------------------------------------------------------------------
# Experiment Condition Definitions
# ---------------------------------------------------------------------------

# Full comprehensive list of experimental stress conditions
CONDITIONS: list[dict[str, Any]] = [
    # Baseline
    dict(name="normal", category="baseline", severity=0.0, stress_params={}),

    # Dynamic cumulative drought
    dict(name="drought", category="drought", severity=1.0,
         stress_params=dict(drought=True, drought_start=15, drought_rate=0.05)),

    # Missing telemetry sweep (0% to 70%)
    dict(name="missing_0",  category="missing", severity=0.0,  stress_params=dict(missing_frac=0.00)),
    dict(name="missing_10", category="missing", severity=0.10, stress_params=dict(missing_frac=0.10)),
    dict(name="missing_20", category="missing", severity=0.20, stress_params=dict(missing_frac=0.20)),
    dict(name="missing_30", category="missing", severity=0.30, stress_params=dict(missing_frac=0.30)),
    dict(name="missing_40", category="missing", severity=0.40, stress_params=dict(missing_frac=0.40)),
    dict(name="missing_50", category="missing", severity=0.50, stress_params=dict(missing_frac=0.50)),
    dict(name="missing_60", category="missing", severity=0.60, stress_params=dict(missing_frac=0.60)),
    dict(name="missing_70", category="missing", severity=0.70, stress_params=dict(missing_frac=0.70)),

    # Controlled water scarcity sweep (110% down to 50%)
    dict(name="supply_110", category="scarcity", severity=1.10, stress_params=dict(supply_ratio=1.10)),
    dict(name="supply_100", category="scarcity", severity=1.00, stress_params=dict(supply_ratio=1.00)),
    dict(name="supply_90",  category="scarcity", severity=0.90, stress_params=dict(supply_ratio=0.90)),
    dict(name="supply_80",  category="scarcity", severity=0.80, stress_params=dict(supply_ratio=0.80)),
    dict(name="supply_70",  category="scarcity", severity=0.70, stress_params=dict(supply_ratio=0.70)),
    dict(name="supply_60",  category="scarcity", severity=0.60, stress_params=dict(supply_ratio=0.60)),
    dict(name="supply_50",  category="scarcity", severity=0.50, stress_params=dict(supply_ratio=0.50)),

    # Inactive node failures
    dict(name="failure_10", category="failure", severity=0.10, stress_params=dict(failure_frac=0.10)),
    dict(name="failure_30", category="failure", severity=0.30, stress_params=dict(failure_frac=0.30)),

    # Demand surge
    dict(name="demand_shock", category="shock", severity=1.0,
         stress_params=dict(shock=True, shock_start=10, shock_end=13,
                            shock_multiplier_min=3.0, shock_multiplier_max=5.0)),

    # Combined stress regimes
    dict(name="drought_missing_30", category="combined", severity=0.70,
         stress_params=dict(supply_ratio=0.70, missing_frac=0.30)),
    dict(name="severe_drought_missing_50", category="combined", severity=0.60,
         stress_params=dict(supply_ratio=0.60, missing_frac=0.50)),
    dict(name="drought_failure_20", category="combined", severity=0.70,
         stress_params=dict(supply_ratio=0.70, failure_frac=0.20)),
    dict(name="drought_shock", category="combined", severity=0.70,
         stress_params=dict(supply_ratio=0.70, shock=True, shock_start=10, shock_end=13,
                            shock_multiplier_min=4.0, shock_multiplier_max=4.0)),
    dict(name="combined_stress", category="combined", severity=0.60,
         stress_params=dict(supply_ratio=0.60, missing_frac=0.30, failure_frac=0.20,
                            shock=True, shock_start=10, shock_end=13,
                            shock_multiplier_min=3.5, shock_multiplier_max=3.5)),
]


# ---------------------------------------------------------------------------
# Single-Condition Simulation Runner
# ---------------------------------------------------------------------------

def _run_one_condition(
    G:            nx.Graph,
    seed:         int,
    topology:     str = "barabasi_albert",
    # Stress parameters
    supply_ratio: float | None = None,
    drought:      bool = False,
    drought_start: int = 15,
    drought_rate: float = 0.05,
    missing_frac: float = 0.0,
    failure_frac: float = 0.0,
    shock:        bool = False,
    shock_start:  int = 10,
    shock_end:    int = 13,
    shock_multiplier_min: float = 3.0,
    shock_multiplier_max: float = 5.0,
    # System A parameter overrides (for sensitivity analysis)
    sys_a_kwargs: dict[str, Any] | None = None,
) -> list[dict]:
    """
    Execute 30 simulation rounds for one condition with rigorous assertion checks.
    """
    rng = random.Random(seed)
    walk = {}

    kwargs_a = sys_a_kwargs or {}
    sys_a = SystemA(G, **kwargs_a)
    sys_b = SystemB(G)
    sys_c = SystemC(G)

    shock_node = rng.choice(list(G.nodes())) if shock else None
    records: list[dict] = []

    for r in range(NUM_ROUNDS):
        # 1. Base demands
        demands = compute_demand_for_round(G, r, rng, walk_state=walk)

        # 2. Demand shock
        if shock and shock_node is not None and shock_start <= r <= shock_end:
            mult = rng.uniform(shock_multiplier_min, shock_multiplier_max)
            demands[shock_node] = demands[shock_node] * mult

        # 3. Supply calculation
        effective_ratio = supply_ratio if supply_ratio is not None else SUPPLY_DEMAND_RATIO
        total_supply = compute_total_supply(demands, ratio=effective_ratio)

        if drought and r >= drought_start:
            rounds_into = r - drought_start + 1
            reduction = (1.0 - drought_rate) ** rounds_into
            total_supply *= reduction

        # 4. Sample disturbance nodes
        all_nodes = list(G.nodes())

        missing_nodes: set[int] = set()
        if missing_frac > 0:
            k = max(1, int(round(len(all_nodes) * missing_frac)))
            missing_nodes = set(rng.sample(all_nodes, k))

        failed_nodes: set[int] = set()
        if failure_frac > 0:
            k = max(1, int(round(len(all_nodes) * failure_frac)))
            failed_nodes = set(rng.sample(all_nodes, k))

        # 5. Build SimulationState
        state = SimulationState(
            round_idx     = r,
            G             = G,
            demands       = demands,
            total_supply  = total_supply,
            failed_nodes  = failed_nodes,
            missing_nodes = missing_nodes,
        )

        # 6. Execute Allocations for all three systems
        alloc_a = sys_a.allocate(state)
        alloc_b = sys_b.allocate(state)
        alloc_c = sys_c.allocate(state)

        # --- Automated Validation Assertions (Phase 15) ---
        global_view = state.get_global_view()
        observed_demands = global_view["demands"]

        for system_label, alloc in [("A", alloc_a), ("B", alloc_b), ("C", alloc_c)]:
            sum_alloc = sum(alloc.values())
            assert sum_alloc <= total_supply + 1e-4, (
                f"Round {r} System {system_label} allocated {sum_alloc:.3f} > supply {total_supply:.3f}"
            )
            for nid, amt in alloc.items():
                assert amt >= -1e-6, f"Negative allocation at node {nid} in System {system_label}"
                if system_label == "A":
                    assert amt <= demands[nid] + 1e-4, (
                        f"System A over-allocation at node {nid} ({amt:.3f} > demand {demands[nid]:.3f})"
                    )
                else:
                    assert amt <= observed_demands.get(nid, 0.0) + 1e-4, (
                        f"System {system_label} violated observed demand cap at node {nid} ({amt:.3f} > obs {observed_demands.get(nid, 0.0):.3f})"
                    )
                if nid in failed_nodes:
                    assert abs(amt) < 1e-6, f"Failed node {nid} received non-zero allocation in System {system_label}"

        state.record_allocation_a(alloc_a)
        state.record_allocation_b(alloc_b)
        state.record_allocation_c(alloc_c)

        # 7. Compute Metrics
        results = state.get_results()
        m_a = compute_metrics(results, "A")
        m_b = compute_metrics(results, "B")
        m_c = compute_metrics(results, "C")
        tot_dem = sum(row["demand"] for row in results["nodes"] if row["active"])

        for system, m in [("A", m_a), ("B", m_b), ("C", m_c)]:
            records.append({
                "round":        r,
                "system":       system,
                "seed":         seed,
                "topology":     topology,
                "efficiency":   m["efficiency"],
                "fairness":     m["fairness"],
                "total_supply": total_supply,
                "total_demand": tot_dem,
            })

    return records


# ---------------------------------------------------------------------------
# All-Experiments Runner (Single Seed)
# ---------------------------------------------------------------------------

def run_all_experiments(
    seed: int = 42,
    topology: str = "barabasi_albert",
    conditions: list[dict[str, Any]] | None = None,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Run all conditions for a single seed and return a consolidated DataFrame.
    """
    cond_list = conditions or CONDITIONS
    G = build_network(seed=seed, topology=topology)

    all_rows: list[dict] = []

    if verbose:
        print(f"Running baseline (normal) on {topology} [seed={seed}]...")
    normal_records = _run_one_condition(G, seed=seed, topology=topology)

    baseline_a = [r for r in normal_records if r["system"] == "A"]
    baseline_b = [r for r in normal_records if r["system"] == "B"]
    baseline_c = [r for r in normal_records if r["system"] == "C"]

    for rec in normal_records:
        all_rows.append({
            **rec,
            "condition":       "normal",
            "category":        "baseline",
            "severity":        0.0,
            "resilience_eff":  0.0,
            "resilience_fair": 0.0,
        })

    for cond in cond_list:
        if cond["name"] == "normal":
            continue
        if verbose:
            print(f"Running condition: {cond['name']:<25} [topology={topology}]...")
        records = _run_one_condition(
            G, seed=seed, topology=topology, **cond["stress_params"]
        )

        rec_a = [r for r in records if r["system"] == "A"]
        rec_b = [r for r in records if r["system"] == "B"]
        rec_c = [r for r in records if r["system"] == "C"]

        res_eff_a  = compute_resilience(baseline_a, rec_a, "efficiency")
        res_fair_a = compute_resilience(baseline_a, rec_a, "fairness")
        res_eff_b  = compute_resilience(baseline_b, rec_b, "efficiency")
        res_fair_b = compute_resilience(baseline_b, rec_b, "fairness")
        res_eff_c  = compute_resilience(baseline_c, rec_c, "efficiency")
        res_fair_c = compute_resilience(baseline_c, rec_c, "fairness")

        for sys_id, r_list, r_eff, r_fair in [
            ("A", rec_a, res_eff_a, res_fair_a),
            ("B", rec_b, res_eff_b, res_fair_b),
            ("C", rec_c, res_eff_c, res_fair_c),
        ]:
            for i, rec in enumerate(r_list):
                all_rows.append({
                    **rec,
                    "condition":       cond["name"],
                    "category":        cond["category"],
                    "severity":        cond["severity"],
                    "resilience_eff":  r_eff[i],
                    "resilience_fair": r_fair[i],
                })

    df = pd.DataFrame(all_rows)
    col_order = [
        "seed", "topology", "round", "system", "condition", "category", "severity",
        "efficiency", "fairness", "resilience_eff", "resilience_fair",
        "total_supply", "total_demand",
    ]
    return df[col_order]


# ---------------------------------------------------------------------------
# Multi-Seed Monte Carlo Runner (Phase 1 & Phase 11)
# ---------------------------------------------------------------------------

def run_multi_seed_experiments(
    seeds: range | list[int] = range(42, 92),  # 50 seeds: 42 to 91
    topologies: list[str] = ["barabasi_albert", "directed_cascade"],
    conditions: list[dict[str, Any]] | None = None,
    raw_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run full experiment matrix across multiple seeds and topologies for Systems A, B, and C.

    Returns:
    --------
    (df_all_raw, df_aggregated, df_paired_diffs)
    """
    cond_list = conditions or CONDITIONS
    all_dfs: list[pd.DataFrame] = []

    if raw_dir:
        raw_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================")
    print(f" Starting Multi-Seed Monte Carlo Suite ({len(seeds)} seeds)")
    print(f" Systems: System A (IKS), System B (MaxFlow LP), System C (MaxMin LP)")
    print(f" Topologies: {', '.join(topologies)}")
    print(f" Total Conditions per seed: {len(cond_list)}")
    print(f"=======================================================\n")

    for seed in seeds:
        seed_dfs = []
        for topo in topologies:
            df_st = run_all_experiments(
                seed=seed, topology=topo, conditions=cond_list, verbose=False
            )
            seed_dfs.append(df_st)
            all_dfs.append(df_st)

        if raw_dir:
            df_seed = pd.concat(seed_dfs, ignore_index=True)
            df_seed.to_csv(raw_dir / f"seed_{seed}.csv", index=False)

        print(f"  [Completed Seed {seed:>3}/{max(seeds)}] Topologies: {', '.join(topologies)}")

    df_all_raw = pd.concat(all_dfs, ignore_index=True)

    # 1. Aggregated Summary Statistics per (topology, condition, system)
    agg_rows = []
    grouped = df_all_raw.groupby(["topology", "condition", "category", "severity", "system"])
    for (topo, cond, cat, sev, sys_name), group in grouped:
        eff_stats = compute_stats_summary(group["efficiency"].tolist())
        fair_stats = compute_stats_summary(group["fairness"].tolist())
        res_eff_stats = compute_stats_summary(group["resilience_eff"].tolist())
        res_fair_stats = compute_stats_summary(group["resilience_fair"].tolist())

        agg_rows.append({
            "topology":        topo,
            "condition":       cond,
            "category":        cat,
            "severity":        sev,
            "system":          sys_name,
            "num_seeds":       len(seeds),
            "total_rounds":    len(group),
            "eff_mean":        eff_stats["mean"],
            "eff_std":         eff_stats["std"],
            "eff_median":      eff_stats["median"],
            "eff_ci95_low":    eff_stats["ci_95_lower"],
            "eff_ci95_high":   eff_stats["ci_95_upper"],
            "fair_mean":       fair_stats["mean"],
            "fair_std":        fair_stats["std"],
            "fair_median":     fair_stats["median"],
            "fair_ci95_low":   fair_stats["ci_95_lower"],
            "fair_ci95_high":  fair_stats["ci_95_upper"],
            "res_eff_mean":    res_eff_stats["mean"],
            "res_eff_std":     res_eff_stats["std"],
            "res_fair_mean":   res_fair_stats["mean"],
            "res_fair_std":    res_fair_stats["std"],
        })

    df_aggregated = pd.DataFrame(agg_rows)

    # 2. Paired Differences per seed
    paired_rows = []
    seed_means = (
        df_all_raw.groupby(["seed", "topology", "condition", "category", "severity", "system"])
        [["efficiency", "fairness"]]
        .mean()
        .reset_index()
    )

    for (topo, cond, cat, sev), group in seed_means.groupby(["topology", "condition", "category", "severity"]):
        piv = group.pivot(index="seed", columns="system", values=["efficiency", "fairness"])
        if "A" in piv["efficiency"].columns and "B" in piv["efficiency"].columns and "C" in piv["efficiency"].columns:
            eff_a = piv["efficiency"]["A"].tolist()
            eff_b = piv["efficiency"]["B"].tolist()
            eff_c = piv["efficiency"]["C"].tolist()

            fair_a = piv["fairness"]["A"].tolist()
            fair_b = piv["fairness"]["B"].tolist()
            fair_c = piv["fairness"]["C"].tolist()

            comp_eff_ab = compute_paired_comparison(eff_a, eff_b)
            comp_fair_ab = compute_paired_comparison(fair_a, fair_b)

            comp_eff_ac = compute_paired_comparison(eff_a, eff_c)
            comp_fair_ac = compute_paired_comparison(fair_a, fair_c)

            comp_eff_cb = compute_paired_comparison(eff_c, eff_b)
            comp_fair_cb = compute_paired_comparison(fair_c, fair_b)

            paired_rows.append({
                "topology":        topo,
                "condition":       cond,
                "category":        cat,
                "severity":        sev,
                "num_seeds":       len(seeds),
                # A vs B (IKS vs Centralized Throughput LP)
                "delta_eff_AB_mean":   comp_eff_ab.get("mean_diff", 0.0),
                "delta_eff_AB_ci_low": comp_eff_ab.get("ci_95_lower", 0.0),
                "delta_eff_AB_ci_high":comp_eff_ab.get("ci_95_upper", 0.0),
                "p_value_eff_AB":      comp_eff_ab.get("p_value", 1.0),
                "delta_fair_AB_mean":  comp_fair_ab.get("mean_diff", 0.0),
                "delta_fair_AB_ci_low":comp_fair_ab.get("ci_95_lower", 0.0),
                "delta_fair_AB_ci_high":comp_fair_ab.get("ci_95_upper", 0.0),
                "p_value_fair_AB":     comp_fair_ab.get("p_value", 1.0),
                # A vs C (IKS vs Centralized Fairness-Aware LP)
                "delta_eff_AC_mean":   comp_eff_ac.get("mean_diff", 0.0),
                "delta_eff_AC_ci_low": comp_eff_ac.get("ci_95_lower", 0.0),
                "delta_eff_AC_ci_high":comp_eff_ac.get("ci_95_upper", 0.0),
                "p_value_eff_AC":      comp_eff_ac.get("p_value", 1.0),
                "delta_fair_AC_mean":  comp_fair_ac.get("mean_diff", 0.0),
                "delta_fair_AC_ci_low":comp_fair_ac.get("ci_95_lower", 0.0),
                "delta_fair_AC_ci_high":comp_fair_ac.get("ci_95_upper", 0.0),
                "p_value_fair_AC":     comp_fair_ac.get("p_value", 1.0),
                # C vs B (Centralized Fairness vs Centralized Throughput LP)
                "delta_eff_CB_mean":   comp_eff_cb.get("mean_diff", 0.0),
                "delta_fair_CB_mean":  comp_fair_cb.get("mean_diff", 0.0),
            })

    df_paired_diffs = pd.DataFrame(paired_rows)

    return df_all_raw, df_aggregated, df_paired_diffs


# ---------------------------------------------------------------------------
# Sensitivity Analysis Runner (Phase 6)
# ---------------------------------------------------------------------------

def run_sensitivity_analysis(
    seeds: range | list[int] = range(42, 52),  # 10 seeds for sensitivity
    topology: str = "barabasi_albert",
) -> pd.DataFrame:
    """
    Evaluate sensitivity of System A to computational modeling parameters:
    - drought_threshold: [0.60, 0.70, 0.80]
    - severe_drought_threshold: [0.40, 0.50, 0.60]
    - inter_village_transfer_rate: [0.10, 0.20, 0.30]
    - conveyance_loss_rate: [0.00, 0.05, 0.10]
    """
    param_grid = [
        # Drought threshold sweep (tested on dynamic drought)
        ("drought_threshold", 0.60, dict(drought_threshold=0.60), "drought"),
        ("drought_threshold", 0.70, dict(drought_threshold=0.70), "drought"),
        ("drought_threshold", 0.80, dict(drought_threshold=0.80), "drought"),

        # Severe drought threshold sweep (tested on supply_50)
        ("severe_drought_threshold", 0.40, dict(severe_drought_threshold=0.40), "supply_50"),
        ("severe_drought_threshold", 0.50, dict(severe_drought_threshold=0.50), "supply_50"),
        ("severe_drought_threshold", 0.60, dict(severe_drought_threshold=0.60), "supply_50"),

        # Inter-village transfer rate sweep (tested on supply_60)
        ("transfer_rate", 0.10, dict(inter_village_transfer_rate=0.10), "supply_60"),
        ("transfer_rate", 0.20, dict(inter_village_transfer_rate=0.20), "supply_60"),
        ("transfer_rate", 0.30, dict(inter_village_transfer_rate=0.30), "supply_60"),

        # Conveyance loss rate sweep (tested on normal)
        ("conveyance_rate", 0.00, dict(conveyance_loss_rate=0.00), "normal"),
        ("conveyance_rate", 0.05, dict(conveyance_loss_rate=0.05), "normal"),
        ("conveyance_rate", 0.10, dict(conveyance_loss_rate=0.10), "normal"),
    ]

    cond_dict = {c["name"]: c for c in CONDITIONS}
    sens_rows = []

    print(f"\n=======================================================")
    print(f" Starting Parameter Sensitivity Analysis ({len(seeds)} seeds)")
    print(f"=======================================================\n")

    for param_name, param_val, sys_a_kw, test_cond_name in param_grid:
        test_cond = cond_dict[test_cond_name]
        eff_a_list, fair_a_list = [], []
        eff_b_list, fair_b_list = [], []
        eff_c_list, fair_c_list = [], []

        for s in seeds:
            G = build_network(seed=s, topology=topology)
            recs = _run_one_condition(
                G, seed=s, topology=topology, sys_a_kwargs=sys_a_kw, **test_cond["stress_params"]
            )
            recs_a = [r for r in recs if r["system"] == "A"]
            recs_b = [r for r in recs if r["system"] == "B"]
            recs_c = [r for r in recs if r["system"] == "C"]

            eff_a_list.append(sum(r["efficiency"] for r in recs_a) / len(recs_a))
            fair_a_list.append(sum(r["fairness"] for r in recs_a) / len(recs_a))
            eff_b_list.append(sum(r["efficiency"] for r in recs_b) / len(recs_b))
            fair_b_list.append(sum(r["fairness"] for r in recs_b) / len(recs_b))
            eff_c_list.append(sum(r["efficiency"] for r in recs_c) / len(recs_c))
            fair_c_list.append(sum(r["fairness"] for r in recs_c) / len(recs_c))

        stat_eff_a = compute_stats_summary(eff_a_list)
        stat_fair_a = compute_stats_summary(fair_a_list)
        stat_eff_b = compute_stats_summary(eff_b_list)
        stat_fair_b = compute_stats_summary(fair_b_list)
        stat_eff_c = compute_stats_summary(eff_c_list)
        stat_fair_c = compute_stats_summary(fair_c_list)

        sens_rows.append({
            "parameter":      param_name,
            "param_value":    param_val,
            "test_condition": test_cond_name,
            "num_seeds":      len(seeds),
            "sys_a_eff_mean": stat_eff_a["mean"],
            "sys_a_eff_std":  stat_eff_a["std"],
            "sys_a_fair_mean":stat_fair_a["mean"],
            "sys_a_fair_std": stat_fair_a["std"],
            "sys_b_eff_mean": stat_eff_b["mean"],
            "sys_b_eff_std":  stat_eff_b["std"],
            "sys_b_fair_mean":stat_fair_b["mean"],
            "sys_b_fair_std": stat_fair_b["std"],
            "sys_c_eff_mean": stat_eff_c["mean"],
            "sys_c_eff_std":  stat_eff_c["std"],
            "sys_c_fair_mean":stat_fair_c["mean"],
            "sys_c_fair_std": stat_fair_c["std"],
        })
        print(f"  Tested {param_name:<25} = {param_val:<5} on {test_cond_name:<10} -> Sys A Fair={stat_fair_a['mean']:.4f}")

    return pd.DataFrame(sens_rows)
