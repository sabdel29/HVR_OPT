#!/usr/bin/env python3
"""Phase-0K-R Sec.4/5 -- audit every proposed profile against the CONSTITUTIVE DOMAIN.

Temperature alone is not sufficient (Sec.5). Three things are checked per profile:

  (1) TEMPERATURE   -- is the joint below the 45 C creep-calibration floor, and for how much
                       of the accumulated damage?
  (2) DRIVING STRESS -- Phase 0J-R proved CalculiX integrates the OVERSTRESS (sigma_eq - sigma_y),
                       so the 7.51-15.92 MPa fitted window must be checked on THAT, not on
                       sigma_eq. Both are reported.
  (3) DAMAGE-WEIGHTED exposure -- the decision-relevant quantity is not "does the cycle visit
                       an uncalibrated state" but "how much of the damage is accumulated there".
"""
from __future__ import annotations
import bisect, csv, math, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
for p in ("phase0kr", "phase0k", "phase0jr", "phase0ir", "phase0i"):
    sys.path.insert(0, str(R / "scripts" / p))
from creep_metric import norton_at_T, yield_at, svm                       # noqa: E402
from decompose import parse_temperature, parse_tensors                     # noqa: E402
from graded_joint import build_joint_graded                                # noqa: E402
from solder_model import CREEP_DATA                                        # noqa: E402

OUT = R / "results" / "phase0kr"
WD = R / "results" / "phase0k" / "disc"
OUT.mkdir(parents=True, exist_ok=True)

CREEP_T = sorted({t for t, s, e in CREEP_DATA})
T_LO, T_HI = min(CREEP_T), max(CREEP_T)                 # 45, 150
S_LO, S_HI = min(s for t, s, e in CREEP_DATA), max(s for t, s, e in CREEP_DATA)
PLASTIC_T = (-40.0, 122.0)                              # Chaboche source range
N_CYC, STAB, DWELLS = 6, 5, None

# Phase-0K candidates (solved in results/phase0k/disc) and Phase-0K-R within-domain
# candidates (solved in results/phase0kr/wd). Both directories are searched.
CONDS = [("OP_BASELINE", 25.0, 82.86, 300.0), ("JEDEC_A104", -40.0, 125.0, 900.0),
         ("COLD_SHALLOW", -40.0, 25.0, 300.0), ("HOT_SHALLOW", 55.0, 125.0, 300.0),
         ("SMALL_DT", 25.0, 55.0, 300.0), ("LONG_DWELL", 25.0, 82.86, 900.0),
         ("SHORT_DWELL", 25.0, 82.86, 30.0), ("WIDE_HOT", 25.0, 125.0, 300.0),
         ("D_LOW_NARROW", 45.0, 85.0, 300.0), ("D_LOW_WIDE", 45.0, 125.0, 300.0),
         ("D_MID", 55.0, 125.0, 300.0), ("D_HIGH_NARROW", 110.0, 150.0, 300.0),
         ("D_HIGH_WIDE", 80.0, 150.0, 300.0), ("D_LOW_LONG", 45.0, 85.0, 900.0),
         ("D_HIGH_LONG", 110.0, 150.0, 900.0)]
WD2 = R / "results" / "phase0kr" / "wd"


def audit(tag, dwell):
    """Damage-weighted domain exposure for one solved case."""
    d = WD / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        d = WD2 / f"{tag}.dat"
    if not (d.is_file() and d.stat().st_size > 5000):
        return None
    m = build_joint_graded(6, 6)
    ids = set(m.sets["ESYED"])
    data = parse_tensors(d, ids)
    temps = parse_temperature(d)
    vols = {e: dd["V"] for per in data.values() for e, dd in per.items() if "V" in dd}
    ser = {}
    for t in sorted(data):
        T = temps.get(t)
        if T is None:
            continue
        for e, dd in data[t].items():
            if "S" in dd and "P" in dd:
                ser.setdefault(e, []).append((t, T, svm(dd["S"]), dd["P"]))
    te = dwell * 2 * STAB
    t0 = te - 2 * dwell
    tot = below = outside_s = 0.0
    smin = dmin = 1e9; smax = dmax = -1e9; tmin = 1e9; tmax = -1e9
    for e, rows in ser.items():
        w = [r for r in rows if t0 - 1e-9 < r[0] <= te + 1e-9]
        if len(w) < 3:
            continue
        v = vols.get(e, 1.0)
        for k in range(1, len(w)):
            (ta, Ta, sa, pa), (tb, Tb, sb, pb) = w[k - 1], w[k]
            dt = tb - ta
            if dt <= 0:
                continue
            Tm, sm, pm = .5 * (Ta + Tb), .5 * (sa + sb), .5 * (pa + pb)
            drv = max(sm - yield_at(Tm, pm), 0.0)        # the stress the creep law SEES
            # Weight by the SOLVER'S OWN increment, not by a reconstructed Norton rate.
            # Phase 0J-R established that the sigma^8 quadrature over these output intervals
            # diverges, and that every increment of PEEQ in this model IS creep. d(PEEQ) is
            # therefore the exact creep increment and needs no reconstruction.
            de = max(pb - pa, 0.0) * v
            tot += de
            if Tm < T_LO:
                below += de
            if drv > 0 and not (S_LO <= drv <= S_HI):
                outside_s += de
            smin, smax = min(smin, sm), max(smax, sm)
            dmin, dmax = min(dmin, drv), max(dmax, drv)
            tmin, tmax = min(tmin, Tm), max(tmax, Tm)
    if tot <= 0:
        return None
    return {"frac_damage_below_45C": below / tot, "frac_damage_outside_stress": outside_s / tot,
            "sigma_eq_min": smin, "sigma_eq_max": smax,
            "driving_min": dmin, "driving_max": dmax, "T_min": tmin, "T_max": tmax}


def classify(a, tmin, tmax):
    """Sec.5 four-way classification, on DAMAGE-WEIGHTED exposure.

    Thresholds predeclared: a profile is FULLY INSIDE if it never goes below the creep floor
    and accumulates under 5 % of its damage outside the fitted stress window; MILD if under
    5 % of damage falls below the floor and under 25 % outside the window; SEVERE if under
    50 % falls below the floor; INVALID beyond that, because a design whose decisive damage is
    accumulated in an uncalibrated regime cannot discriminate models that were calibrated in
    a different one.
    """
    t_ex = tmin < T_LO
    frac = a["frac_damage_below_45C"]
    s_ex = a["frac_damage_outside_stress"]
    if not t_ex and s_ex < 0.05:
        return "FULLY INSIDE CALIBRATED DOMAIN"
    if frac < 0.05 and s_ex < 0.25:
        return "MILD EXTRAPOLATION"
    if frac < 0.50:
        return "SEVERE EXTRAPOLATION"
    return "INVALID FOR MODEL-DISCRIMINATION DESIGN"


def main() -> int:
    print(f"CREEP calibration : T {T_LO}-{T_HI} C, stress {S_LO}-{S_HI} MPa, {len(CREEP_DATA)} pts")
    print(f"PLASTIC calibration: T {PLASTIC_T[0]}-{PLASTIC_T[1]} C (Chaboche)\n")
    rows = []
    for arch in ("Z1", "Z2"):
        for name, tmin, tmax, dwell in CONDS:
            a = audit(f"{arch}_{name}", dwell)
            if a is None:
                print(f"  {arch}_{name:14} no solve"); continue
            cls = classify(a, tmin, tmax)
            rows.append({"arch": arch, "condition": name, "T_min_C": tmin, "T_max_C": tmax,
                         "dwell_s": dwell,
                         "creep_cal_T_range_C": f"{T_LO}-{T_HI}",
                         "creep_cal_stress_MPa": f"{S_LO}-{S_HI}",
                         "T_below_creep_floor": tmin < T_LO,
                         "frac_damage_below_45C": round(a["frac_damage_below_45C"], 5),
                         "sigma_eq_range_MPa": f"{a['sigma_eq_min']:.1f}-{a['sigma_eq_max']:.1f}",
                         "driving_overstress_range_MPa":
                             f"{a['driving_min']:.2f}-{a['driving_max']:.2f}",
                         "frac_damage_outside_stress_window":
                             round(a["frac_damage_outside_stress"], 5),
                         "plastic_T_extrapolated": tmax > PLASTIC_T[1] or tmin < PLASTIC_T[0],
                         "domain_class": cls})
            if arch == "Z1":
                print(f"  {name:14} T {tmin:6.1f}/{tmax:6.1f}  "
                      f"damage below 45 C: {100*a['frac_damage_below_45C']:6.2f} %   "
                      f"drive {a['driving_min']:5.2f}-{a['driving_max']:6.2f} MPa   "
                      f"out-of-window damage {100*a['frac_damage_outside_stress']:5.1f} %   "
                      f"-> {cls}")
    f = OUT / "profile_domain_audit.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
