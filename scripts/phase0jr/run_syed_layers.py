#!/usr/bin/env python3
"""Phase-0J-R Sec.5 -- run the architectures on the graded mesh and extract Syed's metric.

Averaging volume matched to the primary source: the two 25 um solder layers at the package and
board faces, two 12.5 um elements across each. Mesh convergence is checked on the mid-region
refinement, with the target PREDECLARED at < 10 % change in M4 over the final refinement --
the same target Phase 0I used for its own metric.
"""
from __future__ import annotations
import csv, re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0jr", "phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from creep_metric import creep_series, cycle_creep, OUT                     # noqa: E402
from cycle_audit import cycle_quantities, per_element_series               # noqa: E402
from decompose import parse_temperature, parse_tensors                     # noqa: E402
from graded_joint import build_joint_graded                                # noqa: E402
from decompose import material                                            # noqa: E402
from joint import run as run_ccx, write_inp                                # noqa: E402

WD = OUT / "syedlayer"
WD.mkdir(parents=True, exist_ok=True)
# SIX cycles, and the STABILISED cycle reported is the PENULTIMATE one.
# The final simulated cycle is ~15 % low in every run -- identically in the
# 4-cycle and 6-cycle runs, whose cycle 3 values agree to 4 figures (8.86e-3).
# Physics cannot know which cycle is last, so this is an output artifact of the
# final step and that cycle is discarded rather than reported.
N_CYC, DWELL, T_OFF = 6, 300.0, 25.0
STAB_CYCLE = 5          # 1-based
CASES = [("Z1", "ARCH_Z1_EMBEDDED", 1.30, 2.7485664848789826, 82.8604875),
         ("Z2", "ARCH_Z2_BACKSIDE", 0.30, 2.0796010434696357, 81.8453000000000),
         ("Z4", "ARCH_Z4_POWER_DIE", 0.30, 2.9840047587428530, 81.1017812499999)]


def run_case(tag, du_um, t_hot, n_mid=6, kind="EPC"):
    m = build_joint_graded(6, n_mid)
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", t_hot, du_um / 1000.0, DWELL)); t += DWELL
        cyc.append((f"c{k}off", T_OFF, 0.0, DWELL)); t += DWELL
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, material(kind), cyc, cetol=1e-2,
              procedure=("STATIC" if kind == "EP" else "VISCO"))
    s = p.read_text()
    # The 12.5 um layer elements make the Norton integration stiff: the material routine
    # requests pnewdt cutbacks until the increment falls below the floor and the solve aborts.
    # Loosen CETOL to the value Phase 0I showed changes the answer by 0.02 %, soften the
    # opening increment, and drop the floor. This is a SOLVER-CONTROL change, not a physics
    # change, and the mesh-convergence study below is what guards it.
    s = re.sub(r"\*VISCO, CETOL=[0-9.e-]+", "*VISCO, CETOL=0.05", s)
    s = re.sub(r"^0\.002, 300, 1e-06, 15$", "1e-5, 300, 1e-12, 10", s, flags=re.M)
    # print the tensors and PEEQ over the SYED LAYERS, not only the Phase-0I core
    s = s.replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                  "*EL PRINT, ELSET=ESYED\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E",
                  "*NODE PRINT, NSET=NBOT\nNT")
    # element sets must exist in the deck
    for nm in ("ESYED", "ESYEDCORE"):
        if f"*ELSET, ELSET={nm}" not in s:
            ids = m.sets[nm]
            blk = [f"*ELSET, ELSET={nm}"] + [
                ", ".join(str(e) for e in ids[i:i + 8]) for i in range(0, len(ids), 8)]
            s = s.replace("*SOLID SECTION", "\n".join(blk) + "\n*SOLID SECTION", 1)
    p.write_text(s)
    run_ccx(p, threads=6)
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        return None
    # M4 and M5 are taken from the SOLVER'S OWN output, not from the Norton reconstruction.
    # The probe (probe_viscoplastic.py) proved that CalculiX's combined *PLASTIC + *CREEP is a
    # pure viscoplastic OVERSTRESS model with NO rate-independent plastic strain: at 25 MPa
    # against a 15.2 MPa yield, PEEQ at the first output is 1.5e-11 where a rate-independent
    # model would need 5.2e-2. Every increment of PEEQ is therefore creep, so
    #     M4 == M1 == d(PEEQ)        and        M5 == M3 == the inelastic work integral
    # identically for this constitutive model. Reconstructing the Norton integral is only a
    # cross-check, and it is numerically unusable in the high-stress interface layer where the
    # sigma^8 rate makes the output-interval quadrature diverge.
    data = parse_tensors(d, set(m.sets["ESYED"]))
    temps = parse_temperature(d)
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = per_element_series(data, vols, temps)
    te = ends[STAB_CYCLE - 1]
    out = {}
    for lab, es in (("SYED_full", "ESYED"), ("SYED_core", "ESYEDCORE")):
        sub = set(m.sets[es])
        s2 = {e: v for e, v in ser.items() if e in sub}
        v2 = {e: v for e, v in vols.items() if e in sub}
        if not s2:
            continue
        q = cycle_quantities(s2, v2, te - 2 * DWELL, te)
        qp = cycle_quantities(s2, v2, te - 4 * DWELL, te - 2 * DWELL)
        if not q:
            continue
        out[lab] = {"M4_creep_strain": q["d_peeq_per_cycle"],
                    "M5_creep_energy_MJ_per_m3": q["inelastic_work_MJ_per_m3"],
                    "M2_range": q["range_eq_inelastic"],
                    "d_peeq": q["d_peeq_per_cycle"],
                    "vol_mm3": sum(v2.values()),
                    "stab_pct": (100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"])
                                 / qp["d_peeq_per_cycle"]) if qp and qp["d_peeq_per_cycle"]
                    else float("nan")}
    return out


def main() -> int:
    rows = []
    for short, arch, h, du, th in CASES:
        for n_mid in (6, 10):
            tag = f"{short}_nm{n_mid}"
            print(f"  {tag:12} du={du:.3f} T_hot={th:.2f}", flush=True)
            o = run_case(tag, du, th, n_mid=n_mid)
            if not o or "SYED_full" not in o:
                print("      FAILED"); continue
            f_, c_ = o["SYED_full"], o.get("SYED_core", {})
            rows.append({"arch": arch, "short": short, "h_sub_mm": h, "n_mid": n_mid,
                         "du_corner_um": du, "T_hot_C": th,
                         "M4_syed_layer": f_["M4_creep_strain"],
                         "M5_syed_layer_MJ_per_m3": f_["M5_creep_energy_MJ_per_m3"],
                         "M1_dpeeq_syed_layer": f_["d_peeq"],
                         "M2_range_syed_layer": f_["M2_range"],
                         "M4_over_M1": 1.0,
                         "M4_syed_layer_core_only": c_.get("M4_creep_strain", ""),
                         "stab_pct": f_["stab_pct"], "vol_mm3": f_["vol_mm3"]})
            print(f"      M4={f_['M4_creep_strain']:.4e}  M5={f_['M5_creep_energy_MJ_per_m3']:.4f}"
                  f"  M4/M1={f_['M4_creep_strain']/f_['d_peeq']:.3f}  stab={f_['stab_pct']:.2f}%",
                  flush=True)
    f = OUT / "syed_layer_metrics.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}")
    print("\nMESH CONVERGENCE on M4 over the Syed layer (target: < 10 % final step)")
    for short in ("Z1", "Z2", "Z4"):
        rs = sorted([r for r in rows if r["short"] == short], key=lambda r: r["n_mid"])
        if len(rs) >= 2:
            d = 100 * abs(rs[-1]["M4_syed_layer"] - rs[-2]["M4_syed_layer"]) / rs[-2]["M4_syed_layer"]
            print(f"  {short}: " + "  ".join(f"n_mid={r['n_mid']}: {r['M4_syed_layer']:.4e}"
                                             for r in rs) + f"   final step {d:.2f} %"
                  + ("  CONVERGED" if d < 10 else "  NOT CONVERGED"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
