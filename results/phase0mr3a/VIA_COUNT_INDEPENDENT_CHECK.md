# PHASE 0M-R3A SECTION 5 --- INDEPENDENT VIA-ARITHMETIC CHECK

The Phase-0M-R3 routing ratios were produced by `routing_production.edge_loss`. They are
re-derived here from the physics, without calling that function, so agreement is evidence
rather than a tautology.

## The derivation

    r_cu     = r - t_liner                       t_liner = 0.5 um
    A_cu     = pi * r_cu^2
    I_max    = J_design * A_cu                   J_design = 1.0e+08 A/m2
    n_req    = ceil(I / I_max)                   I = 20.4082 A per cell
    pitch    = max(2r + s_min, 2r(1+koz))        s_min = 30.0 um SOURCE_BACKED
    n_avail  = floor(A_pad * packing / pitch^2)  A_pad = 1.8 mm2, packing = 0.5
    ratio    = n_req / n_avail

## Result

| r | pitch | A_cu | n_required | n_available | ratio | production | agreement |
|---|---|---|---|---|---|---|---|
| 15.0 um | 60.0 um | 660.52 um2 | 309 | 250 | 1.2360 | 1.2360 | EXACT |
| 17.5 um | 65.0 um | 907.92 um2 | 225 | 213 | 1.0563 | 1.0563 | EXACT |
| 20.0 um | 70.0 um | 1194.59 um2 | 171 | 183 | 0.9344 | 0.9344 | EXACT |
| 22.5 um | 75.0 um | 1520.53 um2 | 135 | 160 | 0.8438 | 0.8438 | EXACT |
| 25.0 um | 80.0 um | 1885.74 um2 | 109 | 140 | 0.7786 | 0.7786 | EXACT |

**The Phase-0M-R3 values reproduce exactly.** 1.2360 at r = 15 um and 0.9344 at r = 20 um, to machine precision, from an implementation
that shares no code with the production path.

## Why the ratio improves with a LARGER via

Both counts scale inversely with an area, but with different lengths:

    n_req   ~ 1 / (r - t_liner)^2
    n_avail ~ 1 / pitch^2  =  1 / (2r + s_min)^2

so the ratio goes as `(2r + s_min)^2 / (r - t_liner)^2`. Because `s_min = 30 um` is a fixed
additive term, the pitch grows more slowly in proportion than the conductor area does, and
the ratio falls as r rises. This is a consequence of the additive spacing rule, not of any
scaling assumption.

## What this check does NOT establish

The arithmetic is correct. Whether a 20 um via on a 70 um pitch through 673 um of substrate
build-up is MANUFACTURABLE is a separate question, answered in
`LS_TO_L_INTERCONNECT_AUDIT.md`: there is no sourced process rule for this interconnect
class, so the geometry is a self-consistent design point in an unsourced window.
