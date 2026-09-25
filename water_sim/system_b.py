"""
system_b.py
-----------
System B: Centralized LP Optimization Baseline
===============================================

Each round, System B solves a Linear Program using PuLP 4.x (with
HiGHS solver) or scipy.optimize.linprog as fallback to maximise
total satisfied demand subject to:

    sum(x_i) <= total_supply          (supply constraint)
    x_i <= demand_i   for all i       (demand cap)
    x_i >= 0          for all i       (non-negativity)

Objective:  maximize Σ x_i

Visibility & Evaluation Note:
System B may call state.get_global_view() to access central demand data.
Nodes with missing data receive a fallback demand estimate (d_hat_i).
Optimization uses the system's available demand estimate, while post-allocation
metric evaluation uses realized ground-truth demand identically across all systems.

PuLP 4.x API note
-----------------
PuLP 4.0 introduced a Rust backend and changed the variable creation
API:
  - Variables are created via prob.add_variable() or
    prob.add_variable_dict() instead of the old LpVariable() class.
  - prob.solve() now returns an LpSolveStats object (not an int).
  - The HiGHS solver (requires the `highspy` package) replaces CBC.
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
    import pulp          # preferred
    # Verify HiGHS is available (required by PuLP 4.x)
    _highs_solver = pulp.HiGHS(msg=False)
    if not _highs_solver.available():
        raise ImportError("HiGHS solver not available in PuLP")
except Exception:
    _BACKEND = "scipy"
    try:
        import scipy.optimize as _so  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "System B requires either PuLP 4.x + highspy, or scipy.  "
            "Install with: pip install pulp highspy  (or: pip install scipy)"
        ) from exc


# ---------------------------------------------------------------------------
# System B class
# ---------------------------------------------------------------------------

class SystemB:
    """
    Centralized optimization-based water allocator.

    Parameters
    ----------
    G : nx.Graph
        The village network graph (used for node enumeration).
    solver_verbose : bool
        If True, print LP solver output (useful for debugging).
    """

    def __init__(self, G: nx.Graph, solver_verbose: bool = False) -> None:
        self.G              = G
        self.solver_verbose = solver_verbose

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allocate(self, state: SimulationState) -> dict[int, float]:
        """
        Solve the LP and return per-node allocations.

        Returns
        -------
        allocations : dict {node_id: water_allocated}
        """
        # System B is PERMITTED to use the global view
        gv = state.get_global_view()

        total_supply  = gv["total_supply"]
        demands       = gv["demands"]          # may include fallback estimates
        active_nodes  = gv["active_nodes"]

        # Build ordered list for LP variable indexing
        nodes = sorted(active_nodes)

        if not nodes:
            return {n: 0.0 for n in self.G.nodes()}

        if _BACKEND == "pulp":
            allocs = self._solve_pulp(nodes, demands, total_supply)
        else:
            allocs = self._solve_scipy(nodes, demands, total_supply)

        # Fill zeros for failed/inactive nodes
        result: dict[int, float] = {n: 0.0 for n in self.G.nodes()}
        for n, v in allocs.items():
            result[n] = v

        return result

    # ------------------------------------------------------------------
    # LP solvers
    # ------------------------------------------------------------------

    def _solve_pulp(
        self,
        nodes:        list[int],
        demands:      dict[int, float],
        total_supply: float,
    ) -> dict[int, float]:
        """
        Solve the allocation LP using PuLP 4.x API with HiGHS solver.

        LP formulation
        ~~~~~~~~~~~~~~
        Variables : x_i  (allocation for node i), x_i in [0, demand_i]
        Objective : maximise  Σ x_i
        Subject to:
            Σ x_i         <= total_supply
            x_i           <= demands[i]   for all i   (per-node constraint)
            x_i           >= 0            for all i   (global lowBound)

        PuLP 4.x notes
        ~~~~~~~~~~~~~~
        - Variables created via prob.add_variable_dict() (new API).
        - prob.solve() returns an LpSolveStats object; check
          stats.has_solution for feasibility.
        - HiGHS replaces the old CBC bundled solver.
        """
        import pulp

        prob = pulp.LpProblem("WaterAllocation", pulp.LpMaximize)

        # Decision variables (PuLP 4.x API)
        # add_variable_dict returns {index: LpVariable}
        x = prob.add_variable_dict("x", indices=nodes, lowBound=0.0)

        # Per-node demand cap (upper bound as explicit constraint)
        for n in nodes:
            prob += x[n] <= demands[n], f"DemandCap_{n}"

        # Objective: maximise total satisfied demand
        prob += pulp.lpSum(x[n] for n in nodes), "TotalSatisfied"

        # Supply constraint: total allocations cannot exceed supply
        prob += pulp.lpSum(x[n] for n in nodes) <= total_supply, "SupplyCap"

        # Solve with HiGHS
        stats = prob.solve(pulp.HiGHS(msg=self.solver_verbose))

        if not stats.has_solution:
            warnings.warn(
                f"PuLP/HiGHS returned no feasible solution "
                f"(status={stats.status_str}). "
                "Falling back to zero allocations.",
                RuntimeWarning,
                stacklevel=3,
            )
            return {n: 0.0 for n in nodes}

        return {n: max(0.0, x[n].value() or 0.0) for n in nodes}

    def _solve_scipy(
        self,
        nodes:        list[int],
        demands:      dict[int, float],
        total_supply: float,
    ) -> dict[int, float]:
        """
        Solve the allocation LP using scipy.optimize.linprog.

        linprog minimises c·x, so we negate the objective.

        LP (as a minimisation problem for linprog)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        Minimise  -Σ x_i
        Subject to:
            Σ x_i          <= total_supply     (A_ub · x <= b_ub)
            0 <= x_i <= demands[i]             (bounds)
        """
        import scipy.optimize as so  # type: ignore

        n = len(nodes)
        c = [-1.0] * n                     # negate → maximise

        # Inequality constraint: sum(x) <= total_supply
        A_ub = [[1.0] * n]
        b_ub = [total_supply]

        bounds = [(0.0, demands[nd]) for nd in nodes]

        result = so.linprog(
            c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs"
        )

        if result.status != 0:
            warnings.warn(
                f"scipy linprog returned status {result.status}. "
                "Falling back to zero allocations.",
                RuntimeWarning,
                stacklevel=3,
            )
            return {n: 0.0 for n in nodes}

        return {nd: max(0.0, result.x[i]) for i, nd in enumerate(nodes)}
