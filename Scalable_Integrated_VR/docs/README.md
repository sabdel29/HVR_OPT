# `docs/`

| File | Contents |
|---|---|
| `QIF Finals Presentation Script.pdf` / `.docx` | Full 12-minute spoken script for the **Qualcomm Innovation Fellowship finals, March 2026** — Salma Abdelzaher & Mohamed Gharib, HiPerCAS Lab (Dr. Inna Partin-Vaisband), UIC. |

This is the best single explanation of *why* the code is shaped the way it is. Slide guide:

| Slides | Topic |
|---|---|
| 2 | Why vertical power delivery — IR drop **and** `L·di/dt` droop |
| 3 | The system-level co-optimization thesis |
| 4 | Architecture space: direct 48→1 V vs intermediate rail vs in-package |
| 5 | Why not a plain buck (~2 % duty cycle) → **hybrid SC + multiphase buck** |
| **6** | **HVR power-loss models** — what `HVR_FULL_OPT_EPC_V2.py` implements; quoted at 94 % accuracy vs simulation |
| **7** | **PDN routing-loss model** — the parallel-resistance network in `Framework*.py` |
| **8** | **Optimal VR count** — the routing-loss vs VR-area trade-off the sweeps resolve |
| 9–11 | Control layer: predictive control, bandit-driven power gating (IEEE EPEPS 2025), online adaptive controller |
| 14 | One-year roadmap, targeting a validated 1 kW VPD configuration at >80 % system efficiency |
| Appendix | Anticipated Q&A |

**Note:** slides 9–11 (ML-assisted control, bandit power gating) describe work that is
**not** in this repository — this codebase covers the modelling and architectural
co-optimization of slides 5–8.
