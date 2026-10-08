#!/usr/bin/env python3
"""Phase-0J-R Sec.8 -- reproduce Syed 2004's own calibration and validation.

PREDECLARED TOLERANCE (set before the arithmetic was run):
  (a) the paper's own claim "predicts life within 25% in most cases" must be reproduced from
      its published Table 3, and
  (b) the two INDEPENDENTLY fitted constants (strain C' and energy W') must, when applied to
      the SAME four measured configurations, recover a mutually consistent effective stress
      w_acc / eps_acc to within 10 %.

(b) is the non-circular test. C' and W' were regressed separately against 12 calibration
points; nothing forces them to agree on an independent package. If they do, the published
constants are internally consistent and were transcribed correctly.

Digitisation: NONE. Every number is a printed table value from the author-corrected PDF
(Table 2b for the calibration set, Table 3 for the validation set).
"""
from __future__ import annotations
import csv
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0jr"

# Author-corrected constants
C_PL, W_PL = 0.0468, 0.0015        # double power law  (Eq. 14, Eq. 15)
C_SH, W_SH = 0.0513, 0.0019        # hyperbolic sine   (Eq. 16, Eq. 17)

# Table 3, author-corrected: PS-etCSP stack package -- an INDEPENDENT validation package,
# not part of the 12-point calibration set.
T3 = [("no stack",  "single sided", 1225, 1082, 1173,  995, 1112),
      ("no stack",  "double sided",  565,  574,  600,  585,  608),
      ("stacked",   "single sided",  915,  958, 1031,  904, 1000),
      ("stacked",   "double sided",  495,  536,  557,  546,  560)]

# Table 2b, author-corrected: the 12-point SnAgCu calibration set (mean life, cycles).
T2B = [(1, "CABGA 15x15 208I/O",  "TC1", 3520), (2, "CABGA 15x15 256I/O", "TC2", 3960),
       (3, "CABGA 8x8 64I/O",     "TC1", 4570), (4, "CABGA 8x8 64I/O",    "TC2", 3103),
       (5, "Ceramic BGA 8x8",     "TC1",  417), (6, "Ceramic BGA 8x8",    "TC3", 1047),
       (7, "CVBGA 12x12 288I/O",  "TC1", 1890), (8, "fleXBGA 12x12 144",  "TC1", 2868),
       (9, "fleXBGA 12x12 144",   "TC2", 2720), (10, "fleXBGA 12x12 144", "TC3", 10027),
       (11, "PBGA 27x27 256I/O",  "TC2", 6381), (12, "TSCSP 12x12 288I/O", "TC2", 275)]


def main() -> int:
    rows = []
    print("(a) ACCURACY -- reproduce the paper's own +-25 % claim from its Table 3\n")
    print(f"{'config':28} {'measured':>9} {'PL creep':>9} {'err %':>7} {'PL energy':>10} "
          f"{'err %':>7}")
    for st, asm, meas, ns, ne, ss, se in T3:
        e1, e2 = 100 * (ns - meas) / meas, 100 * (ne - meas) / meas
        print(f"{st + ', ' + asm:28} {meas:9} {ns:9} {e1:+7.1f} {ne:10} {e2:+7.1f}")
        rows.append({"data_point": f"{st}/{asm}", "package": "PS-etCSP stack",
                     "cycle": "per ref [15]", "set": "Table 3 VALIDATION",
                     "reported_Nf_measured": meas,
                     "reported_Nf_powerlaw_creep": ns, "reported_Nf_powerlaw_energy": ne,
                     "reported_Nf_sinh_creep": ss, "reported_Nf_sinh_energy": se,
                     "err_powerlaw_creep_pct": round(e1, 2),
                     "err_powerlaw_energy_pct": round(e2, 2),
                     "our_transcription": "printed table value, no digitisation",
                     "recomputed_eps_acc": round(1.0 / (C_PL * ns), 6),
                     "recomputed_w_acc_MPa": round(1.0 / (W_PL * ne), 6),
                     "implied_w_over_eps_MPa": round((1.0 / (W_PL * ne)) / (1.0 / (C_PL * ns)), 3)})
    errs = [abs(r["err_powerlaw_creep_pct"]) for r in rows]
    print(f"\n  worst |error| = {max(errs):.1f} %   -> within the +-25 % the paper claims: "
          f"{'YES' if max(errs) <= 25 else 'NO'}")

    print("\n(b) INTERNAL CONSISTENCY -- do the two independently fitted constants agree?\n")
    print(f"{'config':28} {'eps_acc':>10} {'w_acc (MPa)':>12} {'w/eps (MPa)':>12}")
    wo = []
    for r in rows:
        wo.append(r["implied_w_over_eps_MPa"])
        print(f"{r['data_point']:28} {r['recomputed_eps_acc']:10.5f} "
              f"{r['recomputed_w_acc_MPa']:12.5f} {r['implied_w_over_eps_MPa']:12.2f}")
    spread = 100 * (max(wo) - min(wo)) / (sum(wo) / len(wo))
    print(f"\n  w/eps = {min(wo):.2f} to {max(wo):.2f} MPa, spread {spread:.1f} % "
          f"-> within the 10 % declared: {'YES' if spread <= 10 else 'NO'}")

    # the same test on the hyperbolic-sine pair
    wo2 = [(1.0 / (W_SH * se)) / (1.0 / (C_SH * ss)) for *_, ss, se in T3]
    sp2 = 100 * (max(wo2) - min(wo2)) / (sum(wo2) / len(wo2))
    print(f"  hyperbolic-sine pair: w/eps = {min(wo2):.2f} to {max(wo2):.2f} MPa, "
          f"spread {sp2:.1f} %")

    for i, (n, pkg, tc, life) in enumerate(T2B):
        rows.append({"data_point": f"calib {n}", "package": pkg, "cycle": tc,
                     "set": "Table 2b CALIBRATION", "reported_Nf_measured": life,
                     "reported_Nf_powerlaw_creep": "", "reported_Nf_powerlaw_energy": "",
                     "reported_Nf_sinh_creep": "", "reported_Nf_sinh_energy": "",
                     "err_powerlaw_creep_pct": "", "err_powerlaw_energy_pct": "",
                     "our_transcription": "printed table value, no digitisation",
                     "recomputed_eps_acc": round(1.0 / (C_PL * life), 6),
                     "recomputed_w_acc_MPa": round(1.0 / (W_PL * life), 6),
                     "implied_w_over_eps_MPa": round(C_PL / W_PL, 3)})
    f = OUT / "syed_reproduction.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}")

    print("\n(c) WHERE OUR JOINT SITS relative to the calibration set")
    cal = sorted(l for *_, l in T2B)
    print(f"  Syed calibration mean lives : {cal[0]} to {cal[-1]} cycles")
    print(f"  implied eps_acc range       : {1/(C_PL*cal[-1]):.5f} to {1/(C_PL*cal[0]):.5f}")
    print(f"  implied w_acc range (MPa)   : {1/(W_PL*cal[-1]):.5f} to {1/(W_PL*cal[0]):.5f}")
    print(f"  Syed's w/eps (Table 3)      : {min(wo):.1f} to {max(wo):.1f} MPa")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
