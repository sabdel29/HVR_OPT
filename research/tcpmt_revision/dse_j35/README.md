# Regulator-count design-space exploration at the paper specification (J = 3.5 A/mm2)

`sweep_etm.py` is Salma Abdelzaher's thesis partitioning study (Salma_Thesis/analysis/
system_partitioning_comparison/scripts/partition_sweep_v2.py) with four settings changed to the
ETM paper's specification: J_TARGET 3.5 A/mm2 (was 2.0), RIPPLE_FACTOR 0.5 (the design call of
scripts/phase0f/kw1.py), the fixed architecture N=3, K=3 (was 3, 2), and the engine/output paths
(a private copy of the Scalable_Integrated_VR engine; byte-identical HVR_FULL_OPT_* files).
Run 2026-11-13 on pinback (load ~130): 17 counts, ~4 min, one core.

    python -B sweep_etm.py --counts 36,40,42,45,48,49,50,52,56,60,64,70,76,84,92,100,120 --tag etm35

Cases: A fixed+continuous, B re-synthesized+continuous, C fixed+discrete, D re-synthesized+
discrete (90 EPC devices). At M = 49 case D returns the integration-study regulator exactly
(N3K3K_A2, EPC2014C/EPC2057, 805.17 kHz, 91.45 W conversion). Optimum (D): M = 76, N2K2K_A1.
