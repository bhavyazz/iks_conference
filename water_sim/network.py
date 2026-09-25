"""
network.py
----------
Builds the village water-distribution network (NetworkX graph) and provides
per-round demand generation with seasonal sinusoidal variation and random-walk noise.

Topology options:
1. "barabasi_albert"  – Power-law degree distribution (scale-free complex network benchmark).
2. "directed_cascade" – Synthetic hierarchical cascade / branching network representing
                        upstream-to-downstream tank / canal distribution levels.

Note: Topologies are abstract computational benchmarks motivated by hierarchical
irrigation structures, not literal reconstructions of specific historical cascades.
"""

from __future__ import annotations

import math
import random
from typing import Literal

import networkx as nx

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NUM_NODES   = 15
NUM_ROUNDS  = 30

# Base demand range (units, e.g. ML/round)
BASE_DEMAND_MIN = 80.0
BASE_DEMAND_MAX = 160.0

# Seasonal sinusoidal amplitude as a fraction of base demand
SEASONAL_AMP_FRACTION = 0.25

# Random-walk noise std-dev as a fraction of base demand
NOISE_FRACTION = 0.05

# Total supply relative to total demand (normally >= 1.0)
SUPPLY_DEMAND_RATIO = 1.10   # 10 % slack in baseline unconstrained state


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_network(
    seed: int = 42,
    topology: Literal["barabasi_albert", "directed_cascade"] = "barabasi_albert",
) -> nx.Graph:
    """
    Return a connected graph of NUM_NODES village nodes with assigned attributes.

    Each node carries:
        - 'base_demand'        : fixed per-round base water need (ML)
        - 'seasonal_phase'     : phase offset for sinusoidal variation
        - 'landholding'        : land area entitlement units (1.0 to 10.0)
        - 'distance_from_head' : topological shortest-path hops from intake (Node 0)
        - 'topology'           : name of network topology model used

    Parameters
    ----------
    seed : int
        RNG seed for reproducibility.
    topology : "barabasi_albert" | "directed_cascade"
        Graph structure model.

    Returns
    -------
    G : nx.Graph
    """
    rng = random.Random(seed)

    if topology == "barabasi_albert":
        # BA graph: power-law attachment with m=2
        G = nx.barabasi_albert_graph(NUM_NODES, m=2, seed=seed)
        head_node = 0
    elif topology == "directed_cascade":
        # Hierarchical cascade structure (root intake -> head reaches -> mid reaches -> tail reaches)
        # Undirected underlying graph for bidirectional inter-village adjacency queries
        G = nx.Graph()
        G.add_nodes_from(range(NUM_NODES))
        head_node = 0

        # Tier 0 (Intake): Node 0
        # Tier 1 (Head-reach tanks): Nodes 1, 2
        G.add_edge(0, 1)
        G.add_edge(0, 2)

        # Tier 2 (Mid-reach branch tanks): Nodes 3, 4, 5, 6, 7
        G.add_edge(1, 3)
        G.add_edge(1, 4)
        G.add_edge(2, 5)
        G.add_edge(2, 6)
        G.add_edge(2, 7)
        # Lateral connecting channel between mid-reach nodes
        G.add_edge(4, 5)

        # Tier 3 (Tail-end command tanks): Nodes 8, 9, 10, 11, 12, 13, 14
        G.add_edge(3, 8)
        G.add_edge(3, 9)
        G.add_edge(4, 10)
        G.add_edge(5, 11)
        G.add_edge(6, 12)
        G.add_edge(7, 13)
        G.add_edge(7, 14)
        # Lateral channel at tail-end tier
        G.add_edge(9, 10)
        G.add_edge(11, 12)
    else:
        raise ValueError(f"Unknown topology: {topology}. Choose 'barabasi_albert' or 'directed_cascade'.")

    # Compute shortest path distances from canal head / root intake
    distances = nx.shortest_path_length(G, source=head_node)

    for node in G.nodes():
        G.nodes[node]['base_demand']        = rng.uniform(BASE_DEMAND_MIN, BASE_DEMAND_MAX)
        G.nodes[node]['seasonal_phase']     = rng.uniform(0, 2 * math.pi)
        G.nodes[node]['landholding']        = rng.uniform(1.0, 10.0)  # Landholding units 1-10
        G.nodes[node]['distance_from_head'] = distances.get(node, 0)
        G.nodes[node]['topology']           = topology

    return G


# ---------------------------------------------------------------------------
# Demand generation
# ---------------------------------------------------------------------------

def compute_demand_for_round(
    G: nx.Graph,
    round_idx: int,
    rng: random.Random,
    noise_type: str = "random_walk",
    walk_state: dict | None = None,
) -> dict[int, float]:
    """
    Compute water demand for every node for a given round.

    Demand model:
        demand(v, t) = base(v)
                       + seasonal(v, t)          # sinusoidal term
                       + noise(v, t)             # random perturbation
                       [clamped to >= 1.0]

    Parameters
    ----------
    G          : network graph (read-only)
    round_idx  : 0-based round number
    rng        : seeded random.Random instance
    noise_type : "random_walk" | "iid"
    walk_state : mutable dict {node: walk_value} for random-walk continuity

    Returns
    -------
    demands : dict {node_id: demand_value}
    """
    if walk_state is None:
        walk_state = {}

    demands: dict[int, float] = {}
    for v in G.nodes():
        base   = G.nodes[v]['base_demand']
        phase  = G.nodes[v]['seasonal_phase']

        # Seasonal: one full sinusoidal cycle over NUM_ROUNDS rounds
        seasonal = base * SEASONAL_AMP_FRACTION * math.sin(
            2 * math.pi * round_idx / NUM_ROUNDS + phase
        )

        # Noise term
        noise_std = base * NOISE_FRACTION
        if noise_type == "random_walk":
            prev = walk_state.get(v, 0.0)
            step = rng.gauss(0, noise_std)
            # Drift 10% back toward zero each round for bounded variance
            new_walk = prev * 0.90 + step
            walk_state[v] = new_walk
            noise = new_walk
        else:  # iid Gaussian
            noise = rng.gauss(0, noise_std)

        demands[v] = max(1.0, base + seasonal + noise)

    return demands


# ---------------------------------------------------------------------------
# Supply calculation
# ---------------------------------------------------------------------------

def compute_total_supply(
    demands: dict[int, float],
    ratio: float = SUPPLY_DEMAND_RATIO,
) -> float:
    """
    Return total available supply = ratio * total demand.
    """
    return sum(demands.values()) * ratio
