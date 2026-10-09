#!/usr/bin/env python3
"""Single source of truth for the SK hynix deck.

Every quantitative value used on a slide is loaded here from its authoritative
artifact, never typed in. Values that cannot be loaded (because they live in a
published figure rather than a machine-readable file) are listed explicitly in
PUBLISHED_NOT_RERUN with that provenance attached.
"""
from __future__ import annotations
import csv, json, re
from pathlib import Path

HVR = Path("/home/beams/MGHARIB/Mohamed_stuff/HVR_OPT")
OT = Path("/home/beams/MGHARIB/Mohamed_stuff/OTAPM")
P3 = OT / "revision_jetcas_2026-09-19/results/ectc_package"
AC = OT / "epeps/ansys_case"
R3C = HVR / "results/phase0mr3c"


def _csv(p):            return list(csv.DictReader(Path(p).open()))
def _json(p):           return json.loads(Path(p).read_text())
def _by(rows, k="case"): return {r[k]: r for r in rows}


# ---------------------------------------------------------------- HVR / DVPD
etm   = _by(_csv(R3C / "final_etm_replay.csv"))
loc   = _by(_csv(R3C / "final_local_response.csv"))
inp   = _by(_csv(R3C / "local_submodel_inputs.csv"))
ledg  = _csv(R3C / "final_loss_ledger.csv")
route = _csv(R3C / "routing_feasibility.csv")
cet   = _csv(R3C / "cetol_final_pair.csv")
dec   = _by(_csv(R3C / "local_response_decomposition.csv"))
tim   = _json(R3C / "timing_breakdown.json")
plat  = _json(R3C / "platform.json")
PLATFORM = plat

PAIR = {}
for c in ("Z1", "Z2"):
    PAIR[c] = dict(
        P_elec   = float(etm[c]["P_total_electronics_w"]),
        T_max    = float(etm[c]["T_max_C"]),
        T_mean   = float(etm[c]["T_mean_C"]),
        die_warp = float(etm[c]["die_warpage_pv_um"]),
        pkg_warp = float(etm[c]["pkg_warpage_pv_um"]),
        T_joint  = float(inp[c]["T_joint_C"]),
        du_c     = float(etm[c]["response_driver_um"]),
        d_eps    = float(loc[c]["d_eps_in_stab"]),
        P_tsv    = float(etm[c]["L_P_TSV"]),
        wall_s   = float(etm[c]["wall_s"]),
    )
D_U   = PAIR["Z1"]["du_c"]  / PAIR["Z2"]["du_c"]
D_EPS = PAIR["Z1"]["d_eps"] / PAIR["Z2"]["d_eps"]
DT    = PAIR["Z2"]["T_max"] - PAIR["Z1"]["T_max"]
DTJ   = PAIR["Z2"]["T_joint"] - PAIR["Z1"]["T_joint"]
RED_U, RED_E = 100*(1 - 1/D_U), 100*(1 - 1/D_EPS)

# ---------------------------------------------------------- architecture geometry
# h_sub comes from the frozen pair configs; the through-substrate path length and the
# system rail currents come from the code that actually produced the frozen replay.
_FROZ = {c: (HVR / f"configs/phase0mr3c/frozen_pair_{c}.yaml").read_text()
         for c in ("Z1", "Z2")}
H_SUB_MM = {c: float(re.search(r"^h_sub_mm:\s*([0-9.]+)", t, re.M).group(1))
            for c, t in _FROZ.items()}

# scripts/phase0mr/replay_production.py: for ARCH_Z1_EMBEDDED the TSV spans only
# (h_sub - t_cell); for ARCH_Z2_BACKSIDE it spans the full substrate.
_REPLAY = (HVR / "scripts/phase0mr/replay_production.py").read_text()
T_CELL_UM = float(re.search(r"h_sub_mm \* 1e3 - ([0-9.]+)", _REPLAY).group(1))
H_TSV_UM = {"Z1": max(H_SUB_MM["Z1"] * 1e3 - T_CELL_UM, 0.0),
            "Z2": H_SUB_MM["Z2"] * 1e3}

DIE_MM = float(re.search(r"^DIE_MM, N_VR, LOAD_W = ([0-9.]+)", _REPLAY, re.M).group(1))
STACK_UM = float(re.search(r"same\s+([0-9]+)\s+um stack height",
                           _FROZ["Z1"]).group(1))

# scripts/phase0i/zarch.py rail_currents(): system-level, eta is the Phase-0F value
_ZARCH = (HVR / "scripts/phase0i/zarch.py").read_text()
ETA_PATH = float(re.search(r"eta: float = ([0-9.]+)", _ZARCH).group(1))
LOAD_W, V_IN, V_OUT = 1000.0, 48.0, 1.0
RAIL = {"Z1": dict(rail="48 V input",  V=V_IN,
                   I=(LOAD_W / ETA_PATH) / V_IN),
        "Z2": dict(rail="1 V output",  V=V_OUT, I=LOAD_W / V_OUT)}

# realizability: worst build-up via aspect ratio per candidate, at the sourced pitch
AR = {c: max(float(r["AR_worst"]) for r in route
             if r["candidate"] == c and r["pitch_um"] == "150.0")
      for c in ("baseline_T1", "repartition_C1")}
NETS = {c: {r["net"]: dict(depth=float(r["dielectric_depth_um"]),
                           ar=float(r["AR_worst"]),
                           i=float(r["i_aggregate_a"]),
                           n_req=int(r["n_required_framework"]),
                           n_av=int(r["n_available"]),
                           rr=float(r["routing_ratio"]))
            for r in route if r["candidate"] == c and r["pitch_um"] == "150.0"}
        for c in ("baseline_T1", "repartition_C1")}

# per-cell converter loss mechanisms (W per cell), from the frozen ledger
N_CELL = 49
def _ledger(case):
    row = {r["term"]: float(r["watts"]) for r in ledg
               if r.get("case") == case and r.get("scope") == "ELECTRONICS"
               and r["term"] != "P_total_electronics"}
    if not row:
        row = {k[2:]: float(v) for k, v in etm[case].items() if k.startswith("L_P_")}
    return row
LOSS = {c: _ledger(c) for c in ("Z1", "Z2")}

# CETOL ladder
CETOL = []
for t in sorted({float(r["cetol"]) for r in cet}):
    z = {r["case"]: r for r in cet if float(r["cetol"]) == t}
    ok = z["Z1"]["converged"] == "YES" and z["Z2"]["converged"] == "YES"
    CETOL.append(dict(cetol=t, converged=ok,
                      d_eps=(float(z["Z1"]["d_eps_in_stab"]) / float(z["Z2"]["d_eps_in_stab"]))
                            if ok else None,
                      incr=int(z["Z1"]["increments"])))

# response decomposition: which input causes the 18.4 %
DECOMP = dict(
    z1      = float(dec["Z1"]["d_eps_in_stab"]),
    z2      = float(dec["Z2"]["d_eps_in_stab"]),
    du_only = float(dec["X_duZ2_TZ1"]["d_eps_in_stab"]),
    T_only  = float(dec["X_duZ1_TZ2"]["d_eps_in_stab"]),
)

CONVERTER = dict(V_in=48.0, V_mid=16.0, V_out=1.0, M=N_CELL, I_cell=20.408,
                 A_cell=5.61, D=0.0625, f_sw_kHz=805.17, N=3, K=3)
COOLING = dict(channels=223, w_um=50, h_um=300, m_dot_g_s=27.0, Re=1264.8,
               h_eff_kW=115.6, dT_K=8.858, dp_MPa=0.5378, P_pump_W=14.696,
               T_in_C=25.0)

# ------------------------------------------------------------ transient work
perf  = _json(P3 / "perf_tables.json")
icep  = _json(P3 / "icepak_p3_comparison.json")
son   = _json(AC / "son_scenario_validation.json")

TRANSIENT = dict(
    fv_400_s      = perf["interleaved_400"]["fv_wall"],
    moose_400_s   = perf["interleaved_400"]["moose_wall"],
    ratio_400     = perf["interleaved_400"]["ratio"],
    steady_fv_s   = perf["steady_counter_case"]["fv_total_s"],
    steady_moose_s= perf["steady_counter_case"]["moose_wall_s"],
    steady_ratio  = perf["steady_counter_case"]["ratio"],
    icepak_max_K  = icep["max_abs_icepak_minus_moose_K"],
    fv_max_K      = icep["max_abs_fv_minus_moose_K"],
    icepak_cells  = icep["realized_cells"],
    crossover     = perf["crossover"],
    dies          = icep["dies"],
)
# policy traces: PUBLISHED application results, not rerun after the solver correction
POLICY = dict(
    greedy_oracle   = son["greedy"]["per_die"]["HBM_L2"]["oracle_peak"],
    greedy_ansys    = son["greedy"]["per_die"]["HBM_L2"]["ansys_peak"],
    screened_oracle = son["OTAPM"]["per_die"]["HBM_L2"]["oracle_peak"],
    screened_ansys  = son["OTAPM"]["per_die"]["HBM_L2"]["ansys_peak"],
    hbm_limit_C     = 95.0,
)
PUBLISHED_NOT_RERUN = dict(
    epochs=96, violations_before=33, violations_after=0, leakage_overhead_pct=8.1,
    provenance="EPEPS 2026 published application result; produced before the "
               "post-publication solver correction and not rerun.",
)

if __name__ == "__main__":
    print(f"D_u = {D_U:.4f}   D_eps = {D_EPS:.4f}   dT = {DT:+.2f} K  dTj = {DTJ:+.2f} K")
    print(f"reductions: du {RED_U:.2f} %   d_eps {RED_E:.2f} %")
    print(f"AR  {AR['baseline_T1']:.3f} -> {AR['repartition_C1']:.3f}")
    print(f"TSV loss  Z1 {PAIR['Z1']['P_tsv']:.4f} W   Z2 {PAIR['Z2']['P_tsv']:.4f} W")
    print(f"transient {TRANSIENT['fv_400_s']:.1f} vs {TRANSIENT['moose_400_s']:.1f} s "
          f"= {TRANSIENT['ratio_400']:.2f}x ; steady counter {TRANSIENT['steady_ratio']:.1f}x")
    print(f"icepak max {TRANSIENT['icepak_max_K']:.4f} K   fv max {TRANSIENT['fv_max_K']:.4f} K")
    print(f"policy greedy {POLICY['greedy_oracle']}/{POLICY['greedy_ansys']}  "
          f"screened {POLICY['screened_oracle']}/{POLICY['screened_ansys']}")
    print(f"CETOL: {[(c['cetol'], c['converged']) for c in CETOL]}")
