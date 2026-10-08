# ET Objective — frozen BEFORE any mechanical evaluation

Written and committed to disk before the mechanical replay was run, so that the ET ranking
cannot be reverse-engineered from the warpage results. Timestamp is the file mtime.

## Primary ET objective

Adopted unchanged from the June-2026 DVPD framework, which minimises **total system-wide
power loss subject to footprint, power-density and ripple constraints**:

    J_ET  =  P_elec_total  =  P_conv_total + P_PDN            [W, minimise]

    P_conv_total = sum_j P_conv,j(I_j, T_j, arch_j, f_sw,j)    converter loss, all VRs
    P_PDN        = P_lateral + P_TSV                          package distribution loss
    P_lateral    = sum_i I_i^2 R_eff,i                        Manhattan parallel-conductance
    P_TSV        = sum_j I_v,j^2 R_field,j(h_sub, T)          vertical field, series per VR

Equivalently, end-to-end efficiency `eta = P_die / (P_die + P_elec_total)`, which is a
monotone transform of J_ET and therefore produces an identical ranking.

## Feasibility filter (a candidate is excluded, not penalised)

1. converter ripple satisfied: `|dI_out| <= ripple_factor * I_out` (0.5)
2. converter area feasible within its per-layer budget `A_budget = I_out / J_target`
3. ET fixed point converged (dT_max < 0.05 K and dP/P < 1e-3)
4. thermal: `T_max <= 100 degC` — weakly source-backed (June flags hotspots above 100 degC)

## ET Pareto tuple

    (P_elec_total, T_max)          both minimised

Temperature is carried as a second ET objective because it is an ET quantity, is reported by
the June framework, and is a legitimate design concern independent of mechanics.

## ETM extension (applied only after the ET ranking is frozen)

    (P_elec_total, T_max, die_warpage_pv)

Die peak-to-valley warpage is the ONLY mechanical objective admitted. Per Phase-0C:
interface peel is UNRESOLVED AT M0 and excluded; local Si/Cu stress from the H0 homogenised
model is invalid (+82-97% error vs discrete) and excluded; package warpage and interface
shear may be reported as secondary but do not enter the ranking.

## Ranking rule

Lexicographic ranking is NOT used. Comparison is by **Pareto dominance** on the tuples above.
Any scalarisation `J = P_elec + lambda * w` is used for sensitivity only, with lambda swept
across its full plausible range, and no claim rests on a single lambda.

## What would count as a G1 architecture reversal

A material change in the preferred architecture, not a rank shuffle among near-ties:
- the ET-optimal candidate is Pareto-dominated once warpage is included, OR
- the preferred level of a DVPD variable (h_sub, HVR footprint, converter operating point)
  or the preferred placement class differs between the ET and ETM Pareto sets.

A change of one or two rank positions among candidates whose objectives differ by less than
the numerical uncertainty does NOT count.
