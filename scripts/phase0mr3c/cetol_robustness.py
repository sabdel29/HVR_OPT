#!/usr/bin/env python3
"""Integration-tolerance robustness of the final local solder response.

The reviewer question this answers is narrow: is the Z2 < Z1 inelastic-response
ordering an artifact of the relaxed creep strain-increment tolerance used for the final
high-stress pair?

EVERYTHING except CETOL is the frozen final model. Geometry, mesh, exclusion band,
material card, boundary conditions, stress-free reference, joint temperature, du_c,
dwell, cycle count and extraction code are taken unchanged from
scripts/phase0mr3c/run_final_local_response.py, which itself reuses the Phase-0I/0I-R
production submodel. Only the CETOL value on the *VISCO card differs between runs.

Tolerance ladder, and where each value comes from:
    1e-5  scripts/phase0l/calculix_creep_probe.py      (single-element creep probes)
    1e-4  scripts/phase0jr/probe_viscoplastic.py
    1e-2  scripts/phase0i, scripts/phase0ir            (Phase-0I production joint)
    5e-2  scripts/phase0jr, 0kr, 0lr, 0m               (later production joint; the value
                                                        used for the final pair)
    1e-1  NOT historical. One step looser than production, included only so the production
          point is bracketed from above as well as below; flagged as such in the output.

Non-convergence is a result and is recorded, never discarded.
"""
from __future__ import annotations
import csv, importlib.util, re, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3c"
WD = OUT / "cetol_sweep"
WD.mkdir(parents=True, exist_ok=True)
for p in ("phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from cycle_audit import cycle_quantities, per_element_series          # noqa: E402
from decompose import material, parse_temperature, parse_tensors      # noqa: E402
from joint import build_joint, run, write_inp                         # noqa: E402

_s = importlib.util.spec_from_file_location(
    "rf", R / "scripts" / "phase0mr3c" / "run_final_local_response.py")
RF = importlib.util.module_from_spec(_s); _s.loader.exec_module(RF)

LADDER = [(1.0e-5, "phase0l creep probe"), (1.0e-4, "phase0jr viscoplastic probe"),
          (1.0e-2, "phase0i / phase0ir production"), (5.0e-2, "production, final pair"),
          (1.0e-1, "not historical -- brackets production from above")]


def _sta(p: Path) -> tuple[int, int]:
    """(converged increments, unconverged attempts) from the CalculiX .sta file."""
    if not p.is_file():
        return 0, 0
    inc = att = 0
    for l in p.read_text().splitlines():
        f = l.split()
        if len(f) >= 4 and f[0].isdigit():
            (att := att + 1) if f[2].endswith("U") else (inc := inc + 1)
    return inc, att


def _resid(p: Path) -> float | None:
    """Largest final force residual from the .cvg file, if the solver wrote one."""
    if not p.is_file():
        return None
    last = None
    for l in p.read_text().splitlines():
        f = l.split()
        if len(f) >= 7 and f[0].isdigit():
            try: last = float(f[5])
            except ValueError: pass
    return last


def one(case: str, du_um: float, t_hot: float, cetol: float) -> dict:
    m = build_joint(RF.N_XY, RF.N_Z_SOL, RF.N_Z_PAD)
    cyc, ends, t = [], [], 0.0
    for k in range(RF.N_CYC):
        cyc.append((f"c{k}on", t_hot, du_um / 1000.0, RF.DWELL)); t += RF.DWELL
        cyc.append((f"c{k}off", RF.T_OFF, 0.0, RF.DWELL)); t += RF.DWELL
        ends.append(t)
    tag = f"{case}_c{cetol:g}"
    p = WD / f"{tag}.inp"
    write_inp(m, p, material(RF.MATKIND), cyc, cetol=cetol, procedure=RF.PROCEDURE)
    s = p.read_text().replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                              "*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E",
                  "*EL PRINT, ELSET=ESOL\nS, E\n*NODE PRINT, NSET=NBOT\nNT")
    p.write_text(s)
    t0 = time.time()
    run(p, threads=6)
    wall = time.time() - t0
    inc, att = _sta(WD / f"{tag}.sta")
    res = _resid(WD / f"{tag}.cvg")
    rec = {"case": case, "cetol": cetol, "wall_s": round(wall, 1),
           "increments": inc, "cutback_attempts": att,
           "final_force_residual": "" if res is None else f"{res:.6e}"}
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        rec |= {"converged": "NO", "d_eps_in_stab": "", "range_eq_inelastic": "",
                "inelastic_work_MJ_per_m3": "", "stab_change_pct": ""}
        return rec
    data = parse_tensors(d, set(m.sets["ESOLCORE"]))
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = per_element_series(data, vols, parse_temperature(d))
    te = ends[-1]
    q = cycle_quantities(ser, vols, te - 2 * RF.DWELL, te)
    qp = cycle_quantities(ser, vols, te - 4 * RF.DWELL, te - 2 * RF.DWELL)
    if q is None or qp is None:
        rec |= {"converged": "NO", "d_eps_in_stab": "", "range_eq_inelastic": "",
                "inelastic_work_MJ_per_m3": "", "stab_change_pct": ""}
        return rec
    rec |= {"converged": "YES",
            "d_eps_in_stab": f"{q['d_peeq_per_cycle']:.12e}",
            "range_eq_inelastic": f"{q['range_eq_inelastic']:.12e}",
            "inelastic_work_MJ_per_m3": f"{q['inelastic_work_MJ_per_m3']:.12e}",
            "stab_change_pct": f"{100 * abs(q['d_peeq_per_cycle'] - qp['d_peeq_per_cycle']) / qp['d_peeq_per_cycle']:.6f}"}
    return rec


def main() -> int:
    inp = {r["case"]: r for r in csv.DictReader((OUT / "local_submodel_inputs.csv").open())}
    rows = []
    for cetol, prov in LADDER:
        for case in ("Z1", "Z2"):
            i = inp[case]
            r = one(case, float(i["du_c_um"]), float(i["T_joint_C"]), cetol)
            r["provenance"] = prov
            rows.append(r)
            print(f"  CETOL {cetol:<8g} {case}  {r['converged']:>3s}  "
                  f"inc {r['increments']:>5d}  cut {r['cutback_attempts']:>3d}  "
                  f"{r['wall_s']:>7.1f} s  "
                  f"d_eps {r['d_eps_in_stab'][:12] or '--':>12s}  "
                  f"stab {r['stab_change_pct'][:6] or '--':>6s}", flush=True)
    f = OUT / "cetol_final_pair.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print(f"\n{'CETOL':>8} {'Z1 d_eps':>14} {'Z2 d_eps':>14} {'D_eps':>8} {'Z2 lower %':>11}")
    conv = []
    for cetol, _ in LADDER:
        z = {r["case"]: r for r in rows if r["cetol"] == cetol}
        if z["Z1"]["converged"] == "YES" and z["Z2"]["converged"] == "YES":
            e1, e2 = float(z["Z1"]["d_eps_in_stab"]), float(z["Z2"]["d_eps_in_stab"])
            conv.append((cetol, e1, e2, e1 / e2, 100 * (1 - e2 / e1)))
            print(f"{cetol:8g} {e1:14.6e} {e2:14.6e} {e1/e2:8.4f} {100*(1-e2/e1):11.2f}")
        else:
            print(f"{cetol:8g} {'NONCONVERGED':>14} "
                  f"{'(Z1 ' + z['Z1']['converged'] + ', Z2 ' + z['Z2']['converged'] + ')':>32}")
    if not conv:
        print("\n  NO tolerance converged for both architectures."); return 0
    d = [c[3] for c in conv]
    print(f"\n  converged tolerances      : {len(conv)} of {len(LADDER)}")
    print(f"  D_eps range               : {min(d):.4f} to {max(d):.4f} "
          f"(spread {100*(max(d)-min(d))/min(d):.2f} %)")
    for k, nm in ((1, "Z1"), (2, "Z2")):
        v = [c[k] for c in conv]
        print(f"  {nm} absolute d_eps spread  : {100*(max(v)-min(v))/min(v):.2f} %")
    print(f"  ordering Z2 < Z1 holds    : {all(c[3] > 1.0 for c in conv)} "
          f"(at every converged tolerance)")
    print(f"\n  wrote {f.relative_to(R)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
