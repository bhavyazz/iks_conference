"""
simulation_state.py
-------------------
SimulationState is the single source of truth for one simulation
round.  Both System A and System B read from it, but each system
accesses only the slice of state it is permitted to see.

Architecture note
-----------------
SimulationState itself is *not* a god-object that hands out global
views freely.  Accessor methods enforce the visibility boundary:

    - get_local_view(node)          → local + neighbour slice only
    - get_global_view()             → all data (System B only)

The distinction is structural: System A code must only call
get_local_view(); System B code may call get_global_view().
"""

from __future__ import annotations

import dataclasses
from typing import Any

import networkx as nx


# ---------------------------------------------------------------------------
# Data classes for per-node status
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class NodeStatus:
    """Tracks mutable per-node state for one simulation round."""
    node_id:       int
    demand:        float          # true demand this round
    active:        bool  = True   # False if node has failed
    missing_data:  bool  = False  # True if demand hidden from System B
    allocation_a:  float = 0.0    # water received from System A (Distributed IKS)
    allocation_b:  float = 0.0    # water received from System B (Centralized Max-Flow LP)
    allocation_c:  float = 0.0    # water received from System C (Centralized Max-Min Fairness LP)


# ---------------------------------------------------------------------------
# SimulationState
# ---------------------------------------------------------------------------

class SimulationState:
    """
    Holds the complete world-state for a single simulation round.

    Parameters
    ----------
    round_idx     : 0-based round counter
    G             : the network graph (used for adjacency queries)
    demands       : {node_id: demand_value} for ALL nodes
    total_supply  : total water available this round
    failed_nodes  : set of node IDs that are disabled this round
    missing_nodes : set of node IDs whose demand is hidden (System B & C)
    """

    def __init__(
        self,
        round_idx:     int,
        G:             nx.Graph,
        demands:       dict[int, float],
        total_supply:  float,
        failed_nodes:  set[int]  | None = None,
        missing_nodes: set[int]  | None = None,
    ) -> None:
        self.round_idx    = round_idx
        self.G            = G
        self.total_supply = total_supply

        self._failed_nodes  = failed_nodes  or set()
        self._missing_nodes = missing_nodes or set()

        # Build per-node status objects
        self._nodes: dict[int, NodeStatus] = {}
        for nid, demand in demands.items():
            self._nodes[nid] = NodeStatus(
                node_id      = nid,
                demand       = demand,
                active       = (nid not in self._failed_nodes),
                missing_data = (nid in self._missing_nodes),
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active_nodes(self) -> list[int]:
        """Return list of currently active (non-failed) node IDs."""
        return [nid for nid, ns in self._nodes.items() if ns.active]

    @property
    def failed_nodes(self) -> set[int]:
        return set(self._failed_nodes)

    @property
    def missing_nodes(self) -> set[int]:
        return set(self._missing_nodes)

    # ------------------------------------------------------------------
    # Visibility-gated accessors
    # ------------------------------------------------------------------

    def get_local_view(self, node: int) -> dict[str, Any]:
        """
        Return the information slice visible to a single node agent.

        Contains:
            - This node's own demand and status
            - Each immediate neighbour's demand and active status
              (but NOT neighbour allocations or global supply)

        This is the ONLY method System A code is permitted to call
        when making allocation decisions.
        """
        ns = self._nodes[node]
        neighbours: dict[int, dict] = {}
        for nbr in self.G.neighbors(node):
            nbr_ns = self._nodes[nbr]
            neighbours[nbr] = {
                "demand":             nbr_ns.demand if nbr_ns.active else 0.0,
                "active":             nbr_ns.active,
                "landholding":        self.G.nodes[nbr].get("landholding", 1.0),
                "distance_from_head": self.G.nodes[nbr].get("distance_from_head", 0),
            }

        return {
            "node_id":            node,
            "demand":             ns.demand,
            "active":             ns.active,
            "landholding":        self.G.nodes[node].get("landholding", 1.0),
            "distance_from_head": self.G.nodes[node].get("distance_from_head", 0),
            "neighbours":         neighbours,
        }

    def get_global_view(self) -> dict[str, Any]:
        """
        Return complete observed world-state. Permitted for System B and System C.

        Nodes with missing_data=True have their demand replaced by
        a fallback estimate (mean of active observed neighbours).
        """
        demands_visible: dict[int, float] = {}
        for nid, ns in self._nodes.items():
            if not ns.active:
                demands_visible[nid] = 0.0          # failed → no demand
            elif ns.missing_data:
                # Fallback: use mean of active-neighbour demands as proxy
                nbr_demands = [
                    self._nodes[nbr].demand
                    for nbr in self.G.neighbors(nid)
                    if self._nodes[nbr].active and not self._nodes[nbr].missing_data
                ]
                demands_visible[nid] = (
                    sum(nbr_demands) / len(nbr_demands)
                    if nbr_demands else 100.0       # absolute fallback constant
                )
            else:
                demands_visible[nid] = ns.demand

        return {
            "total_supply":  self.total_supply,
            "demands":       demands_visible,
            "active_nodes":  self.active_nodes,
            "missing_nodes": list(self._missing_nodes),
        }

    # ------------------------------------------------------------------
    # Allocation recorders
    # ------------------------------------------------------------------

    def record_allocation_a(self, allocations: dict[int, float]) -> None:
        """Write System A allocations back into the state."""
        for nid, alloc in allocations.items():
            self._nodes[nid].allocation_a = max(0.0, alloc)

    def record_allocation_b(self, allocations: dict[int, float]) -> None:
        """Write System B allocations back into the state."""
        for nid, alloc in allocations.items():
            self._nodes[nid].allocation_b = max(0.0, alloc)

    def record_allocation_c(self, allocations: dict[int, float]) -> None:
        """Write System C allocations back into the state."""
        for nid, alloc in allocations.items():
            self._nodes[nid].allocation_c = max(0.0, alloc)

    # ------------------------------------------------------------------
    # Result extraction (for metrics)
    # ------------------------------------------------------------------

    def get_results(self) -> dict[str, Any]:
        """
        Return per-node demand and allocations for metric computation.
        Includes ALL nodes (active or not).
        """
        rows = []
        for nid, ns in self._nodes.items():
            rows.append({
                "node_id":      nid,
                "demand":       ns.demand,
                "active":       ns.active,
                "allocation_a": ns.allocation_a,
                "allocation_b": ns.allocation_b,
                "allocation_c": ns.allocation_c,
            })
        return {
            "round_idx":    self.round_idx,
            "total_supply": self.total_supply,
            "nodes":        rows,
        }
