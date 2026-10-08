# PHASE 0M PART 3 --- THE TSV RADIUS / ALLOCATION LAW

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

* `A_min_capability`: closed form reproduced on 24 feasible points, max relative error 4.86e-02 over all of them and 5.82e-03 over the 15 with count > 100 (the residual is integer rounding of `n_required`, nothing else)
* `E_fixed_cu_fraction`: closed form reproduced on 24 feasible points, max relative error 9.75e-05 over all of them and 9.75e-05 over the 24 with count > 100 (the residual is integer rounding of `n_allocated`, nothing else)
* `C_fixed_pitch`: closed form reproduced on 6 feasible points, max relative error 9.92e-05 over all of them and 9.92e-05 over the 6 with count > 100 (the residual is integer rounding of `n_available`, nothing else)

## Measured spread across r = 2.5 to 50 um, 1000 A on the field, J = 1e8 A/m^2

| policy | R_field lo -> hi (mOhm) | spread | phi_Cu lo -> hi | n_alloc lo -> hi |
|---|---|---|---|---|
| `A_min_capability` | 0.000640 -> 0.000640 | 0.07 % | 0.0200 -> 0.0200 | 15140 -> 1300 |
| `B_fixed_count` | 0.000640 -> 0.000155 | 313.91 % | 0.0200 -> 0.0828 | 15140 -> 15140 |
| `C_fixed_pitch` | 0.000140 -> 0.000133 | 4.88 % | 0.0917 -> 0.0962 | 69440 -> 6249 |
| `D_area_optimal` | 0.000140 -> 0.000133 | 4.88 % | 0.0917 -> 0.0962 | 69440 -> 6249 |
| `E_fixed_cu_fraction` | 0.000640 -> 0.000640 | 0.02 % | 0.0200 -> 0.0200 | 15140 -> 1299 |

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
