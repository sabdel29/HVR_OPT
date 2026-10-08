#!/usr/bin/env python3
"""Phase-0K Sec.10/11/29 -- can any experiment discriminate the strain and energy life laws?

THE ALGEBRA FIRST, because it determines what the simulations need to look for.

    strain law   N = 1/(C * eps)          energy law   N = 1/(W * w)

Given ONE measured life at ONE condition, both laws fit it EXACTLY:
    C_fit = 1/(N_test * eps_test)        W_fit = 1/(N_test * w_test)
so one condition cannot discriminate. It re-labels the disagreement, it does not resolve it.

With TWO conditions A and B the laws predict DIFFERENT life ratios:
    strain:  N_A/N_B = eps_B/eps_A       energy:  N_A/N_B = w_B/w_A
and the DISCRIMINATION POWER is exactly

    D = (eps_B/eps_A) / (w_B/w_A) = (w/eps)_A / (w/eps)_B

So an experiment discriminates ONLY to the extent that the two conditions differ in w/eps.
Maximising damage is irrelevant; maximising the SPREAD IN w/eps is the whole design problem.

This script computes w/eps over candidate test conditions and ranks every pair by D against
the experimental scatter a realistic specimen count can achieve.
"""
from __future__ import annotations
import csv, itertools, math, re, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0k", "phase0jr", "phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from cycle_audit import cycle_quantities, per_element_series               # noqa: E402
from decompose import material, parse_temperature, parse_tensors           # noqa: E402
from graded_joint import build_joint_graded                                # noqa: E402
from joint import run as run_ccx, write_inp                                # noqa: E402

OUT = R / "results" / "phase0k"
WD = OUT / "disc"
WD.mkdir(parents=True, exist_ok=True)
N_CYC, STAB = 6, 5

# Baseline operating point from the global model (Phase 0I): du at dT = 57.86 K for Z1.
DU_REF_Z1, DT_REF_Z1 = 2.7485664848789826, 57.8604875
DU_REF_Z2, DT_REF_Z2 = 2.0796010434696357, 56.8453000000000

# Candidate BOARD-LEVEL test conditions. du is scaled linearly with dT from the operating
# point -- a first-order CTE-mismatch model, stated as an assumption, not a measurement.
CONDS = [
    ("OP_BASELINE",   25.0,  82.86, 300.0, "the DVPD operating cycle itself"),
    ("JEDEC_A104",   -40.0, 125.0,  900.0, "JESD22-A104-B as applied: 15-min dwells"),
    ("COLD_SHALLOW", -40.0,  25.0,  300.0, "cold half-range: high yield stress, low T"),
    ("HOT_SHALLOW",   55.0, 125.0,  300.0, "hot half-range: low yield stress, high T"),
    ("SMALL_DT",      25.0,  55.0,  300.0, "small excursion about the operating mean"),
    ("LONG_DWELL",    25.0,  82.86, 900.0, "operating cycle, 15-min dwells"),
    ("SHORT_DWELL",   25.0,  82.86,  30.0, "operating cycle, 30-s dwells"),
    ("WIDE_HOT",      25.0, 125.0,  300.0, "wide range, warm minimum"),
]


def run_case(tag, du_um, t_min, t_max, dwell, n_mid=6):
    m = build_joint_graded(6, n_mid)
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", t_max, du_um / 1000.0, dwell)); t += dwell
        cyc.append((f"c{k}off", t_min, 0.0, dwell)); t += dwell
        ends.append(t)
    p = WD / f"{tag}.inp"
    write_inp(m, p, material("EPC"), cyc, t_ref_c=t_min, cetol=5e-2, procedure="VISCO")
    s = p.read_text()
    s = re.sub(r"\*VISCO, CETOL=[0-9.e-]+", "*VISCO, CETOL=0.05", s)
    s = re.sub(r"^[0-9.e-]+, %g, [0-9.e-]+, [0-9.e-]+$" % dwell,
               f"1e-5, {dwell:g}, 1e-12, {dwell/30:g}", s, flags=re.M)
    s = s.replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                  "*EL PRINT, ELSET=ESYED\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E", "*NODE PRINT, NSET=NBOT\nNT")
    ids = m.sets["ESYED"]
    blk = ["*ELSET, ELSET=ESYED"] + [", ".join(map(str, ids[i:i + 8]))
                                     for i in range(0, len(ids), 8)]
    s = s.replace("*SOLID SECTION", "\n".join(blk) + "\n*SOLID SECTION", 1)
    p.write_text(s)
    run_ccx(p, threads=6)
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        return None
    data = parse_tensors(d, set(ids))
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = per_element_series(data, vols, parse_temperature(d))
    te = ends[STAB - 1]
    q = cycle_quantities(ser, vols, te - 2 * dwell, te)
    qp = cycle_quantities(ser, vols, te - 4 * dwell, te - 2 * dwell)
    if not q:
        return None
    q["stab_pct"] = (100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"])
                     / qp["d_peeq_per_cycle"]) if qp and qp["d_peeq_per_cycle"] else float("nan")
    return q


def main() -> int:
    rows = []
    for arch, du_ref, dt_ref in (("Z1", DU_REF_Z1, DT_REF_Z1), ("Z2", DU_REF_Z2, DT_REF_Z2)):
        for name, tmin, tmax, dwell, desc in CONDS:
            dt = tmax - tmin
            du = du_ref * dt / dt_ref                    # first-order CTE-mismatch scaling
            tag = f"{arch}_{name}"
            t0 = time.time()
            q = run_case(tag, du, tmin, tmax, dwell)
            if q is None:
                print(f"  {tag:22} FAILED", flush=True); continue
            m4, m5 = q["d_peeq_per_cycle"], q["inelastic_work_MJ_per_m3"]
            rows.append({"arch": arch, "condition": name, "description": desc,
                         "T_min_C": tmin, "T_max_C": tmax, "dT_K": dt,
                         "T_mean_C": 0.5 * (tmin + tmax), "dwell_s": dwell,
                         "du_um_assumed": round(du, 4),
                         "du_basis": "scaled linearly with dT from the global-model operating "
                                     "point -- FIRST-ORDER ASSUMPTION",
                         "M4_creep_strain": m4, "M5_creep_energy_MJ_per_m3": m5,
                         "w_over_eps_MPa": m5 / m4, "stab_pct": q["stab_pct"]})
            print(f"  {tag:22} dT={dt:6.1f} dwell={dwell:5.0f}  M4={m4:.4e}  M5={m5:.4f}  "
                  f"w/eps={m5/m4:7.2f}  ({time.time()-t0:.0f}s)", flush=True)
    f = OUT / "experiment_condition_metrics.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}")
    z1 = [r for r in rows if r["arch"] == "Z1"]
    we = [r["w_over_eps_MPa"] for r in z1]
    print(f"\nw/eps across candidate conditions (Z1): {min(we):.1f} to {max(we):.1f} MPa "
          f"-> best possible D = {max(we)/min(we):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
