#!/usr/bin/env python3
"""Phase-0K Sec.2/3 -- robust G2 decision map across EVERY admitted absolute-life formulation.

Sec.3 forbids choosing one law. All four Syed 2004 author-corrected formulations that carry an
absolute constant are applied independently, and each N_required is classified as ROBUST PASS,
ROBUST FAIL or MODEL-FORM AMBIGUOUS.

Schubert 2003 is deliberately EXCLUDED here: it prints exponents but no prefactor, so it yields
relative life only and cannot vote on an absolute pass/fail. Its exclusion is recorded rather
than silently assumed, and it does not change the conclusion -- adding a fifth absolute model
could only widen the ambiguous band, never narrow it.
"""
from __future__ import annotations
import csv, math
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0k"
P0JR = R / "results" / "phase0jr"
OUT.mkdir(parents=True, exist_ok=True)

# Syed 2004 AUTHOR-CORRECTED constants. Both constitutive variants, both metric families.
LAWS = [
    ("SYED_EQ14_STRAIN_POWERLAW", "M4", 0.0468, "double power law, accumulated creep strain"),
    ("SYED_EQ15_ENERGY_POWERLAW", "M5", 0.0015, "double power law, creep energy density"),
    ("SYED_EQ16_STRAIN_SINH", "M4", 0.0513, "hyperbolic sine, accumulated creep strain"),
    ("SYED_EQ17_ENERGY_SINH", "M5", 0.0019, "hyperbolic sine, creep energy density"),
]
ARCH = ("Z1", "Z2", "Z4")
LONG = {"Z1": "ARCH_Z1_EMBEDDED", "Z2": "ARCH_Z2_BACKSIDE", "Z4": "ARCH_Z4_POWER_DIE"}


def metrics():
    rs = {r["short"]: r for r in
          csv.DictReader(open(P0JR / "syed_layer_metrics.csv")) if r["n_mid"] == "10"}
    return ({a: float(rs[a]["M4_syed_layer"]) for a in ARCH},
            {a: float(rs[a]["M5_syed_layer_MJ_per_m3"]) for a in ARCH})


def lives():
    m4, m5 = metrics()
    out = {}
    for name, met, C, _ in LAWS:
        src = m4 if met == "M4" else m5
        out[name] = {a: 1.0 / (C * src[a]) for a in ARCH}
    return out


def classify(nf_by_law, a, nreq):
    v = [nf_by_law[L][a] >= nreq for L, *_ in [(k,) for k in nf_by_law]]
    if all(v):
        return "ROBUST PASS"
    if not any(v):
        return "ROBUST FAIL"
    return "MODEL-FORM AMBIGUOUS"


def main() -> int:
    nf = lives()
    print(f"{'law':30} {'Z1':>8} {'Z2':>8} {'Z4':>8}")
    for L, met, C, desc in LAWS:
        print(f"{L:30} " + " ".join(f"{nf[L][a]:8.0f}" for a in ARCH))
    lo = {a: min(nf[L][a] for L, *_ in LAWS) for a in ARCH}
    hi = {a: max(nf[L][a] for L, *_ in LAWS) for a in ARCH}
    print("\nacross all four admitted absolute formulations:")
    for a in ARCH:
        print(f"  {a}: {lo[a]:6.0f} to {hi[a]:6.0f} cycles   (spread {hi[a]/lo[a]:.2f}x)")

    rows = []
    grid = [10 ** (2 + 3 * k / 600) for k in range(601)]          # 1e2..1e5, dense log grid
    for n in grid:
        st = {a: classify(nf, a, n) for a in ARCH}
        npass = sum(v == "ROBUST PASS" for v in st.values())
        nfail = sum(v == "ROBUST FAIL" for v in st.values())
        namb = sum(v == "MODEL-FORM AMBIGUOUS" for v in st.values())
        if npass == 3:
            dec = "ALL ARCHITECTURES ROBUSTLY PASS -- G2 NOT ACTIVE"
        elif nfail == 3:
            dec = "ALL ARCHITECTURES ROBUSTLY FAIL -- reliability limiting, architecture does not solve it"
        elif st["Z1"] == "ROBUST FAIL" and st["Z2"] == "ROBUST PASS":
            dec = "ROBUST G2 REVERSAL -- Z1 fails, Z2 passes"
        elif namb:
            dec = "MODEL-FORM-DEPENDENT FEASIBILITY"
        else:
            dec = "MIXED BUT ROBUST"
        rows.append({"N_required": round(n, 2), **{f"{a}_status": st[a] for a in ARCH},
                     **{f"{a}_{L}": round(nf[L][a], 1) for a in ARCH for L, *_ in LAWS},
                     "architecture_decision": dec,
                     "label": "PARAMETRIC -- N_required is OPEN, no project requirement exists"})
    f = OUT / "g2_decision_map.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}  ({len(rows)} grid points)")

    # ---- the boundaries, exactly
    allpass_hi = min(lo.values())
    allfail_lo = max(hi.values())
    print("\n=== ROBUST DECISION REGIONS ===")
    print(f"  ROBUST ALL-PASS  : N_required <= {allpass_hi:.0f}")
    print(f"  MODEL-FORM AMBIGUOUS: {allpass_hi:.0f} < N_required <= {allfail_lo:.0f}"
          f"   (a factor of {allfail_lo/allpass_hi:.1f})")
    print(f"  ROBUST ALL-FAIL  : N_required > {allfail_lo:.0f}")

    # ---- THE key question of Sec.3
    z1_fails_all = hi["Z1"]        # N_required must EXCEED this for Z1 to fail under every law
    z2_passes_all = lo["Z2"]       # N_required must NOT exceed this for Z2 to pass under every law
    print("\n=== Sec.3 KEY QUESTION: any N_required where ALL models agree Z1 FAILS and Z2 PASSES? ===")
    print(f"  Z1 fails under EVERY law only when   N_required >  {z1_fails_all:.0f}")
    print(f"  Z2 passes under EVERY law only when  N_required <= {z2_passes_all:.0f}")
    if z2_passes_all > z1_fails_all:
        print(f"  -> YES: robust reversal band is ({z1_fails_all:.0f}, {z2_passes_all:.0f}]")
    else:
        print(f"  -> NO. The two conditions are DISJOINT: {z2_passes_all:.0f} < {z1_fails_all:.0f}.")
        print("     NO N_required exists at which the current models all agree that Z1 fails")
        print("     and Z2 passes. An EXPERIMENTAL ABSOLUTE-LIFE CALIBRATION IS NECESSARY")
        print("     before mechanics can alter the feasible architecture set.")
    n_rev = sum(1 for r in rows if r["architecture_decision"].startswith("ROBUST G2 REVERSAL"))
    print(f"\n  grid points classified ROBUST G2 REVERSAL: {n_rev} of {len(rows)}")
    n_amb = sum(1 for r in rows
                if r["architecture_decision"] == "MODEL-FORM-DEPENDENT FEASIBILITY")
    print(f"  grid points MODEL-FORM-DEPENDENT          : {n_amb} of {len(rows)}"
          f"  ({100*n_amb/len(rows):.1f} % of the swept range)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
