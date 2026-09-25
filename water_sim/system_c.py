"""
system_c.py
-----------
System C: Centralized Fairness-Aware LP Optimization Baseline
=============================================================
Centralized optimization model that explicitly maximizes distributive equity
(max-min fractional demand satisfaction) under global observed demand.

Mathematical Formulation:
-------------------------
Variables:
    x_i    : allocation to active node i (x_i in [0, d_hat_i])
    theta  : uniform fractional satisfaction lower bound (theta in [0, 1])

Objective:
    Maximize:  theta + 1e-4 * sum(x_i / d_hat_i)
    (Maximizes the minimum satisfaction fraction across all nodes, with a small
     regularizer to distribute any remaining surplus).

Subject to:
    x_i >= theta * d_hat_i       for all i in V_active   (equity lower bound)
    x_i <= d_hat_i               for all i in V_active   (demand cap)
    x_i >= 0                     for all i in V_active   (non-negativity)
    sum(x_i) <= total_supply                             (supply capacity)
    theta in [0, 1]

Visibility & Evaluation Note:
    Optimization uses the system's available demand estimate (d_hat_i via
    state.get_global_view()), while post-allocation metric evaluation uses
    realized ground-truth demand (d_i) identically across all systems.
"""

from __future__ import annotations

import warnings
from typing import Literal

import networkx as nx

from .simulation_state import SimulationState

# ---------------------------------------------------------------------------
# Solver backend detection
# ---------------------------------------------------------------------------
_BACKEND: Literal["pulp", "scipy"] = "pulp"

try:
    import pulp
    _highs_solver = pulp.HiGHS(msg=False)
    if not _highs_solver.available():
        raise ImportError("HiGHS solver not available in PuLP")
except Exception:
    _BACKEND = "scipy"
    try:
        import scipy.optimize as _so  # type: ignore
    except ImportError as exc:
        raise ImportError("System C requires PuLP + highspy or scipy.") from exc


# ---------------------------------------------------------------------------
# System C: Centralized Fairness-Aware Optimizer
# ---------------------------------------------------------------------------

class SystemC:
    """
    Centralized fairness-aware allocator solving a max-min fractional satisfaction LP.
    """

    def __init__(self, G: nx.Graph, solver_verbose: bool = False) -> None:
        self.G = G
        self.solver_verbose = solver_verbose

    def allocate(self, state: SimulationState) -> dict[int, float]:
        """
        Solve max-min fairness LP and return per-node allocations.

        Information-architecture note:
            Optimization uses the system's available demand estimate
            (d_hat_i via state.get_global_view(), with neighbor-mean
            imputation for missing telemetry), while post-allocation
            metric evaluation uses realized ground-truth demand (d_i)
            identically across all three systems (A, B, C).
            This asymmetry is an intentional research variable, not an
            implementation defect.
        """
        gv = state.get_global_view()
        total_supply = gv["total_supply"]
        demands = gv["demands"]
        active_nodes = sorted(gv["active_nodes"])

        if not active_nodes:
            return {n: 0.0 for n in self.G.nodes()}

        if _BACKEND == "pulp":
            allocs = self._solve_pulp(active_nodes, demands, total_supply)
        else:
            allocs = self._solve_scipy(active_nodes, demands, total_supply)

        result: dict[int, float] = {n: 0.0 for n in self.G.nodes()}
        for n, v in allocs.items():
            result[n] = v

        return result

    def _solve_pulp(
        self,
        nodes: list[int],
        demands: dict[int, float],
        total_supply: float,
    ) -> dict[int, float]:
        import pulp

        prob = pulp.LpProblem("WaterFairnessLP", pulp.LpMaximize)

        # Decision variables
        x = prob.add_variable_dict("x", indices=nodes, lowBound=0.0)
        theta = prob.add_variable("theta", lowBound=0.0, upBound=1.0)

        # Max-min satisfaction constraints: x_i >= theta * demand_i
        for n in nodes:
            d_val = max(1e-3, demands[n])
            prob += x[n] <= d_val, f"DemandCap_{n}"
            prob += x[n] >= theta * d_val, f"FairnessBound_{n}"

        # Supply constraint
        prob += pulp.lpSum(x[n] for n in nodes) <= total_supply, "SupplyCap"

        # Objective: Maximize min fraction theta + small regularizer
        reg_terms = [x[n] / max(1e-3, demands[n]) for n in nodes]
        prob += theta + (1e-4 / len(nodes)) * pulp.lpSum(reg_terms), "MaxMinFairnessObj"

        stats = prob.solve(pulp.HiGHS(msg=self.solver_verbose))

        if not stats.has_solution:
            warnings.warn("System C LP returned no feasible solution; falling back to zeros.")
            return {n: 0.0 for n in nodes}

        return {n: max(0.0, x[n].value() or 0.0) for n in nodes}

    def _solve_scipy(
        self,
        nodes: list[int],
        demands: dict[int, float],
        total_supply: float,
    ) -> dict[int, float]:
        import scipy.optimize as so  # type: ignore

        n = len(nodes)
        # Decision variables: [x_0, ..., x_{n-1}, theta]
        c = [-1e-4 / (n * max(1e-3, demands[nd])) for nd in nodes] + [-1.0]

        # Inequality constraints:
        # 1. sum(x) <= total_supply  ->  [1, ..., 1, 0] * z <= total_supply
        # 2. theta * d_i - x_i <= 0  ->  [-1_i, ..., d_i] * z <= 0
        A_ub = []
        b_ub = []

        # Supply cap
        A_ub.append([1.0] * n + [0.0])
        b_ub.append(total_supply)

        # Equity lower bounds
        for i, nd in enumerate(nodes):
            d_val = max(1e-3, demands[nd])
            row = [0.0] * (n + 1)
            row[i] = -1.0
            row[-1] = d_val
            A_ub.append(row)
            b_ub.append(0.0)

        bounds = [(0.0, max(1e-3, demands[nd])) for nd in nodes] + [(0.0, 1.0)]

        result = so.linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")

        if result.status != 0:
            warnings.warn("System C scipy LP returned non-zero status; falling back to zeros.")
            return {n: 0.0 for n in nodes}

        return {nd: max(0.0, result.x[i]) for i, nd in enumerate(nodes)}
