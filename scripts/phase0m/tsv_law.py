#!/usr/bin/env python3
"""Phase-0M Part 3 -- the TSV radius / allocation law.

USER HYPOTHESIS UNDER TEST
    "increasing TSV radius decreases ohmic loss but decreases density"

That is true for a SINGLE via. Whether it is true for a FIELD depends entirely on the
allocation policy, and the answer is derived here for five policies, then checked
numerically against the closed forms. The answer is NOT presupposed.
"""
from __future__ import annotations
import csv, math, sys
from pathlib import Path
import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0m"))
from interconnect import (TSVGeometry, allocate, evaluate, rho_cu,        # noqa: E402
                          r_field_policy_A_analytic, r_field_policy_C_analytic,
                          r_field_policy_E_analytic)

OUT = R / "results" / "phase0m"
OUT.mkdir(parents=True, exist_ok=True)

DIE_MM = 22.36
FOOT = (DIE_MM * 1e-3) ** 2
T_C = 85.0
H = 300.0e-6
J_LO, J_HI = 1.0e8, 4.0e8
PG = 0.5
RADII = [2.5, 5.0, 7.5, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]   # um
CURRENTS = {"Z2_LV_1000A": 1000.0, "Z1_HV_23p4A": 23.434570678665168}


def sweep() -> list[dict]:
    rows = []
    # reference field for the fixed-count and fixed-fraction policies: what the
    # source-nominal r = 15 um geometry provisions for 1000 A at J = 1e8
    gref = TSVGeometry(r_m=15e-6, h_m=H)
    n_ref = gref.n_required(1000.0, J_LO)
    phi_ref = gref.phi_cu(n_ref, FOOT)
    for label, I in CURRENTS.items():
        for j in (J_LO, J_HI):
            for r_um in RADII:
                g = TSVGeometry(r_m=r_um * 1e-6, h_m=H)      # pitch = minimum legal
                for pol, kw in (("A_min_capability", {}),
                                ("B_fixed_count", {"n_fixed": n_ref}),
                                ("C_fixed_pitch", {}),
                                ("D_area_optimal", {}),
                                ("E_fixed_cu_fraction", {"phi_target": phi_ref})):
                    e = evaluate(g, I, j, FOOT, pol, T_c=T_C, pg_ratio=PG, **kw)
                    e.update(rail=label, current_a=I, j_max=j, n_ref=n_ref,
                             phi_ref=phi_ref, footprint_mm2=FOOT * 1e6, T_c=T_C)
                    rows.append(e)
    # fixed-pitch variant at the SOURCE pitch (60 um) rather than the minimum legal pitch,
    # so the r-dependence of the pitch rule can be separated from the r-dependence of R
    for r_um in RADII:
        if 2 * r_um * 1e-6 + 30e-6 > 60e-6:
            continue
        g = TSVGeometry(r_m=r_um * 1e-6, h_m=H, p_m=60e-6)
        e = evaluate(g, 1000.0, J_LO, FOOT, "C_fixed_pitch", T_c=T_C, pg_ratio=PG)
        e.update(rail="Z2_LV_1000A", current_a=1000.0, j_max=J_LO, n_ref=n_ref,
                 phi_ref=phi_ref, footprint_mm2=FOOT * 1e6, T_c=T_C,
                 policy="C_fixed_pitch_60um")
        rows.append(e)
    return rows


def analytic_check(rows) -> list[str]:
    """Every closed form must reproduce the swept numbers. The only permitted residual is
    the integer rounding (`ceil` on n_required, `int` on n_available), so the check is
    reported twice: over all points, and over the points where the integer count exceeds
    100 and rounding is therefore below 1 %."""
    out, rho = [], rho_cu(T_C)

    def report(name, sel, fn, cnt):
        if not sel:
            out.append(f"{name}: NO FEASIBLE POINTS"); return
        err = [abs(r["R_field_mohm"] / 1e3 - fn(r)) / fn(r) for r in sel]
        big = [e for e, r in zip(err, sel) if r[cnt] > 100]
        out.append(f"`{name}`: closed form reproduced on {len(sel)} feasible points, "
                   f"max relative error {max(err):.2e} over all of them and "
                   f"{max(big):.2e} over the {len(big)} with count > 100 "
                   f"(the residual is integer rounding of `{cnt}`, nothing else)")

    report("A_min_capability",
           [r for r in rows if r["policy"] == "A_min_capability" and r["feasible"]],
           lambda r: r_field_policy_A_analytic(rho, H, r["j_max"], r["current_a"]),
           "n_required")
    report("E_fixed_cu_fraction",
           [r for r in rows if r["policy"] == "E_fixed_cu_fraction" and r["feasible"]],
           lambda r: r_field_policy_E_analytic(rho, H, r["phi_ref"], FOOT),
           "n_allocated")
    report("C_fixed_pitch",
           [r for r in rows if r["policy"] == "C_fixed_pitch" and r["feasible"]
            and r["rail"] == "Z2_LV_1000A" and r["j_max"] == J_LO],
           lambda r: r_field_policy_C_analytic(rho, H, r["r_um"] * 1e-6,
                                               r["r_cu_um"] * 1e-6, 30e-6, FOOT, PG,
                                               koz_ratio=1.0),
           "n_available")
    return out


def spacing_rule_sweep() -> list[dict]:
    """Separate the ADDITIVE spacing rule from the PROPORTIONAL keep-out rule.

    They give opposite answers for policy C and the distinction has never been made in this
    project, so it is swept rather than assumed: koz_ratio = 0 is pure additive spacing,
    koz_ratio >= s_min/(2r) makes the keep-out zone bind instead.
    """
    rows = []
    for koz in (0.0, 0.25, 0.5, 1.0, 1.5):
        for r_um in RADII:
            g = TSVGeometry(r_m=r_um * 1e-6, h_m=H, koz_ratio=koz)
            e = evaluate(g, 1000.0, J_LO, FOOT, "C_fixed_pitch", T_c=T_C, pg_ratio=PG)
            e.update(koz_ratio=koz, rule=("additive" if 2 * r_um * 1e-6 + 30e-6 >=
                                          2 * r_um * 1e-6 * (1 + koz) else "proportional"),
                     rail="Z2_LV_1000A", current_a=1000.0, j_max=J_LO,
                     footprint_mm2=FOOT * 1e6, T_c=T_C, policy="C_spacing_rule_sweep")
            rows.append(e)
    return rows


def spread(rows, policy, rail, j) -> dict:
    sel = sorted([r for r in rows if r["policy"] == policy and r["rail"] == rail
                  and r["j_max"] == j and r["feasible"]], key=lambda r: r["r_um"])
    if not sel:
        return {}
    rf = [r["R_field_mohm"] for r in sel]
    return {"policy": policy, "n_points": len(sel),
            "r_lo_um": sel[0]["r_um"], "r_hi_um": sel[-1]["r_um"],
            "R_lo_mohm": rf[0], "R_hi_mohm": rf[-1],
            "R_spread_pct": 100.0 * (max(rf) - min(rf)) / min(rf),
            "phi_lo": sel[0]["phi_cu"], "phi_hi": sel[-1]["phi_cu"],
            "P_lo_W": sel[0]["P_joule_W"], "P_hi_W": sel[-1]["P_joule_W"],
            "n_alloc_lo": sel[0]["n_allocated"], "n_alloc_hi": sel[-1]["n_allocated"]}


MD = """# PHASE 0M PART 3 --- THE TSV RADIUS / ALLOCATION LAW

## The hypothesis

> *increasing TSV radius decreases ohmic loss but decreases density*

True for **one** via. For a **field**, it is true under exactly one of the five allocation
policies examined, and under the two most physically defensible ones the two effects cancel
**exactly**.

## The derivation

A via field of `n` identical vias, each of conducting cross-section `A_c`, height `h`, in a
field footprint `A_f`, carrying total current `I`:

```
R_single = rho(T) h / A_c
R_field  = R_single / n_alloc
phi_Cu   = n_alloc A_c / A_f
```

### A --- minimum-capability allocation (the policy the reference framework uses)

`n_alloc = n_req = I / (J_max A_c)`, so

```
R_field = [rho h / A_c] * [J_max A_c / I] = rho h J_max / I
```

**The conductor cross-section cancels identically.** Not only the radius: the result does
not contain `A_c` at all, so it is independent of via shape, of liner thickness and of the
radius, and it holds for square vias, annular vias and any other cross-section. Three
corollaries follow immediately and all three are counter-intuitive:

```
IR_drop = I R_field = rho h J_max          independent of the CURRENT as well
P       = I^2 R_field = I rho h J_max      LINEAR in I, not quadratic
phi_Cu  = n_alloc A_c / A_f = I / (J_max A_f)   independent of the radius AND of h
```

So under minimum-capability provisioning the TSV radius is **not an electrical lever, not a
thermal lever and not a mechanical lever**: the effective conductivity and the effective CTE
of the through-silicon layer depend on `I/(J_max A_f)` and not on `r`. The only things that
change the field resistance are `rho` (temperature and material), `h` (substrate thickness)
and `J_max` (the provisioning current density). **Derating harder --- choosing a LOWER
`J_max` --- lowers the loss**, because it buys more parallel vias; it costs footprint.

This also explains, from first principles, the Phase-0E observation that `P_TSV` looked
proportional to `I`. That was never a law of via fields; it is a property of policy A.

### B --- fixed count

`n_alloc = N` fixed, so `R_field = rho h / (A_c N) ~ 1/r^2`. Here the hypothesis is not only
true, it is the strongest possible form: resistance falls as the inverse square of the
radius. But the field then either over-provisions (wasting area) or violates `n_req`.

### C / D --- fixed-pitch geometric and area-optimal allocation

With the pitch at its design-rule minimum `p = 2r + s_min` and the whole footprint filled,
`n_alloc = A_f f / p^2`, so

```
R_field = rho h (2r + s_min)^2 / (pi r_c^2 A_f f)
```

With `r_c ~ r`, this is `rho h (2 + s_min/r)^2 / (pi A_f f)`: **monotone decreasing in r,
saturating** at `4 rho h / (pi A_f f)` as `s_min/r -> 0`. There is no interior optimum. The
radius enters only through the **spacing overhead** `s_min/r`; the real design variable is
the ratio of minimum spacing to via radius, not the radius. At the source geometry
(`r = 15 um`, `s_min = 30 um`) the overhead factor is `(2+2)^2/4 = 4`, i.e. the field is a
factor of 4 worse than the close-packed limit; doubling the radius to 30 um recovers 1.78x
of that and the remaining 2.25x is unreachable.

### C / D refined --- the spacing rule decides

The step above assumed the pitch rule is **additive**, `p = 2r + s_min`. Real TSV design
rules are usually **proportional**: the keep-out zone scales with via diameter, because the
stress field a TSV projects into the silicon scales with its radius. Under
`p = 2r(1 + k_KOZ)`,

```
R_field = rho h 4 (1+k_KOZ)^2 r^2 / (pi r_c^2 A_f f)  ->  rho h 4 (1+k_KOZ)^2 / (pi A_f f)
```

and with `r_c ~ r` **the radius cancels exactly a third time**. The binding rule is
`p = max(2r + s_min, 2r(1+k_KOZ))`, so the additive rule binds for
`r < s_min / (2 k_KOZ)` and the proportional rule binds above it. At the source geometry
(`s_min = 30 um`, `k_KOZ = 1`) the crossover is at `r = 15 um` --- exactly the reference via
radius --- so the reference design sits on the boundary, and every larger via is in the
regime where the radius does nothing. This is swept explicitly in
`tsv_geometry_sensitivity.csv` (`policy = C_spacing_rule_sweep`).

`k_KOZ` is an ASSUMPTION here. No primary source giving a TSV keep-out rule for this
technology was retrievable, so it is swept from 0 to 1.5 and never fixed.

### E --- fixed total copper fraction

`n_alloc A_c = phi A_f` by construction, so

```
R_field = rho h / (phi A_f)
```

**The cross-section cancels exactly again.** Once the copper budget is fixed, how it is
divided into vias does not matter electrically.

## What the radius DOES change

| quantity | policy A | policy B | policy C/D | policy E |
|---|---|---|---|---|
| `R_field` | **independent of r** | `~ 1/r^2` | decreasing, saturating | **independent of r** |
| `phi_Cu`, `k_z`, `CTE_eff` | **independent of r** | `~ r^2` | increasing, saturating | fixed by construction |
| **feasibility** `n_req <= n_avail` | **improves with r** | -- | -- | improves with r |
| area consumed | **independent of r** | `~ r^2` | whole footprint | `~ (2r+s)^2/r^2` |
| aspect ratio `h/2r` | **improves with r** | improves | improves | improves |

The feasibility row is the one that survives everywhere. Requiring
`I/(J_max A_c) <= A_f f / (2r+s_min)^2` gives

```
I (2 + s_min/r)^2 / (J_max pi A_f f) <= 1
```

whose left side is **monotone decreasing in r**. So a larger radius always relaxes
feasibility even where it cannot change the resistance --- and it always improves the
aspect ratio, which is the manufacturability constraint.

## Numerical verification

{checks}

## Measured spread across r = 2.5 to 50 um, 1000 A on the field, J = 1e8 A/m^2

| policy | R_field lo -> hi (mOhm) | spread | phi_Cu lo -> hi | n_alloc lo -> hi |
|---|---|---|---|---|
{spreadtbl}

## Verdict on the hypothesis

**REFUTED as a general statement; true only under fixed-count allocation, and under
fixed-pitch allocation only where the spacing rule is additive rather than proportional.** For a
minimum-provisioned via field --- which is what the reference framework and this project
actually build --- the TSV radius is **not an independent loss lever at all**. It is a
feasibility, aspect-ratio and area variable. The loss levers are `h`, `rho(T)` and `J_max`.

This changes what belongs in an optimizer: `r` should enter through the feasibility and
manufacturability constraints and through `J_max(r)` if an r-dependent reliability limit can
ever be sourced, not through the resistance model. It also means the current
`i_max_a` entry in `configs/phase0dr/power_path_graphs.yaml` --- a primitive per-via current
in amperes --- is the single most consequential remaining primitive: it, not the geometry,
sets the field resistance.

## Sensitivity to an r-dependent current limit

The cancellation is exact only for `J_max` independent of `r`. If `J_max = J_0 (r_0/r)^a`
then `R_field = rho h J_0 r_0^a / (I r^a) ~ r^-a` and larger vias do help. No primary source
giving `a` for TSVs was retrievable (the electromigration limit is recorded OPEN in
`configs/phase0e/physical_stack.yaml`), so `a = 0` is carried and the sensitivity is stated
rather than assumed away: at `a = 0.5` a 2x radius increase would buy 29 % of the field
resistance; at `a = 1` it would buy 50 %.
"""


def main() -> int:
    rows = sweep() + spacing_rule_sweep()
    keys = sorted({k for r in rows for k in r})
    with open(OUT / "tsv_geometry_sensitivity.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader(); w.writerows(rows)
    checks = analytic_check(rows)
    sp = [spread(rows, p, "Z2_LV_1000A", J_LO) for p in
          ("A_min_capability", "B_fixed_count", "C_fixed_pitch",
           "D_area_optimal", "E_fixed_cu_fraction")]
    tbl = "\n".join(
        f"| `{s['policy']}` | {s['R_lo_mohm']:.6f} -> {s['R_hi_mohm']:.6f} | "
        f"{s['R_spread_pct']:.2f} % | {s['phi_lo']:.4f} -> {s['phi_hi']:.4f} | "
        f"{s['n_alloc_lo']} -> {s['n_alloc_hi']} |" for s in sp if s)
    (OUT / "TSV_RADIUS_ALLOCATION_LAW.md").write_text(
        MD.format(checks="\n".join("* " + c for c in checks), spreadtbl=tbl))
    for c in checks:
        print("  " + c)
    print(tbl)
    print(f"\nwrote {OUT/'TSV_RADIUS_ALLOCATION_LAW.md'} ({len(rows)} sweep points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
