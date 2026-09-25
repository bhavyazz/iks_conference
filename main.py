"""
main.py
-------
Command-line orchestrator and experiment runner for the water governance
simulation research project.

Target: International Conference on IKS & SDGs (NMKRV, 2026).

Usage Examples:
---------------
1. Run single-seed baseline replication (Seed 42):
   python main.py --seed 42

2. Run 50-seed Monte Carlo evaluation across topologies:
   python main.py --multi-seed --num-seeds 50 --start-seed 42

3. Run parameter sensitivity analysis:
   python main.py --sensitivity

4. Run complete research experiment suite (All seeds + Topologies + Sensitivity + Plots):
   python main.py --all

5. Filter to specific conditions or topologies:
   python main.py --conditions normal drought missing_50 supply_60 --topologies barabasi_albert directed_cascade
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd


# ---------------------------------------------------------------------------
# CLI Argument Parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Water-Distribution Network Simulation: Traditional IKS Distributed vs Centralized LP",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--seed", type=int, default=42, help="Single random seed for replication (default: 42)")
    p.add_argument("--multi-seed", action="store_true", help="Execute multi-seed Monte Carlo simulation")
    p.add_argument("--num-seeds", type=int, default=50, help="Number of seeds in multi-seed sweep (default: 50)")
    p.add_argument("--start-seed", type=int, default=42, help="Starting seed index (default: 42)")
    p.add_argument("--sensitivity", action="store_true", help="Execute parameter sensitivity analysis")
    p.add_argument("--all", action="store_true", help="Execute full research suite (Multi-seed + Topologies + Sensitivity)")
    p.add_argument("--topologies", nargs="+", default=["barabasi_albert", "directed_cascade"],
                   help="Topologies to simulate (barabasi_albert, directed_cascade)")
    p.add_argument("--conditions", nargs="+", default=None, help="Subset of condition names to run")
    p.add_argument("--output-dir", default="results", help="Directory for CSV outputs (default: results/)")
    p.add_argument("--plot-dir", default="plots", help="Directory for figure outputs (default: plots/)")
    p.add_argument("--no-plots", action="store_true", help="Skip figure generation")
    p.add_argument("--list-conditions", action="store_true", help="List all defined experimental conditions")
    return p


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    from water_sim.experiments import (
        run_all_experiments,
        run_multi_seed_experiments,
        run_sensitivity_analysis,
        CONDITIONS,
    )
    from water_sim.plotting import generate_research_figures, generate_all_plots

    all_cond_names = [c["name"] for c in CONDITIONS]

    if args.list_conditions:
        print("Available experimental conditions:")
        for c in CONDITIONS:
            print(f"  {c['name']:<28} category={c['category']:<12} severity={c['severity']}")
        sys.exit(0)

    # Filter conditions if specified
    cond_subset = None
    if args.conditions:
        unknown = set(args.conditions) - set(all_cond_names)
        if unknown:
            print(f"ERROR: Unknown condition(s): {', '.join(sorted(unknown))}")
            sys.exit(1)
        cond_subset = [c for c in CONDITIONS if c["name"] in args.conditions]

    out_dir = Path(args.output_dir)
    plot_dir = Path(args.plot_dir)
    raw_dir = out_dir / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  WATER DISTRIBUTION NETWORK SIMULATION RESEARCH SUITE")
    print("  System A (Distributed IKS) vs System B (Centralized LP)")
    print("  Venue: NMKRV 2026 (IKS & SDGs)")
    print("=" * 65)

    t0 = time.perf_counter()

    if args.all or args.multi_seed:
        # Full Multi-Seed Execution (Phases 1, 2, 3, 4, 7, 11, 12, 13)
        seeds_range = range(args.start_seed, args.start_seed + args.num_seeds)
        df_raw, df_agg, df_paired = run_multi_seed_experiments(
            seeds=seeds_range,
            topologies=args.topologies,
            conditions=cond_subset,
            raw_dir=raw_dir,
        )

        # Save primary outputs
        raw_csv = out_dir / "all_experiments_raw.csv"
        agg_csv = out_dir / "aggregated_results.csv"
        pair_csv = out_dir / "paired_differences.csv"

        df_raw.to_csv(raw_csv, index=False)
        df_agg.to_csv(agg_csv, index=False)
        df_paired.to_csv(pair_csv, index=False)

        print(f"\n[Saved Raw Data]           -> {raw_csv}")
        print(f"[Saved Aggregated Summary] -> {agg_csv}")
        print(f"[Saved Paired Diffs]       -> {pair_csv}")

        df_sens = None
        if args.all or args.sensitivity:
            df_sens = run_sensitivity_analysis(seeds=range(args.start_seed, args.start_seed + 10))
            sens_csv = out_dir / "sensitivity_results.csv"
            df_sens.to_csv(sens_csv, index=False)
            print(f"[Saved Sensitivity Data]   -> {sens_csv}")

        # Generate Publication Figures
        if not args.no_plots:
            print("\nGenerating publication figures...")
            generate_research_figures(df_agg, df_paired, df_sens, out_dir=plot_dir)
            print(f"All research figures saved to -> {plot_dir}/")

    elif args.sensitivity:
        df_sens = run_sensitivity_analysis(seeds=range(args.start_seed, args.start_seed + 10))
        sens_csv = out_dir / "sensitivity_results.csv"
        df_sens.to_csv(sens_csv, index=False)
        print(f"\n[Saved Sensitivity Data] -> {sens_csv}")

    else:
        # Single-Seed Replication Mode (Default Seed 42)
        print(f"Running single-seed replication (Seed={args.seed}, Topologies={args.topologies})...")
        dfs = []
        for topo in args.topologies:
            df_t = run_all_experiments(seed=args.seed, topology=topo, conditions=cond_subset)
            dfs.append(df_t)
        df_res = pd.concat(dfs, ignore_index=True)
        csv_path = out_dir / f"results_seed{args.seed}.csv"
        df_res.to_csv(csv_path, index=False)
        print(f"\nResults saved -> {csv_path}")

        # Summary print
        print("\n--- Summary: Mean Efficiency & Fairness per Condition ---\n")
        print(df_res.groupby(["topology", "condition", "system"])[["efficiency", "fairness"]].mean().round(4))

        if not args.no_plots:
            generate_all_plots(df_res, out_dir=plot_dir)

    elapsed = time.perf_counter() - t0
    print(f"\nSimulation suite completed in {elapsed:.2f}s.")
    print("Done.\n")


if __name__ == "__main__":
    main()
