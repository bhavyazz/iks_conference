# Water Distribution Network Simulation

### Formalizing Traditional Indian Water-Governance Principles as a Distributed Allocation Framework: A Computational Comparison with Centralized Optimization Under Resource Stress

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Conference](https://img.shields.io/badge/Target-NMKRV%202026-orange.svg)]()

**Target Conference:** International Conference on Indian Knowledge Systems and Sustainable Development Goals (NMKRV, 2026)

---

## 1. Overview

This project presents a research-grade Python simulation framework that **formalizes documented principles from traditional Indian water governance**—specifically **Warabandi** canal rotation (North India) and **Murai** tank-cascade drought-sharing with **Neerkatti** sluice coordination (Tamil Nadu)—into a decentralized allocation algorithm (System A), and benchmarks it against two centralized Linear Programming (LP) baselines (Systems B and C) under compound resource stress.

> **Research Question:**
> *How do computationally formalized principles from traditional Indian water governance compare with centralized optimization under resource scarcity and information disruption?*

The results apply to the tested simulation conditions. No general causal law about decentralized versus centralized systems is asserted. The framework is a computational formalization of qualitative historical principles, not a literal reconstruction of historical systems.

---

## 2. Systems Compared

| Dimension | System A — Distributed IKS-Informed | System B — Centralized Throughput LP | System C — Centralized Fairness LP |
|:---|:---|:---|:---|
| **Architecture** | Decentralized village node agents | Centralized optimization dispatcher | Centralized optimization dispatcher |
| **Information Scope** | **Local only** (own demand, landholding, intake distance, immediate neighbour status) | **Global** (all node demands; neighbour-mean imputation for missing telemetry) | **Global** (all node demands; neighbour-mean imputation for missing telemetry) |
| **Core Algorithm** | Warabandi proportional rotation + conveyance compensation + Murai equal-share subsistence + tail-first scarcity protection + Neerkatti sluice sharing | LP maximising aggregate satisfied volume: max Σxᵢ | LP maximising min fractional satisfaction: max θ + 10⁻⁴ Σxᵢ/d̂ᵢ |
| **Equity Mechanism** | Customary suspension of landholding priority during drought; inter-village sluice transfers | None (purely utilitarian throughput) | Structural max-min fairness constraint |

### Information-Architecture Consistency

The information scope difference between System A and Systems B/C is an **intentional research variable** (information-architecture consistency audit), not an accidental implementation defect.

- **System A:** local demand only, local/neighbour state — no global demand vector
- **Systems B & C:** centralized demand table with estimated values for missing telemetry (active neighbour-mean imputation)

Metric evaluation (efficiency and Jain's fairness) uses realized ground-truth demand **identically** across all three systems. Only the optimizer receives the estimated demand. This is documented in `system_c.py`, `system_b.py`, and `simulation_state.py`.

---

## 3. Institutional Principles vs. Computational Parameters

> **Important Research Framing:**
> The mechanisms modeled here represent a **computational formalization** of qualitative principles documented in historical and socio-hydrological literature. Numerical thresholds (e.g., 70% drought trigger, 50% severe drought trigger, 5% conveyance loss coefficient, 20% transfer rate, 50 ML subsistence baseline, 7-round cycle) are **simulation modeling parameters**, not universal historical constants.

### Key Literature Sources

1. **Warabandi Canal System:** Malhotra, S. P. (1982). *The Warabandi System and Its Infrastructure*. Central Board of Irrigation and Power, New Delhi. State Irrigation Codes (Punjab, Haryana, Rajasthan).
2. **Murai Tank Cascades & Neerkatti Governance:** Mosse, David (2003). *The Rule of Water: Statecraft, Ecology and Collective Action in South India*. Oxford University Press. Palanisami, K. and Easter, K. W. (2000). *Tank Irrigation in the 21st Century*. Discovery Publishing House.

---

## 4. Repository Structure

```
iks/
├── README.md                       # Project documentation (this file)
├── RESEARCH_RESULTS_AUDIT.md       # Full 50-seed experimental audit & findings
├── RESEARCH_FINAL_AUDIT.md         # 12-point pre-paper PASS/FAIL validation checklist
├── requirements.txt                # Pinned Python dependencies
├── main.py                         # CLI orchestrator
├── water_sim/
│   ├── __init__.py
│   ├── network.py                  # Graph topology generation (BA & Directed Cascade)
│   ├── simulation_state.py         # World-state with structural visibility gating
│   ├── system_a.py                 # IKS-informed distributed allocator (Warabandi + Murai)
│   ├── system_b.py                 # Centralized throughput LP (PuLP/HiGHS + SciPy fallback)
│   ├── system_c.py                 # Centralized fairness-aware max-min LP
│   ├── metrics.py                  # Efficiency, Jain's index, resilience, paired statistics
│   ├── experiments.py              # 25-condition stress suite, multi-seed & sensitivity runner
│   └── plotting.py                 # Publication-quality Matplotlib figures (Fig 1–8)
├── results/
│   ├── aggregated_results.csv      # Mean, std, median, 95% CI across 50 seeds
│   ├── paired_differences.csv      # Seed-paired differences & raw p-values
│   ├── sensitivity_results.csv     # Parameter perturbation sweep outputs
│   └── raw/                        # Per-seed raw CSVs (seed_42.csv … seed_91.csv)
└── plots/                          # Generated research figures
```

---

## 5. Experiment Suite

| Parameter | Value |
|:---|:---|
| Seeds | 50 (seeds 42–91) |
| Topologies | 2 (Barabási–Albert scale-free, Directed Cascade tree) |
| Conditions | 25 |
| Rounds per run | 30 |
| Systems evaluated | A, B, C |
| Total allocator invocations | 225,000 |

### Experimental Conditions (25 total)

| Category | Conditions |
|:---|:---|
| Baseline | `normal` (110% supply) |
| Hydrological Drought | `drought` (cumulative 5%/round drawdown from round 15) |
| Telemetry Loss Sweep | `missing_0` → `missing_70` (0%–70% of nodes hide telemetry) |
| Scarcity Sweep | `supply_110` → `supply_50` (110% down to 50% of aggregate demand) |
| Physical Node Failure | `failure_10`, `failure_30` |
| Demand Surge | `demand_shock` (3×–5× spike, rounds 10–13) |
| Compound Hazard | `drought_missing_30`, `severe_drought_missing_50`, `drought_failure_20`, `drought_shock`, `combined_stress` |

---

## 6. Key Results (50-Seed Monte Carlo Means, Barabási–Albert Topology)

> All values are 50-seed means. Results apply to the tested simulation conditions only.

| Scenario | A Efficiency | A Fairness | B Efficiency | B Fairness | C Efficiency | C Fairness |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| `normal` (baseline) | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `supply_50` | 0.500 | **0.923** | 0.500 | 0.512 | 0.500 | **1.000** |
| `missing_50` | **1.000** | 1.000 | 0.911 | 0.977 | 0.913 | 0.981 |
| `missing_70` | **1.000** | 1.000 | 0.882 | 0.971 | 0.885 | 0.975 |
| `combined_stress` | **0.754** | 0.955 | 0.726 | 0.767 | 0.743 | **0.979** |

**Key observations (under tested simulation conditions):**

- System A efficiency is consistent across all telemetry-loss levels, consistent with its local-information architecture.
- Under complete global information (pure scarcity), System C achieves theoretically optimal fairness (J = 1.000) by design of its max-min objective.
- The persistence of System A's efficiency advantage under telemetry disruption after introducing a fairness-aware centralized baseline (System C) supports the interpretation that the observed robustness is associated with the systems' different information architectures rather than being solely attributable to the objective mismatch between Systems A and B.
- Under compound hazard, System A achieves the highest throughput (0.754), while System C achieves the highest fairness (0.979).

### System C Fairness Note

System C's J = 1.000 under `supply_50` is a correct mathematical consequence of its max-min objective—not an evaluation bug. The LP forces equal fractional satisfaction θ across all active nodes. Metric evaluation uses realized ground-truth demand identically across all systems.

---

## 7. Statistical Analysis

| Property | Value |
|:---|:---|
| Test | Paired Wilcoxon signed-rank (paired by seed, topology, condition, metric) |
| p-values | **Raw** (no multiple-comparison correction applied) |
| Total hypothesis tests | **200** (50 rows × 4 paired p-value columns) |
| Limitation | Holm-Bonferroni or equivalent correction should be acknowledged in the final paper |

---

## 8. Installation & Setup

```bash
# Clone the repository
git clone https://github.com/bhavyazz/iks_conference.git
cd iks_conference

# Install dependencies
pip install -r requirements.txt
```

---

## 9. Reproducing Results

### Single-Seed Replication (deterministic, Seed 42)
```bash
python main.py --seed 42
```

### Full 50-Seed Monte Carlo Suite
```bash
python main.py --all --num-seeds 50 --start-seed 42
```

### Parameter Sensitivity Sweep
```bash
python main.py --sensitivity
```

### Custom Conditions or Topologies
```bash
python main.py --conditions normal drought missing_50 supply_60 combined_stress \
               --topologies barabasi_albert directed_cascade
```

Reproducibility verified: identical seed → byte-identical outputs across independent runs.

---

## 10. Generated Figures

| Figure | Description | Key Finding |
|:---|:---|:---|
| `fig1_efficiency_vs_missing_telemetry.png` | Efficiency vs Missing Telemetry (0%–70%) with 95% CI | System A is robust to central data loss; Systems B/C degrade from 1.0 to ~0.88 at 70% missing. |
| `fig2_fairness_vs_supply_scarcity.png` | Jain's Fairness vs Water Scarcity (50%–110%) | System A maintains >0.92 fairness; System B collapses to 0.51 under severe scarcity. |
| `fig3_efficiency_combined_stress.png` | Efficiency under Compound Hazard Regimes | System A maintains higher efficiency when telemetry loss coincides with physical scarcity, under the tested conditions. |
| `fig4_fairness_combined_stress.png` | Fairness under Compound Hazard Regimes | System A sustains high equity under combined shocks (ΔFair = +0.188 vs System B). |
| `fig5_paired_differences_distribution.png` | Paired Differences (Δ = A − B) across 50 seeds | Statistically significant differences in telemetry and scarcity regimes (raw p < 10⁻¹⁴). |
| `fig6_sensitivity_drought_threshold.png` | Drought Trigger Threshold Sensitivity | Results are consistent across trigger thresholds (0.60 to 0.80). |
| `fig7_sensitivity_transfer_rate.png` | Sluice Transfer Fraction Sensitivity | Throughput remains stable across transfer rates (0.10 to 0.30). |
| `fig8_topology_comparison.png` | Topology Invariance: Scale-Free vs Cascade Tree | Core findings hold on both topologies (\|Δ\| < 0.003). |

---

## 11. Limitations

1. **Synthetic Networks** — topologies are abstract benchmarks with no claim to represent actual historical catchments.
2. **Synthetic Demand Generation** — sinusoidal random-walk demands; no measured irrigation data used.
3. **Simplified Discrete-Time Model** — no hydraulic flow simulation, no physical travel-time dynamics, no carry-over storage.
4. **No Hydraulic Flow Simulation** — pipe/channel capacity, pressure losses, and conveyance delays are not modeled.
5. **Neighbour-Mean Imputation** — may over- or underestimate demand under spatially correlated failures.
6. **Limited Topology Diversity** — only two synthetic graph families tested.
7. **Fairness Metric Scope** — Jain's Index measures equality of relative satisfaction ratios, not historical, caste, or social equity.
8. **Intentionally Different Information Architectures** — this is a research variable, not a defect; it must be disclosed in comparative interpretation.
9. **Raw p-values** — 200 hypothesis tests reported without multiple-comparison correction.
10. **Simulation-Scope Generalisability** — all results apply only to the tested simulation conditions.

---

## License

This project is released under the [MIT License](LICENSE).

---

## Citation

If you use this framework, please cite the associated conference paper (forthcoming, NMKRV 2026) and the following key references:

- Mosse, D. (2003). *The Rule of Water: Statecraft, Ecology and Collective Action in South India*. Oxford University Press.
- Palanisami, K. & Easter, K. W. (2000). *Tank Irrigation in the 21st Century*. Discovery Publishing House.
- Malhotra, S. P. (1982). *The Warabandi System and Its Infrastructure*. Central Board of Irrigation and Power, New Delhi.
