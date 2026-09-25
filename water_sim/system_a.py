"""
system_a.py
-----------
System A: Traditional Distributed Water-Allocation Framework
============================================================
Computational formalization of traditional Indian water-governance principles
inspired by Warabandi canal rotation (North India) and Murai tank-cascade
drought sharing with Neerkatti sluice management (South India / Tamil Nadu).

RESEARCH & INSTITUTIONAL FOUNDATIONS
------------------------------------
1. Warabandi Canal Rotation & Conveyance Allowances (North India):
   - Principle: Systematic rotational scheduling proportional to landholding,
     with time/volume credits (nikal) given to tail-end farmers to compensate
     for canal conveyance and seepage losses.
   - Sources: State Irrigation Codes (Punjab, Haryana, Rajasthan);
     Malhotra, S. P. (1982) "The Warabandi System and Its Infrastructure",
     Central Board of Irrigation and Power, New Delhi.

2. Murai Tank Scarcity & Neerkatti Sluice Sharing (South India / Tamil Nadu):
   - Principle: During water scarcity, customary proportional landholding
     privileges are suspended in favor of equal subsistence rations across
     all village members. Peripheral / tail-end reaches receive prioritized
     turns under severe drought to prevent crop loss. Upstream surplus is
     redistributed to water-deficient downstream tanks via coordinated sluices.
   - Sources: Mosse, David (2003) "The Rule of Water: Statecraft, Ecology and
     Collective Action in South India", Oxford University Press;
     Palanisami, K. and Easter, K. W. (2000) "Tank Irrigation in the 21st Century",
     Discovery Publishing House.

MODELING NOTE ON PARAMETERS
---------------------------
The specific numerical values used in this simulation—including the drought
trigger threshold (0.70), severe drought threshold (0.50), conveyance loss
coefficient (0.05), inter-village transfer fraction (0.20), subsistence
baseline (50.0 ML), and 7-round rotation cycle—are COMPUTATIONAL MODELING
PARAMETERS chosen to operationalize qualitative historical principles into
discrete algorithmic rules, NOT historically fixed universal constants.
"""

from __future__ import annotations

from typing import Any
import networkx as nx

from .simulation_state import SimulationState


# ---------------------------------------------------------------------------
# Algorithmic Formalization Functions
# ---------------------------------------------------------------------------

def compute_warabandi_weight(
    landholding: float,
    distance_from_head: int,
    conveyance_loss_rate: float = 0.05,
) -> float:
    """
    Compute Warabandi entitlement weight for a node.

    Formalization:
        weight_i = landholding_i * (1.0 + conveyance_loss_rate * distance_i)

    Conveyance compensation operationalizes the documented Warabandi 'nikal'
    credit providing additional turn duration to downstream cultivators.
    """
    conveyance_compensation = 1.0 + conveyance_loss_rate * float(distance_from_head)
    return max(0.1, landholding * conveyance_compensation)


def murai_subsistence_share(
    available_pool: float,
    active_node_count: int,
) -> float:
    """
    Compute Murai equal-share subsistence quota under drought conditions.

    Operationalizes the documented Murai convention of suspending landholding
    inequalities during scarcity to guarantee baseline survival across communities.
    """
    if active_node_count <= 0:
        return 0.0
    return available_pool / float(active_node_count)


# ---------------------------------------------------------------------------
# System A: Distributed Allocator
# ---------------------------------------------------------------------------

class SystemA:
    """
    Decentralized water allocator operationalizing Warabandi and Murai principles.

    Parameters
    ----------
    G : nx.Graph
        The village network graph.
    cycle_length : int
        Rotation cycle length in rounds (default: 7).
    conveyance_loss_rate : float
        Simulation coefficient for tail-end conveyance compensation (default: 0.05).
    drought_threshold : float
        Supply-to-baseline ratio triggering equal-share rationing (default: 0.70).
    severe_drought_threshold : float
        Supply-to-baseline ratio triggering tail-first service inversion (default: 0.50).
    inter_village_transfer_rate : float
        Fraction of upstream surplus transferred to downstream neighbors (default: 0.20).
    subsistence_level : float
        Nominal baseline subsistence threshold per node (default: 50.0).
    local_supply_mode : bool
        If True, runs in strict decentralized mode where nodes estimate supply locally
        without an active running pool counter (default: False).
    """

    def __init__(
        self,
        G: nx.Graph,
        cycle_length: int = 7,
        conveyance_loss_rate: float = 0.05,
        drought_threshold: float = 0.70,
        severe_drought_threshold: float = 0.50,
        inter_village_transfer_rate: float = 0.20,
        subsistence_level: float = 50.0,
        local_supply_mode: bool = False,
    ) -> None:
        self.G = G
        self.cycle_length = cycle_length
        self.conveyance_loss_rate = conveyance_loss_rate
        self.drought_threshold = drought_threshold
        self.severe_drought_threshold = severe_drought_threshold
        self.inter_village_transfer_rate = inter_village_transfer_rate
        self.subsistence_level = subsistence_level
        self.local_supply_mode = local_supply_mode

        # Nominal aggregate baseline demand across the network
        self.nominal_baseline = sum(
            G.nodes[n].get("base_demand", 100.0) for n in G.nodes()
        )

    # ------------------------------------------------------------------
    # Allocation Execution
    # ------------------------------------------------------------------

    def allocate(self, state: SimulationState) -> dict[int, float]:
        """
        Execute one round of distributed water allocation.

        Information boundary:
        Queries for per-node state use state.get_local_view(node).
        """
        all_nodes = list(self.G.nodes())
        allocations: dict[int, float] = {n: 0.0 for n in all_nodes}

        # Gather local views for all nodes
        local_views: dict[int, dict[str, Any]] = {
            n: state.get_local_view(n) for n in all_nodes
        }

        active_nodes = [n for n in all_nodes if local_views[n]["active"]]
        if not active_nodes:
            return allocations

        available_pool = state.total_supply
        supply_ratio = available_pool / self.nominal_baseline if self.nominal_baseline > 0 else 1.0

        is_drought = supply_ratio < self.drought_threshold
        is_severe_drought = supply_ratio < self.severe_drought_threshold

        # --- Service Ordering ---
        # 1. Severe Drought: Tail-First Priority (protect peripheral tail nodes from crop desiccation)
        # 2. Normal / Moderate Scarcity: Head-to-Tail Warabandi order (along hydraulic gradient)
        if is_severe_drought:
            serve_order = sorted(
                active_nodes,
                key=lambda n: (-local_views[n]["distance_from_head"], n),
            )
        else:
            serve_order = sorted(
                active_nodes,
                key=lambda n: (local_views[n]["distance_from_head"], n),
            )

        # --- Primary Allocation Phase ---
        if is_drought:
            # Murai Equal-Share Protocol: Landholding privileges suspended
            equal_ration = murai_subsistence_share(available_pool, len(active_nodes))
            for node in serve_order:
                demand = local_views[node]["demand"]
                alloc = min(demand, equal_ration, available_pool)
                allocations[node] = max(0.0, alloc)
                available_pool -= allocations[node]

            # Distribute any remaining surplus sequentially
            if available_pool > 1e-6:
                for node in serve_order:
                    if available_pool <= 1e-6:
                        break
                    demand = local_views[node]["demand"]
                    unmet = max(0.0, demand - allocations[node])
                    additional = min(unmet, available_pool)
                    if additional > 0:
                        allocations[node] += additional
                        available_pool -= additional

        else:
            # Warabandi Proportional-by-Landholding with Conveyance Loss Compensation
            weights = {
                n: compute_warabandi_weight(
                    local_views[n]["landholding"],
                    local_views[n]["distance_from_head"],
                    self.conveyance_loss_rate,
                )
                for n in active_nodes
            }
            total_weight = sum(weights.values())

            for node in serve_order:
                demand = local_views[node]["demand"]
                proportional_quota = (
                    (weights[node] / total_weight) * state.total_supply
                    if total_weight > 0 else 0.0
                )
                alloc = min(demand, proportional_quota, available_pool)
                allocations[node] = max(0.0, alloc)
                available_pool -= allocations[node]

            # Distribute leftover surplus to satisfy unmet demands
            if available_pool > 1e-6:
                for node in serve_order:
                    if available_pool <= 1e-6:
                        break
                    demand = local_views[node]["demand"]
                    unmet = max(0.0, demand - allocations[node])
                    additional = min(unmet, available_pool)
                    if additional > 0:
                        allocations[node] += additional
                        available_pool -= additional

        # --- Inter-Village Sluice Transfer (Neerkatti Rule) ---
        # Coordinated transfer of upstream surplus to deficient adjacent downstream neighbors
        for u in active_nodes:
            u_view = local_views[u]
            u_dist = u_view["distance_from_head"]
            u_alloc = allocations[u]

            if u_alloc > self.subsistence_level:
                surplus = u_alloc - self.subsistence_level
                for v, nbr_info in u_view["neighbours"].items():
                    if not nbr_info["active"]:
                        continue
                    v_dist = nbr_info.get("distance_from_head", u_dist)
                    if v_dist > u_dist and allocations[v] < self.subsistence_level:
                        transfer_amount = surplus * self.inter_village_transfer_rate
                        transfer_amount = min(transfer_amount, allocations[u] - self.subsistence_level)
                        v_demand = nbr_info["demand"]
                        transfer_amount = min(transfer_amount, max(0.0, v_demand - allocations[v]))

                        if transfer_amount > 0:
                            allocations[u] -= transfer_amount
                            allocations[v] += transfer_amount
                            surplus -= transfer_amount

        return allocations
