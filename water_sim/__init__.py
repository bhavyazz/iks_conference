"""
water_sim/__init__.py
---------------------
Package init — exports top-level public API.
"""

from .network          import build_network, compute_demand_for_round, compute_total_supply, NUM_NODES, NUM_ROUNDS
from .simulation_state import SimulationState
from .system_a         import SystemA, compute_warabandi_weight, murai_subsistence_share
from .system_b         import SystemB
from .system_c         import SystemC
from .metrics          import compute_metrics, compute_resilience, compute_stats_summary, compute_paired_comparison
from .experiments      import run_all_experiments, run_multi_seed_experiments, run_sensitivity_analysis, CONDITIONS
from .plotting         import generate_research_figures, generate_all_plots

__all__ = [
    "build_network",
    "compute_demand_for_round",
    "compute_total_supply",
    "NUM_NODES",
    "NUM_ROUNDS",
    "SimulationState",
    "SystemA",
    "SystemB",
    "SystemC",
    "compute_warabandi_weight",
    "murai_subsistence_share",
    "compute_metrics",
    "compute_resilience",
    "compute_stats_summary",
    "compute_paired_comparison",
    "run_all_experiments",
    "run_multi_seed_experiments",
    "run_sensitivity_analysis",
    "CONDITIONS",
    "generate_research_figures",
    "generate_all_plots",
]
