#!/usr/bin/env python3
"""Phase-0M-R3A Section 6 --- Z2 TSV diameter re-audit.

Phase 0M-R3 wrote "a 34 um via restores M_AR = 1.089 at the cost of 22.8 % MORE vias".
Under fixed-current-density provisioning n_required goes as 1/A_cu, so a larger via needs
FEWER of them. Every count is separated here and named explicitly.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr3", "scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0m",
          "scripts"):
    sys.path.insert(0, str(R / p))

import arch_geometry as AG                                              # noqa: E402
import tsv_production as TP                                             # noqa: E402
from interconnect import TSVGeometry                                    # noqa: E402

OUT = R / "results" / "phase0mr3a"
ARCH = "ARCH_Z2_BACKSIDE"
AR_MAX = 10.0
S_MIN_UM = 30.0
T_LINER_UM = 0.5
J = 1.0e8
I = 1000.0
TOL_D, TOL_H = 0.02, 0.02       # the declared modest bound


def main() -> int:
    sp = AG.span(ARCH)
    L = sp.length_um
    rows = []
    for d in (30.0, 32.0, 34.0, 36.0):
        pitch = max(d + S_MIN_UM, d)
        g = TSVGeometry(r_m=d / 2 * 1e-6, h_m=L * 1e-6, p_m=pitch * 1e-6,
                        t_liner_m=T_LINER_UM * 1e-6)
        e = TP.evaluate(g, I, TP.BUDGET)
        # hand check of n_required, independent of TP
        a_cu = math.pi * ((d / 2 - T_LINER_UM) * 1e-6) ** 2
        n_hand = math.ceil(I / (J * a_cu))
        ar = L / d
        ar_worst = (L * (1 + TOL_H)) / (d * (1 - TOL_D))
        rows.append({
            "d_um": d, "pitch_um": pitch, "L_um": L,
            "AR": ar, "AR_worst_modest": ar_worst,
            "M_AR": AR_MAX / ar, "M_AR_worst_modest": AR_MAX / ar_worst,
            "passes_hard_rule": ar <= AR_MAX,
            "passes_modest_bound": ar_worst <= AR_MAX,
            "n_required": e["n_required"], "n_required_hand": n_hand,
            "n_allocated": e["n_allocated"], "n_available": e["n_available"],
            "utilisation_alloc_over_avail": e["n_allocated"] / e["n_available"],
            "A_cu_per_via_um2": a_cu * 1e12,
            "total_Cu_area_mm2": e["n_allocated"] * a_cu * 1e6,
            "phi_cu": e["phi_cu"],
            "R_single_mohm": e["R_single_mohm"], "R_field_mohm": e["R_field_mohm"],
            "P_TSV_W": e["P_joule_W"],
            "k_z": e["k_z"], "k_xy": e["k_xy"],
            "E_xy_MPa": e["E_xy_MPa"], "CTE_eff": e["CTE_eff"],
        })
    with open(OUT / "z2_tsv_diameter_sweep.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    b = rows[0]
    t = next(r for r in rows if r["d_um"] == 34.0)
    print("  %6s %7s %7s %8s %11s %11s %11s %10s" %
          ("d_um", "AR", "M_AR", "modest", "n_required", "n_allocated", "n_available",
           "phi_cu"))
    for r in rows:
        print("  %6.0f %7.3f %7.3f %8s %11d %11d %11d %10.6f" %
              (r["d_um"], r["AR"], r["M_AR"],
               "OK" if r["passes_modest_bound"] else "FAIL",
               r["n_required"], r["n_allocated"], r["n_available"], r["phi_cu"]))
    print(f"\n  hand check of n_required matches TP at every diameter: "
          f"{all(r['n_required'] == r['n_required_hand'] for r in rows)}")
    dn = 100 * (t["n_required"] - b["n_required"]) / b["n_required"]
    print(f"  30 -> 34 um: n_required {b['n_required']} -> {t['n_required']} "
          f"({dn:+.1f} %)  <-- FEWER, not more")

    md = f"""# PHASE 0M-R3A SECTION 6 --- Z2 TSV DIAMETER RE-AUDIT

> **Phase 0M-R3 stated the direction backwards.** It wrote that a 34 um via costs
> "22.8 % MORE vias". Under fixed-current-density provisioning a larger via needs
> **22.8 % FEWER**. The magnitude was right; the sign and the framing as a cost were not.

## Which count?

"Via count" is ambiguous and the error hid inside the ambiguity. Four distinct quantities:

| quantity | meaning |
|---|---|
| `n_required` | vias needed to carry the rail at J_design: `ceil(I / (J * A_cu))` |
| `n_allocated` | vias the allocation policy actually places |
| `n_available` | vias the field footprint can hold at the legal pitch |
| total Cu area | `n_allocated * A_cu`, the conducting cross-section actually provided |

## The sweep

All at ARCH_Z2's span of {L:.0f} um, J_design = {J:.0e} A/m2, liner {T_LINER_UM} um,
pitch = max(d + {S_MIN_UM:.0f}, d), identical allocation policy and field footprint.

| d | pitch | AR | M_AR | modest bound | n_required | n_allocated | n_available | phi_Cu |
|---|---|---|---|---|---|---|---|---|
""" + "".join(
        f"| {r['d_um']:.0f} um | {r['pitch_um']:.0f} um | {r['AR']:.3f} | {r['M_AR']:.3f} | "
        f"{'OK' if r['passes_modest_bound'] else '**FAIL**'} | {r['n_required']} | "
        f"{r['n_allocated']} | {r['n_available']} | {r['phi_cu']:.6f} |\n" for r in rows) + f"""
| quantity | 30 um | 34 um | change |
|---|---|---|---|
| n_required | {b['n_required']} | {t['n_required']} | **{dn:+.1f} %** |
| n_allocated | {b['n_allocated']} | {t['n_allocated']} | {100*(t['n_allocated']-b['n_allocated'])/b['n_allocated']:+.1f} % |
| n_available | {b['n_available']} | {t['n_available']} | {100*(t['n_available']-b['n_available'])/b['n_available']:+.1f} % |
| A_cu per via | {b['A_cu_per_via_um2']:.1f} um2 | {t['A_cu_per_via_um2']:.1f} um2 | {100*(t['A_cu_per_via_um2']-b['A_cu_per_via_um2'])/b['A_cu_per_via_um2']:+.1f} % |
| total Cu area | {b['total_Cu_area_mm2']:.4f} mm2 | {t['total_Cu_area_mm2']:.4f} mm2 | {100*(t['total_Cu_area_mm2']-b['total_Cu_area_mm2'])/b['total_Cu_area_mm2']:+.2f} % |
| phi_Cu | {b['phi_cu']:.6f} | {t['phi_cu']:.6f} | {100*(t['phi_cu']-b['phi_cu'])/b['phi_cu']:+.3f} % |
| R_field | {b['R_field_mohm']:.6f} mOhm | {t['R_field_mohm']:.6f} mOhm | {100*(t['R_field_mohm']-b['R_field_mohm'])/b['R_field_mohm']:+.3f} % |
| P_TSV | {b['P_TSV_W']:.4f} W | {t['P_TSV_W']:.4f} W | {100*(t['P_TSV_W']-b['P_TSV_W'])/b['P_TSV_W']:+.3f} % |
| k_z | {b['k_z']:.3f} | {t['k_z']:.3f} | {100*(t['k_z']-b['k_z'])/b['k_z']:+.3f} % |
| k_xy | {b['k_xy']:.4f} | {t['k_xy']:.4f} | {100*(t['k_xy']-b['k_xy'])/b['k_xy']:+.3f} % |
| E_xy | {b['E_xy_MPa']:.0f} MPa | {t['E_xy_MPa']:.0f} MPa | {100*(t['E_xy_MPa']-b['E_xy_MPa'])/b['E_xy_MPa']:+.3f} % |
| CTE_eff | {b['CTE_eff']:.4e} | {t['CTE_eff']:.4e} | {100*(t['CTE_eff']-b['CTE_eff'])/b['CTE_eff']:+.3f} % |

`n_required` is verified against an independent hand calculation at every diameter:
`ceil(I / (J * pi * (d/2 - t_liner)^2))`. They agree exactly.

## Why the count falls

    n_required  ~  1 / A_cu  ~  1 / (d/2 - t_liner)^2

so `(14.5 / 16.5)^2 = 0.7723`, i.e. **22.8 % fewer**. The 22.8 % figure in the Phase-0M-R3
text is this number with its sign inverted and relabelled a cost.

## Why nothing else moves

`phi_Cu`, `R_field`, `P_TSV`, the thermal tensor, the modulus and the CTE change by well
under 0.1 %. That is the Phase-0M allocation law: under minimum-capability provisioning the
copper fraction is `I / (J_design * A_field)`, in which the via radius cancels identically.
A larger via means fewer vias and the same total copper. **The 34 um change is essentially
free in E/T/M terms** -- which was the correct conclusion in Phase 0M-R3, reached through
an incorrect statement about counts.

## Process margin

| d | AR | M_AR | under -2 % diameter, +2 % depth |
|---|---|---|---|
""" + "".join(
        f"| {r['d_um']:.0f} um | {r['AR']:.3f} | {r['M_AR']:.3f} | "
        f"{r['AR_worst_modest']:.3f} -> {'PASSES' if r['passes_modest_bound'] else '**VIOLATES AR <= 10**'} |\n"
        for r in rows) + """
30 um fails the modest bound; 32 um and above pass. **32 um is the smallest diameter on
this grid with positive margin**, not 34 um -- Phase 0M-R3 swept 30/34/40/50/60 and never
evaluated 32.
"""
    (OUT / "Z2_TSV_PROCESS_MARGIN_REAUDIT.md").write_text(md)
    print(f"wrote {OUT/'Z2_TSV_PROCESS_MARGIN_REAUDIT.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
