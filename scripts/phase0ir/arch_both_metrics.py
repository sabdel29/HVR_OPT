#!/usr/bin/env python3
"""Phase-0I-R -- do the Phase-0I ARCHITECTURE conclusions survive the choice of metric?

Sec.6 established that enabling creep moves the strain-based metric DOWN 29.8 % and the
energy-based metric UP 164.6 %. The two disagree about what "more damage" means. That is only
a presentational problem if the two metrics still RANK the architectures the same way. If they
disagree on ranking, the Phase-0I architecture conclusion depends on an unjustified choice and
has to be withdrawn.

The three Phase-0I architecture cases are re-run at their own electrical optima with full
tensor output, and both metrics are computed from the same solve.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
for p in ("phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from cycle_audit import cycle_quantities, per_element_series          # noqa: E402
from decompose import OUT, WD, material, parse_temperature, parse_tensors  # noqa: E402
from joint import build_joint, run, write_inp, BALL_H_UM              # noqa: E402

# from results/phase0i/z_architecture_comparison.csv, each architecture's electrical optimum
CASES = [("ARCH_Z1_EMBEDDED", 1.30, 2.749, 82.86),
         ("ARCH_Z2_BACKSIDE", 0.30, 2.080, 81.85),
         ("ARCH_Z4_POWER_DIE", 0.30, 2.984, 81.10)]
N_CYC, DWELL, T_OFF = 4, 300.0, 25.0
WD2 = OUT / "archmetrics"
WD2.mkdir(parents=True, exist_ok=True)


def run_case(tag, du_um, t_hot):
    m = build_joint(6, 8, 1)
    cyc, ends, t = [], [], 0.0
    for k in range(N_CYC):
        cyc.append((f"c{k}on", t_hot, du_um / 1000.0, DWELL)); t += DWELL
        cyc.append((f"c{k}off", T_OFF, 0.0, DWELL)); t += DWELL
        ends.append(t)
    p = WD2 / f"{tag}.inp"
    write_inp(m, p, material("EPC"), cyc, cetol=1e-2, procedure="VISCO")
    s = p.read_text().replace("*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL",
                              "*EL PRINT, ELSET=ESOLCORE\nPEEQ, EVOL, S, E")
    s = s.replace("*EL PRINT, ELSET=ESOL\nS, E",
                  "*EL PRINT, ELSET=ESOL\nS, E\n*NODE PRINT, NSET=NBOT\nNT")
    p.write_text(s)
    run(p, threads=6)
    d = WD2 / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        return None
    data = parse_tensors(d, set(m.sets["ESOLCORE"]))
    temps = parse_temperature(d)
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = per_element_series(data, vols, temps)
    te = ends[-1]
    q = cycle_quantities(ser, vols, te - 2 * DWELL, te)
    qprev = cycle_quantities(ser, vols, te - 4 * DWELL, te - 2 * DWELL)
    return q, qprev


def main():
    rows = []
    print(f"{'architecture':20s} {'h mm':>5s} {'du um':>7s} {'d(PEEQ)/cyc':>13s} "
          f"{'range':>12s} {'W_in MJ/m3':>13s} {'stab %':>7s}")
    for arch, h, du, th in CASES:
        r = run_case(f"{arch[7:11]}", du, th)
        if not r:
            print(f"{arch:20s}  FAILED"); continue
        q, qp = r
        stab = (100 * abs(q["d_peeq_per_cycle"] - qp["d_peeq_per_cycle"])
                / qp["d_peeq_per_cycle"]) if qp else float("nan")
        rows.append({"arch": arch, "h_sub_mm": h, "du_corner_um": du, "T_hot_C": th,
                     **q, "stab_change_pct": stab})
        print(f"{arch:20s} {h:5.2f} {du:7.3f} {q['d_peeq_per_cycle']:13.5e} "
              f"{q['range_eq_inelastic']:12.5e} {q['inelastic_work_MJ_per_m3']:13.5e} "
              f"{stab:7.2f}", flush=True)
    with open(OUT / "architecture_metric_agreement.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    print("\n=== DO THE TWO METRICS RANK THE ARCHITECTURES THE SAME WAY? ===")
    ref = next(r for r in rows if r["arch"] == "ARCH_Z1_EMBEDDED")
    print(f"{'architecture':20s} {'d(PEEQ) vs Z1':>15s} {'range vs Z1':>13s} {'W_in vs Z1':>13s}")
    for r in rows:
        print(f"{r['arch']:20s} "
              f"{100*(r['d_peeq_per_cycle']-ref['d_peeq_per_cycle'])/ref['d_peeq_per_cycle']:+14.1f}% "
              f"{100*(r['range_eq_inelastic']-ref['range_eq_inelastic'])/ref['range_eq_inelastic']:+12.1f}% "
              f"{100*(r['inelastic_work_MJ_per_m3']-ref['inelastic_work_MJ_per_m3'])/ref['inelastic_work_MJ_per_m3']:+12.1f}%")
    order = lambda k: [r["arch"] for r in sorted(rows, key=lambda x: x[k])]
    o1, o2, o3 = order("d_peeq_per_cycle"), order("range_eq_inelastic"), \
        order("inelastic_work_MJ_per_m3")
    print(f"\n  ranking by d(PEEQ)/cycle : {' < '.join(a[7:] for a in o1)}")
    print(f"  ranking by strain range  : {' < '.join(a[7:] for a in o2)}")
    print(f"  ranking by inelastic work: {' < '.join(a[7:] for a in o3)}")
    print(f"\n  ALL THREE METRICS AGREE ON RANKING: {o1 == o2 == o3}")
    print(f"\nwrote architecture_metric_agreement.csv")


if __name__ == "__main__":
    main()
