# Research Results & Experimental Audit
**Project:** Formalizing Traditional Indian Water-Governance Principles as a Distributed Allocation Framework: A Computational Comparison with Centralized Optimization Under Resource Stress  
**Target Venue:** International Conference on Indian Knowledge Systems and Sustainable Development Goals (NMKRV, 2026)  
**Date:** September 2026  
**Execution Environment:** Multi-seed Monte Carlo Framework ($N = 50$ seeds: 42 to 91, 2 topologies, 25 conditions, 225,000 allocator invocations)

---

## 1. Experimental Setup

* **Network Scale:** 15 nodes per network.
* **Temporal Scope:** 30 simulation rounds per execution.
* **Seed Space:** 50 independent seeds ($42, 43, \dots, 91$). For each seed, identical demand realizations, stochastic noise walks, node failures, telemetry drops, and demand shock locations are delivered to Systems A, B, and C for paired evaluation.
* **Topologies Evaluated:**
  1. `barabasi_albert` (Scale-free complex network benchmark with power-law preferential attachment, $m=2$).
  2. `directed_cascade` (Hierarchical 4-tier directed acyclic cascade benchmark representing upstream-to-downstream tank command branching).
* **Systems Compared:**
  - **System A (Distributed IKS-Informed):** Decentralized allocator formalizing Warabandi rotation with conveyance compensation + Murai equal-share subsistence and tail-first protection under scarcity + Neerkatti inter-village sluice sharing.
  - **System B (Centralized Throughput-Maximizing LP):** Central optimizer solving single-objective max-flow ($\max \sum x_i$) under observed demand bounds.
  - **System C (Centralized Fairness-Aware LP):** Central optimizer solving max-min fractional satisfaction ($\max \theta + 10^{-4} \sum x_i / d_i$) under observed demand bounds.
* **Information & Visibility Boundaries:**
  - **System A:** Queries only `SimulationState.get_local_view(node)` (own demand, own landholding, distance from intake, immediate neighbor active status/demands, and local channel routing counter).
  - **Systems B & C:** Query `SimulationState.get_global_view()`. Under telemetry loss, unobserved demands are estimated via active neighbor-mean proxies.

---

## 2. Experiment Matrix (25 Conditions)

| Category | Conditions | Description |
|:---|:---|:---|
| **Baseline** | `normal` | Supply = 110% demand, no disturbances |
| **Dynamic Hydrological Drought** | `drought` | Cumulative 5%/round supply drawdown starting round 15 |
| **Missing Telemetry Sweep** | `missing_0` to `missing_70` | 0%, 10%, 20%, 30%, 40%, 50%, 60%, 70% of nodes hide demand telemetry from central LP |
| **Controlled Scarcity Sweep** | `supply_110` to `supply_50` | Constant supply ratio at 110%, 100%, 90%, 80%, 70%, 60%, 50% of aggregate demand |
| **Physical Inactivity** | `failure_10`, `failure_30` | 10% and 30% randomly disabled nodes per round |
| **Demand Surge** | `demand_shock` | Single node demand spikes 3.0x–5.0x during rounds 10–13 |
| **Compound Hazard Regimes** | `drought_missing_30` | 70% supply + 30% missing telemetry |
| | `severe_drought_missing_50` | 60% supply + 50% missing telemetry |
| | `drought_failure_20` | 70% supply + 20% node failure |
| | `drought_shock` | 70% supply + 4.0x demand surge |
| | `combined_stress` | 60% supply + 30% missing + 20% failure + 3.5x shock |

---

## 3. Results Summary (50 Seeds Monte Carlo, Barabási–Albert Topology)

| Condition | System A (Eff / Fair) | System B (Eff / Fair) | System C (Eff / Fair) | $\Delta \text{Eff}_{AB}$ [$p$-val] | $\Delta \text{Fair}_{AB}$ [$p$-val] | $\Delta \text{Eff}_{AC}$ [$p$-val] | $\Delta \text{Fair}_{AC}$ [$p$-val] |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `normal` | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 | 0.000 [$1.0$] | 0.000 [$1.0$] | 0.000 [$1.0$] | 0.000 [$1.0$] |
| `drought` | 0.872 / **0.973** | 0.872 / 0.877 | 0.872 / **1.000** | 0.000 [$1.0$] | **+0.095** [$<10^{-14}$] | 0.000 [$1.0$] | -0.027 [$<10^{-14}$] |
| `missing_10` | **1.000** / 1.000 | 0.981 / 0.996 | 0.981 / 0.996 | **+0.019** [$<10^{-14}$] | **+0.004** [$<10^{-14}$] | **+0.019** [$<10^{-14}$] | **+0.004** [$<10^{-14}$] |
| `missing_30` | **1.000** / 1.000 | 0.960 / 0.990 | 0.960 / 0.991 | **+0.040** [$<10^{-14}$] | **+0.010** [$<10^{-14}$] | **+0.040** [$<10^{-14}$] | **+0.009** [$<10^{-14}$] |
| `missing_50` | **1.000** / 1.000 | 0.911 / 0.977 | 0.913 / 0.981 | **+0.089** [$<10^{-14}$] | **+0.023** [$<10^{-14}$] | **+0.087** [$<10^{-14}$] | **+0.019** [$<10^{-14}$] |
| `missing_70` | **1.000** / 1.000 | 0.882 / 0.971 | 0.885 / 0.975 | **+0.118** [$<10^{-14}$] | **+0.029** [$<10^{-14}$] | **+0.115** [$<10^{-14}$] | **+0.025** [$<10^{-14}$] |
| `supply_70` | 0.700 / **0.923** | 0.700 / 0.712 | 0.700 / **1.000** | 0.000 [$1.0$] | **+0.211** [$<10^{-14}$] | 0.000 [$1.0$] | -0.077 [$<10^{-14}$] |
| `supply_60` | 0.600 / **0.932** | 0.600 / 0.613 | 0.600 / **1.000** | 0.000 [$1.0$] | **+0.320** [$<10^{-14}$] | 0.000 [$1.0$] | -0.068 [$<10^{-14}$] |
| `supply_50` | 0.500 / **0.923** | 0.500 / 0.512 | 0.500 / **1.000** | 0.000 [$1.0$] | **+0.412** [$<10^{-14}$] | 0.000 [$1.0$] | -0.077 [$<10^{-14}$] |
| `drought_missing_30` | **0.700** / 0.927 | 0.675 / 0.710 | 0.695 / **0.978** | **+0.025** [$<10^{-14}$] | **+0.217** [$<10^{-14}$] | **+0.005** [$<10^{-14}$] | -0.051 [$<10^{-14}$] |
| `severe_drought_missing_50`| **0.600** / 0.932 | 0.558 / 0.616 | 0.595 / **0.946** | **+0.042** [$<10^{-14}$] | **+0.317** [$<10^{-14}$] | **+0.005** [$<10^{-14}$] | -0.014 [$<10^{-14}$] |
| `combined_stress` | **0.754** / 0.955 | 0.726 / 0.767 | 0.743 / **0.979** | **+0.028** [$<10^{-14}$] | **+0.188** [$<10^{-14}$] | **+0.010** [$<10^{-14}$] | -0.025 [$<10^{-14}$] |

---

## 4. Key Comparative Insights

1. **Information Robustness:** System A's throughput is completely immune to central telemetry loss ($1.000$ efficiency across 0% to 70% missing data), whereas both Centralized Throughput LP (System B) and Centralized Fairness LP (System C) degrade significantly (falling to $\approx 0.88$ at 70% missing data).
2. **Centralized Fairness vs. Distributed Fairness:**
   - Under *perfect global information* (pure scarcity without telemetry loss), System C achieves theoretical perfection ($J = 1.000$), while System A maintains strong customary equity ($J \approx 0.923$).
   - When telemetry is corrupted or incomplete, System C loses throughput efficiency and its fairness bounds degrade. Under compound hazards, System A achieves the **highest throughput ($0.754$)** while sustaining high distributive equity ($0.955$).
3. **Throughput Invariance:** System A matches both centralized LPs in aggregate volume delivery across all pure scarcity levels; the observed results indicate that the customary scarcity sharing formalization incurs no measurable throughput penalty under the tested simulation conditions.

---

## 5. Parameter Sensitivity Findings

Across 10 seeds:
* **Drought Trigger Threshold ($0.60 \rightarrow 0.80$):** System A fairness remains stable ($0.966 \rightarrow 0.976$).
* **Severe Drought Tail-First Threshold ($0.40 \rightarrow 0.60$):** Under 50% supply, fairness is consistently $0.926$.
* **Inter-Village Sluice Transfer Rate ($0.10 \rightarrow 0.30$):** Under 60% supply, fairness remains steady at $0.935$.
* **Conveyance Loss Rate ($0.00 \rightarrow 0.10$):** In normal supply, efficiency and fairness remain $1.000$.

---

## 6. Topology Invariance

* Scale-free network (`barabasi_albert`) and hierarchical cascade (`directed_cascade`) exhibit virtually identical metrics across all 25 conditions ($|\Delta| < 0.003$).

---

## 7. Limitations & Methodological Assumptions

1. **Synthetic Networks:** Network topologies (`barabasi_albert`, `directed_cascade`) are abstract computational benchmarks with no claim to represent actual historical catchments.
2. **Synthetic Demand Generation:** Per-node demands are generated via sinusoidal random walks; they do not correspond to measured irrigation data.
3. **Simplified Discrete-Time Allocation:** Each round is independent; the model does not simulate hydraulic flow, physical travel-time dynamics, or carry-over storage.
4. **No Hydraulic Flow Simulation:** Water routing ignores pipe/channel capacity, pressure losses, and physical conveyance delays.
5. **Neighbour-Mean Imputation:** Systems B and C estimate missing demands via the active-neighbour mean, which may systematically over- or underestimate true demand under spatially correlated failures.
6. **Limited Topology Diversity:** Only two synthetic graph families are tested; results may not generalise to other network structures.
7. **Fairness Metric Scope:** Jain's Fairness Index measures equality of relative demand satisfaction ratios, not historical, caste, or social equity.
8. **Intentionally Different Information Architectures:** System A uses strictly local information; Systems B and C use global demand tables with imputation. This is an intentional research variable (information-architecture consistency audit), not an accidental implementation defect, and must be disclosed in any comparative interpretation.
9. **Simulation-Scope Generalisability:** All results apply only to the tested simulation conditions (50 seeds, 2 topologies, 25 conditions, 30 rounds). No general causal law about decentralised versus centralised systems is asserted.
10. **Multiple Comparisons:** 200 hypothesis tests (50 condition-topology rows × 4 paired p-values per row) are currently reported with raw p-values. Multiple-comparison correction (e.g., Holm-Bonferroni) should be acknowledged as a limitation or applied in the final statistical analysis.

---

## 8. Exact Reproducibility Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run single-seed replication (Seed 42)
python main.py --seed 42

# Run full 50-seed Monte Carlo suite (Systems A, B, C across both topologies)
python main.py --all --num-seeds 50 --start-seed 42
```
