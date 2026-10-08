#!/usr/bin/env python3
"""Final local solder response on the FROZEN R3C Z1/Z2 pair.

The existing production local submodel is run unchanged. Nothing about the model is new:
the mesh, exclusion band, constitutive card, solver, procedure, step schedule, dwell, cycle
count, stabilisation rule and extraction code are all the validated Phase-0I/0I-R family
(scripts/phase0i/joint.py, scripts/phase0ir/{decompose,cycle_audit}.py), the same family
that produced the 1.90 % finest-pair mesh drift in
results/phase0i/local_metric_convergence.csv at n_xy=6, n_z=8, cetol=1e-2, excl_frac=1.0.

The only inputs that change are the two the architecture supplies, both read from
results/phase0mr3c/local_submodel_inputs.csv, which is itself derived from the frozen
replay and asserted against every frozen global value:

    du_c      corner-joint relative in-plane displacement
    T_joint   mean corner-band joint temperature

One solve per architecture. No sweep, no fit, no new metric.
"""
from __future__ import annotations
import csv, sys, time
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from cycle_audit import cycle_quantities, per_element_series          # noqa: E402
from decompose import material, parse_temperature, parse_tensors      # noqa: E402
from joint import build_joint, run, write_inp                         # noqa: E402

OUT = R / "results" / "phase0mr3c"
WD = OUT / "local_final"
WD.mkdir(parents=True, exist_ok=True)

# the validated local family -- mesh, exclusion band, constitutive card, procedure, cycle
# schedule and extraction identical to scripts/phase0ir/arch_both_metrics.py
N_XY, N_Z_SOL, N_Z_PAD = 6, 8, 1
N_CYC, DWELL, T_OFF = 4, 300.0, 25.0
PROCEDURE, MATKIND = "VISCO", "EPC"

# CETOL is the creep-strain-increment tolerance of the time integrator: a solver accuracy
# control, not a material or loading property. At the R3C operating point the integrator
# cannot satisfy CETOL = 1e-2 at any admissible step -- force equilibrium converges to
# machine zero in five Newton iterations, but the step is cut until it falls below the
# minimum. CETOL = 5e-2 is the setting four later production scripts already use
# (phase0jr/dwell_sensitivity, phase0kr/within_domain_search, phase0lr/replay_lr,
# phase0m/me_energy) and its effect on this metric was measured in the Phase-0I convergence
# study: tags c0.01 and c0.05 in results/phase0i/local_metric_convergence.csv differ by
# 0.015 % on d_eps_in_stab at the same mesh. run_control() below re-establishes that on the
# published Phase-0I architecture case before the R3C numbers are accepted.
CETOL = 5.0e-2
CETOL_VALIDATED = 1.0e-2

# published Phase-0I control (results/phase0ir/architecture_metric_agreement.csv)
CONTROL = {"du_um": 2.749, "T_hot_C": 82.86, "d_eps_in_stab": 0.006513193433593729}
CONTROL_TOL_PCT = 0.5


def run_case(case: str, du_um: float, t_hot: float) -> dict | None:
    m = build_joint(N_XY, N_Z_SOL, N_Z_PAD)
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", t_hot, du_um / 1000.0, DWELL)); t += DWELL
        cyc.append((f"c{k}off", T_OFF, 0.0, DWELL)); t += DWELL
        ends.append(t)
    p = WD / f"{case}.inp"
    write_inp(m, p, material(MATKIND), cyc, cetol=CETOL, procedure=PROCEDURE)
    s = p.read_text().replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                              "*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E",
                  "*EL PRINT, ELSET=ESOL\nS, E\n*NODE PRINT, NSET=NBOT\nNT")
    p.write_text(s)
    t0 = time.time()
    run(p, threads=6)
    wall = time.time() - t0
    d = WD / f"{case}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        return None
    data = parse_tensors(d, set(m.sets["ESOLCORE"]))
    temps = parse_temperature(d)
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = per_element_series(data, vols, temps)
    te = ends[-1]
    q = cycle_quantities(ser, vols, te - 2 * DWELL, te)            # stabilised (last) cycle
    qp = cycle_quantities(ser, vols, te - 4 * DWELL, te - 2 * DWELL)   # previous cycle
    if q is None or qp is None:
        return None
    stab = 100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"]) / qp["d_peeq_per_cycle"]
    return {"n_core": len(m.sets["ESOLCORE"]), "n_elem": len(m.elems),
            "wall_s": wall, "stab_change_pct": stab,
            "prev_cycle_d_eps": qp["d_peeq_per_cycle"], **q}


def run_control() -> float:
    """The published Phase-0I case at the CETOL actually used, so the setting is not a free
    variable: it must reproduce the published number to within the characterised tolerance."""
    r = run_case("CONTROL", CONTROL["du_um"], CONTROL["T_hot_C"])
    if r is None:
        raise SystemExit("  CONTROL diverged -- the harness itself is not usable")
    got, want = r["d_peeq_per_cycle"], CONTROL["d_eps_in_stab"]
    dev = 100 * abs(got - want) / want
    print(f"  control @ CETOL={CETOL:g}: d_eps_in = {got:.9e} against published "
          f"{want:.9e}  ({dev:.4f} %)")
    if dev > CONTROL_TOL_PCT:
        raise SystemExit(f"  control deviates by {dev:.4f} % > {CONTROL_TOL_PCT} % -- STOP")
    return dev


def main() -> int:
    inp = {r["case"]: r for r in csv.DictReader((OUT / "local_submodel_inputs.csv").open())}
    ctrl_dev = run_control()
    rows = []
    for case in ("Z1", "Z2"):
        i = inp[case]
        du, th = float(i["du_c_um"]), float(i["T_joint_C"])
        print(f"  {case}: du_c = {du:.4f} um, T_joint = {th:.3f} C, "
              f"{N_CYC} cycles x 2 x {DWELL:.0f} s ...", flush=True)
        r = run_case(case, du, th)
        if r is None:
            print(f"  FAILED {case} -- no usable .dat"); return 1
        rows.append({"case": case, "arch": i["arch"], "du_c_um": f"{du:.10f}",
                     "T_joint_C": f"{th:.6f}", "T_off_C": T_OFF, "n_cycles": N_CYC,
                     "dwell_s": DWELL, "n_xy": N_XY, "n_z_solder": N_Z_SOL,
                     "cetol": CETOL, "cetol_control_dev_pct": f"{ctrl_dev:.6f}",
                     "procedure": PROCEDURE, "material": MATKIND,
                     "d_eps_in_stab": f"{r['d_peeq_per_cycle']:.12e}",
                     "prev_cycle_d_eps": f"{r['prev_cycle_d_eps']:.12e}",
                     "stab_change_pct": f"{r['stab_change_pct']:.6f}",
                     "range_eq_inelastic": f"{r['range_eq_inelastic']:.12e}",
                     "inelastic_work_MJ_per_m3": f"{r['inelastic_work_MJ_per_m3']:.12e}",
                     "n_core": r["n_core"], "n_elem": r["n_elem"],
                     "wall_s": f"{r['wall_s']:.2f}"})
        print(f"        d_eps_in = {r['d_peeq_per_cycle']:.6e} / cycle, "
              f"range = {r['range_eq_inelastic']:.6e}, "
              f"W_in = {r['inelastic_work_MJ_per_m3']:.6e} MJ/m3, "
              f"cycle-to-cycle {r['stab_change_pct']:.2f} %", flush=True)

    z1, z2 = (next(r for r in rows if r["case"] == c) for c in ("Z1", "Z2"))
    e1, e2 = float(z1["d_eps_in_stab"]), float(z2["d_eps_in_stab"])
    d_eps = e1 / e2
    red = 1.0 - e2 / e1
    w1, w2 = (float(r["inelastic_work_MJ_per_m3"]) for r in (z1, z2))
    for r, extra in ((z1, {}), (z2, {})):
        r.update(extra)
    f = OUT / "final_local_response.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    du1, du2 = (float(inp[c]["du_c_um"]) for c in ("Z1", "Z2"))
    print(f"\n  D_u   = {du1 / du2:.4f}   (displacement driver, frozen)")
    print(f"  D_eps = {d_eps:.4f}   (stabilised local inelastic response)")
    print(f"  Z2 carries {100 * red:.1f} % LOWER stabilised inelastic response than Z1")
    print(f"  D_work = {w1 / w2:.4f}  (inelastic work, secondary)")
    print(f"  orderings agree: {(d_eps > 1.0) == (du1 / du2 > 1.0)}")
    print(f"\n  wrote {f.relative_to(R)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
