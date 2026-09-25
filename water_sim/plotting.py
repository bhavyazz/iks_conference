"""
plotting.py
-----------
Publication-quality Matplotlib visualization suite for the water governance
simulation experiments comparing Systems A (Distributed IKS), B (MaxFlow LP),
and C (Fairness-Aware MaxMin LP).

Figures Generated:
1. fig1_efficiency_vs_missing_telemetry.png  (0% to 70% sweep with 95% CI bands)
2. fig2_fairness_vs_supply_scarcity.png      (50% to 110% supply sweep)
3. fig3_efficiency_combined_stress.png       (Multi-disturbance regimes)
4. fig4_fairness_combined_stress.png         (Equity under compound hazards)
5. fig5_paired_differences_distribution.png  (Distribution of Delta across seeds)
6. fig6_sensitivity_drought_threshold.png    (Parameter sensitivity: drought triggers)
7. fig7_sensitivity_transfer_rate.png        (Parameter sensitivity: sluice sharing)
8. fig8_topology_comparison.png              (Barabasi-Albert vs Directed Cascade)
"""

from __future__ import annotations

import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Style & Palette Configuration
# ---------------------------------------------------------------------------

PALETTE = {
    "A": "#D95F02",   # Terracotta / Rust for System A (IKS-inspired)
    "B": "#2166AC",   # Deep Steel Blue for System B (Central MaxFlow LP)
    "C": "#2CA25F",   # Emerald Green for System C (Central Fairness-Aware LP)
}

SYSTEM_LABELS = {
    "A": "System A (Distributed IKS)",
    "B": "System B (Central Throughput LP)",
    "C": "System C (Central Fairness-Aware LP)",
}

def _apply_style():
    plt.rcParams.update({
        "figure.dpi":         200,
        "figure.facecolor":   "#FFFFFF",
        "axes.facecolor":     "#FFFFFF",
        "axes.grid":          True,
        "grid.alpha":         0.30,
        "grid.linestyle":     "--",
        "font.family":        "sans-serif",
        "font.size":          10,
        "axes.titlesize":     12,
        "axes.labelsize":     11,
        "legend.fontsize":    9.0,
        "lines.linewidth":    2.2,
        "lines.markersize":   6,
    })


def _save(fig: plt.Figure, out_dir: Path, filename: str):
    os.makedirs(out_dir, exist_ok=True)
    fpath = out_dir / filename
    fig.savefig(fpath, bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  Saved Plot -> {fpath}")


# ---------------------------------------------------------------------------
# Publication Figures
# ---------------------------------------------------------------------------

def generate_research_figures(
    df_agg: pd.DataFrame,
    df_paired: pd.DataFrame,
    df_sens: pd.DataFrame | None,
    out_dir: Path,
) -> None:
    """
    Generate all primary research figures comparing Systems A, B, and C.
    """
    _apply_style()
    os.makedirs(out_dir, exist_ok=True)

    # -----------------------------------------------------------------------
    # Fig 1: Efficiency vs Missing Telemetry (0% to 70%)
    # -----------------------------------------------------------------------
    sub1 = df_agg[(df_agg["topology"] == "barabasi_albert") & (df_agg["category"] == "missing")]
    if not sub1.empty:
        fig, ax = plt.subplots(figsize=(7.0, 4.3))
        markers = {"A": "o", "B": "s", "C": "^"}
        for sys_id in ["A", "B", "C"]:
            s_data = sub1[sub1["system"] == sys_id].sort_values("severity")
            if s_data.empty:
                continue
            x = s_data["severity"] * 100
            y = s_data["eff_mean"]
            yerr_low = s_data["eff_ci95_low"]
            yerr_high = s_data["eff_ci95_high"]

            ax.plot(x, y, label=SYSTEM_LABELS[sys_id], color=PALETTE[sys_id], marker=markers[sys_id])
            ax.fill_between(x, yerr_low, yerr_high, color=PALETTE[sys_id], alpha=0.12)

        ax.set_title("Allocation Efficiency vs. Telemetry Loss", fontweight="bold")
        ax.set_xlabel("Missing Demand Telemetry (%)")
        ax.set_ylabel("Mean Allocation Efficiency")
        ax.set_ylim(0.85, 1.02)
        ax.legend(loc="lower left", frameon=True)
        _save(fig, out_dir, "fig1_efficiency_vs_missing_telemetry.png")

    # -----------------------------------------------------------------------
    # Fig 2: Fairness vs Supply Scarcity (50% to 110%)
    # -----------------------------------------------------------------------
    sub2 = df_agg[(df_agg["topology"] == "barabasi_albert") & (df_agg["category"] == "scarcity")]
    if not sub2.empty:
        fig, ax = plt.subplots(figsize=(7.0, 4.3))
        markers = {"A": "o", "B": "s", "C": "^"}
        for sys_id in ["A", "B", "C"]:
            s_data = sub2[sub2["system"] == sys_id].sort_values("severity")
            if s_data.empty:
                continue
            x = s_data["severity"] * 100
            y = s_data["fair_mean"]
            y_low = s_data["fair_ci95_low"]
            y_high = s_data["fair_ci95_high"]

            ax.plot(x, y, label=SYSTEM_LABELS[sys_id], color=PALETTE[sys_id], marker=markers[sys_id])
            ax.fill_between(x, y_low, y_high, color=PALETTE[sys_id], alpha=0.12)

        ax.axvline(70, color="gray", linestyle=":", label="Drought Threshold (70%)")
        ax.axvline(50, color="red", linestyle=":", label="Severe Drought Threshold (50%)")
        ax.set_title("Distributive Equity (Jain's Index) vs. Water Scarcity", fontweight="bold")
        ax.set_xlabel("Total Available Supply (% of Total Demand)")
        ax.set_ylabel("Mean Jain's Fairness Index")
        ax.set_ylim(0.48, 1.02)
        ax.legend(loc="lower right", frameon=True)
        _save(fig, out_dir, "fig2_fairness_vs_supply_scarcity.png")

    # -----------------------------------------------------------------------
    # Fig 3 & Fig 4: Combined Stress Regimes (Efficiency & Fairness)
    # -----------------------------------------------------------------------
    sub_comb = df_agg[(df_agg["topology"] == "barabasi_albert") & (df_agg["category"].isin(["combined", "baseline", "drought"]))]
    comb_conds = ["normal", "drought", "drought_missing_30", "severe_drought_missing_50", "combined_stress"]
    sub_comb = sub_comb[sub_comb["condition"].isin(comb_conds)]

    if not sub_comb.empty:
        labels_map = {
            "normal": "Baseline (110%)\n[No Stress]",
            "drought": "Dynamic Drought\n[5%/rnd draw]",
            "drought_missing_30": "Drought 70%\n+ 30% Missing",
            "severe_drought_missing_50": "Severe 60%\n+ 50% Missing",
            "combined_stress": "Compound Hazard\n[60%+30%M+20%F+Shock]",
        }

        # Efficiency Bar Chart
        fig, ax = plt.subplots(figsize=(9.5, 4.6))
        x = np.arange(len(comb_conds))
        width = 0.26

        for idx, sys_id in enumerate(["A", "B", "C"]):
            vals = [sub_comb[(sub_comb["condition"] == c) & (sub_comb["system"] == sys_id)]["eff_mean"].values[0] for c in comb_conds]
            errs = [sub_comb[(sub_comb["condition"] == c) & (sub_comb["system"] == sys_id)]["eff_std"].values[0] for c in comb_conds]
            ax.bar(x + (idx - 1) * width, vals, width, yerr=errs, label=SYSTEM_LABELS[sys_id], color=PALETTE[sys_id], capsize=3)

        ax.set_title("Allocation Efficiency Under Compound Disturbance Regimes", fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([labels_map[c] for c in comb_conds], fontsize=8.5)
        ax.set_ylabel("Mean Allocation Efficiency")
        ax.set_ylim(0.5, 1.05)
        ax.legend(loc="lower left", frameon=True)
        _save(fig, out_dir, "fig3_efficiency_combined_stress.png")

        # Fairness Bar Chart
        fig, ax = plt.subplots(figsize=(9.5, 4.6))
        for idx, sys_id in enumerate(["A", "B", "C"]):
            vals = [sub_comb[(sub_comb["condition"] == c) & (sub_comb["system"] == sys_id)]["fair_mean"].values[0] for c in comb_conds]
            errs = [sub_comb[(sub_comb["condition"] == c) & (sub_comb["system"] == sys_id)]["fair_std"].values[0] for c in comb_conds]
            ax.bar(x + (idx - 1) * width, vals, width, yerr=errs, label=SYSTEM_LABELS[sys_id], color=PALETTE[sys_id], capsize=3)

        ax.set_title("Distributive Equity (Jain's Index) Under Compound Disturbance Regimes", fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([labels_map[c] for c in comb_conds], fontsize=8.5)
        ax.set_ylabel("Mean Jain's Fairness Index")
        ax.set_ylim(0.55, 1.05)
        ax.legend(loc="lower left", frameon=True)
        _save(fig, out_dir, "fig4_fairness_combined_stress.png")

    # -----------------------------------------------------------------------
    # Fig 5: Paired Differences across seeds
    # -----------------------------------------------------------------------
    if not df_paired.empty:
        sub_pair = df_paired[df_paired["topology"] == "barabasi_albert"].copy()
        select_conds = ["normal", "drought", "missing_30", "missing_50", "supply_70", "supply_50", "combined_stress"]
        sub_pair = sub_pair[sub_pair["condition"].isin(select_conds)]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.5))

        y_pos = np.arange(len(sub_pair))
        w = 0.35

        # Efficiency Differences
        ax1.barh(y_pos - w/2, sub_pair["delta_eff_AB_mean"], w, label="System A vs B (Throughput)", color=PALETTE["A"], alpha=0.85)
        if "delta_eff_AC_mean" in sub_pair.columns:
            ax1.barh(y_pos + w/2, sub_pair["delta_eff_AC_mean"], w, label="System A vs C (Fairness)", color=PALETTE["C"], alpha=0.85)
        ax1.axvline(0, color="black", linestyle="--", alpha=0.6)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(sub_pair["condition"])
        ax1.set_title("Paired Difference in Efficiency\n(Delta = Sys A - Baseline)", fontweight="bold")
        ax1.set_xlabel("Mean Delta (Efficiency)")
        ax1.legend(loc="lower right")

        # Fairness Differences
        ax2.barh(y_pos - w/2, sub_pair["delta_fair_AB_mean"], w, label="System A vs B", color=PALETTE["A"], alpha=0.85)
        if "delta_fair_AC_mean" in sub_pair.columns:
            ax2.barh(y_pos + w/2, sub_pair["delta_fair_AC_mean"], w, label="System A vs C", color=PALETTE["C"], alpha=0.85)
        ax2.axvline(0, color="black", linestyle="--", alpha=0.6)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels([])
        ax2.set_title("Paired Difference in Fairness\n(Delta = Sys A - Baseline)", fontweight="bold")
        ax2.set_xlabel("Mean Delta (Jain's Index)")
        ax2.legend(loc="lower right")

        _save(fig, out_dir, "fig5_paired_differences_distribution.png")

    # -----------------------------------------------------------------------
    # Fig 6 & Fig 7: Sensitivity Analysis
    # -----------------------------------------------------------------------
    if df_sens is not None and not df_sens.empty:
        # Drought Threshold Sensitivity
        dt_sub = df_sens[df_sens["parameter"] == "drought_threshold"]
        if not dt_sub.empty:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.plot(dt_sub["param_value"], dt_sub["sys_a_fair_mean"], marker="o", color=PALETTE["A"], label="System A (IKS)")
            ax.plot(dt_sub["param_value"], dt_sub["sys_b_fair_mean"], marker="s", color=PALETTE["B"], linestyle="--", label="System B (Central Throughput)")
            ax.set_title("Sensitivity: Drought Trigger Threshold vs. Equity", fontweight="bold")
            ax.set_xlabel("Drought Activation Threshold (Supply / Baseline Ratio)")
            ax.set_ylabel("Mean Jain's Fairness Index")
            ax.set_ylim(0.80, 1.0)
            ax.legend()
            _save(fig, out_dir, "fig6_sensitivity_drought_threshold.png")

        # Transfer Rate Sensitivity
        tr_sub = df_sens[df_sens["parameter"] == "transfer_rate"]
        if not tr_sub.empty:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.plot(tr_sub["param_value"], tr_sub["sys_a_fair_mean"], marker="o", color=PALETTE["A"], label="System A Fairness")
            ax.plot(tr_sub["param_value"], tr_sub["sys_a_eff_mean"], marker="^", color="darkgreen", label="System A Efficiency")
            ax.set_title("Sensitivity: Inter-Village Sluice Transfer Rate", fontweight="bold")
            ax.set_xlabel("Surplus Transfer Coefficient (Fraction)")
            ax.set_ylabel("Metric Value")
            ax.legend()
            _save(fig, out_dir, "fig7_sensitivity_transfer_rate.png")

    # -----------------------------------------------------------------------
    # Fig 8: Topology Comparison
    # -----------------------------------------------------------------------
    topos = df_agg["topology"].unique()
    if len(topos) >= 2:
        top_sub = df_agg[df_agg["condition"].isin(["normal", "drought", "missing_50", "supply_60", "combined_stress"])]
        fig, ax = plt.subplots(figsize=(9.5, 4.5))

        cond_names = ["normal", "drought", "missing_50", "supply_60", "combined_stress"]
        x = np.arange(len(cond_names))
        width = 0.18

        ba_a = [top_sub[(top_sub["topology"] == "barabasi_albert") & (top_sub["condition"] == c) & (top_sub["system"] == "A")]["fair_mean"].values[0] for c in cond_names]
        ba_b = [top_sub[(top_sub["topology"] == "barabasi_albert") & (top_sub["condition"] == c) & (top_sub["system"] == "B")]["fair_mean"].values[0] for c in cond_names]
        cas_a = [top_sub[(top_sub["topology"] == "directed_cascade") & (top_sub["condition"] == c) & (top_sub["system"] == "A")]["fair_mean"].values[0] for c in cond_names]
        cas_b = [top_sub[(top_sub["topology"] == "directed_cascade") & (top_sub["condition"] == c) & (top_sub["system"] == "B")]["fair_mean"].values[0] for c in cond_names]

        ax.bar(x - 1.5*width, ba_a, width, label="BA Graph - System A", color=PALETTE["A"])
        ax.bar(x - 0.5*width, ba_b, width, label="BA Graph - System B", color=PALETTE["B"])
        ax.bar(x + 0.5*width, cas_a, width, label="Cascade - System A", color="#FDAE6B", edgecolor="black", hatch="//")
        ax.bar(x + 1.5*width, cas_b, width, label="Cascade - System B", color="#9ECAE1", edgecolor="black", hatch="\\\\")

        ax.set_title("Network Topology Robustness Comparison (Fairness Index)", fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(cond_names, fontsize=9.0)
        ax.set_ylabel("Mean Jain's Fairness Index")
        ax.set_ylim(0.48, 1.05)
        ax.legend(loc="lower left", frameon=True, fontsize=8.5)
        _save(fig, out_dir, "fig8_topology_comparison.png")


# Single-run plot generator
def generate_all_plots(df: pd.DataFrame, out_dir: Path) -> None:
    """Generate basic single-seed summary figures for A, B, and C."""
    _apply_style()
    os.makedirs(out_dir, exist_ok=True)
    summary = df.groupby(["condition", "system"])[["efficiency", "fairness"]].mean().reset_index()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))
    conds = summary["condition"].unique()
    x = np.arange(len(conds))
    w = 0.25

    for idx, sys_id in enumerate(["A", "B", "C"]):
        sub_s = summary[summary["system"] == sys_id]
        if sub_s.empty:
            continue
        effs = [summary[(summary["condition"] == c) & (summary["system"] == sys_id)]["efficiency"].values[0] for c in conds]
        fairs = [summary[(summary["condition"] == c) & (summary["system"] == sys_id)]["fairness"].values[0] for c in conds]
        ax1.bar(x + (idx - 1) * w, effs, w, label=SYSTEM_LABELS.get(sys_id, sys_id), color=PALETTE.get(sys_id, "gray"))
        ax2.bar(x + (idx - 1) * w, fairs, w, label=SYSTEM_LABELS.get(sys_id, sys_id), color=PALETTE.get(sys_id, "gray"))

    ax1.set_xticks(x)
    ax1.set_xticklabels(conds, rotation=45, ha="right", fontsize=8.0)
    ax1.set_title("Mean Efficiency per Condition")
    ax1.legend(fontsize=8)

    ax2.set_xticks(x)
    ax2.set_xticklabels(conds, rotation=45, ha="right", fontsize=8.0)
    ax2.set_title("Mean Fairness per Condition")
    ax2.legend(fontsize=8)

    _save(fig, out_dir, "summary_bars_efficiency.png")
