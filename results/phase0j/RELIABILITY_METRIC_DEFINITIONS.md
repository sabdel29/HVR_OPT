# Phase 0J Sec. 1 — The three reliability metrics, frozen

Three quantities are available from the Phase-0I local submodel. They are frozen here **before**
any life law is chosen, so that no metric can be redefined to suit a law found later. All three
are computed from the **same solve** and the **same output records**.

Implementation: `scripts/phase0j/native_metrics.py`, using
`scripts/phase0ir/cycle_audit.py::cycle_quantities` and
`scripts/phase0ir/decompose.py::decompose`.

---

## Common definitions — identical for M1, M2 and M3

| property | value |
|---|---|
| **solver** | CalculiX 2.23, `*VISCO` with `CETOL=1e-2` |
| **material** | SAC305: `*ELASTIC` E(T), `*PLASTIC` σ(T) (Chaboche-derived), `*CREEP, LAW=NORTON` A(T), n(T) fitted to 19 measured points, valid **7.5–16 MPa** |
| **solver fields read** | `PEEQ` (scalar), `S` (6-component Cauchy stress), `E` (6-component **total** strain), `EVOL` (element volume), `NT` (nodal temperature) |
| **averaging volume** | element set `ESOLCORE` — the solder core, **volume-weighted**: `Σ(q_e·V_e)/Σ(V_e)` |
| **corner exclusion rule** | **one element** removed from each free-edge corner of the bimaterial solder/pad interface. Retaining the corner LOWERS the value, so the metric is not corner-dominated; the 0/1/2-element span is 6.4 % |
| **geometry** | equal-area square prism of side 354.49 µm and height 300 µm, representing the June-2026 400 µm ball at 800 µm pitch, between explicit Cu pads |
| **stabilised cycle** | first cycle whose value differs from the previous cycle by < 5 %. **All values reported are cycle 4 of 4**, achieved at 0.48–2.00 % |
| **plastic included?** | **YES** in all three |
| **creep included?** | **YES** in all three — proven in Phase 0I-R by a creep-only deck with no `*PLASTIC` card giving PEEQ/eq(ε_in) = 1.0000 |

**Temperature is read from the solver, never reconstructed.** CalculiX ramps `*TEMPERATURE`
linearly across a step unless `AMPLITUDE=STEP` is given; reconstructing T analytically from the
step schedule corrupts the thermal-strain subtraction and produced negative dissipation in the
first Phase-0I-R attempt. `NT` is read instead.

The inelastic strain tensor used by M2 and M3 is obtained by decomposition, not by a solver
field (CalculiX produces no separate inelastic tensor):

```
eps_inelastic = E_total − C(T)^-1 : S − alpha·(T − T_ref)·I
eq(e)         = sqrt( 2/3 · e'_ij · e'_ij )        on the deviatoric part
```

---

## METRIC M1 — accumulated equivalent inelastic PATH per stabilised cycle

```
M1 = < PEEQ(t_end of cycle k) − PEEQ(t_end of cycle k−1) >_V
```

**Units:** dimensionless (strain).
**Character:** a **path length**. PEEQ accumulates monotonically along the deformation path and
never decreases; differencing over one cycle removes the accumulation but keeps the path
character. **M1 is NOT a strain range** and must never be described as one.
**Contents:** plastic **and** creep, inseparably — CalculiX aliases `CEEQ`, `CE` and `PE` to
`PEEQ` and produces no separate creep field.
**This is the Phase-0I metric**, unchanged in value.

## METRIC M2 — direct within-cycle inelastic strain RANGE

```
M2 = < max_t eq(eps_inelastic(t)) − min_t eq(eps_inelastic(t)) >_V ,  t in the stabilised cycle
```

**Units:** dimensionless (strain).
**Computed DIRECTLY from the time history at every output point.** Sec. 2 forbids obtaining it
as `M1 / 3.72`, and Sec. 10 of this phase shows why that would have been wrong by 84 % — see
below.
**Character:** a range of an oscillating instantaneous quantity, the conventional input to a
strain-range fatigue law.

## METRIC M3 — dissipated inelastic energy density per stabilised cycle

```
M3 = < SUM_k  sigma_mid : d(eps_inelastic)  >_V   over the stabilised cycle
   sigma_mid = (sigma_k + sigma_k−1)/2         trapezoidal in stress
   the contraction uses the ENGINEERING SHEAR FACTOR 2 on the three shear terms
```

**Units:** MPa × strain = **MJ/m³** (equivalently N·mm/mm³, or MPa).
**Per-cycle, not cumulative** — the integral runs over the stabilised cycle only.
**Both plastic and creep** contribute, since `d(eps_inelastic)` is the full inelastic increment.
**Integration region:** the same volume-averaged solder core with the same corner exclusion,
**not** a thin interface layer. This matters for Darveaux-class laws — see
`LIFE_LAW_ADMISSIBILITY.md`.
Positivity was verified: every case dissipates positive inelastic work.

---

## Sec. 10 — the M1/M2 ratio is a property of the LOADING PATH, not of the material

Phase 0I-R measured `M1/M2 = 3.72` and stated it was not universal. Phase 0J tests that
directly by computing both metrics natively at **all eleven** z-sweep points
(`native_metrics_by_architecture.csv`):

| loading trajectory | ΔT | displacement path | **M1/M2** |
|---|---|---|---|
| **all 11 DVPD architecture cases** — Z1/Z2/Z4, h_sub 0.3–2.0 mm | 56.1–58.2 K | **unidirectional** 0 → du → 0 | **2.023 – 2.027** |
| Phase-0I-R decomposition case | 100 K | **fully reversed** −du → +du → −du | **3.72** |

**The ratio is set by the trajectory.** A unidirectional out-and-back path traverses the same
strain excursion twice, giving the textbook factor of ≈ 2; a fully-reversed path traverses a
larger multi-reversal excursion and gives 3.7. Across three architectures and a 6.7× span in
substrate thickness the ratio varies by **0.2 %** — it is insensitive to architecture and
geometry, and sensitive to cycle shape alone.

**Consequence.** Had the Phase-0I-R factor 3.72 been used to convert M1 into a strain range for
the architecture cases, M2 would have been under-predicted by a factor 3.72/2.03 = **1.84**, and
any strain-range life law fed that number would have been wrong by 1.84^m — a factor of **2.6 at
m = 1.5** and **6.2 at m = 3**. This is the concrete justification for the Sec. 2 rule.

---

## The cycle these metrics describe

Recovered from the deck, not assumed (see `cycle_compatibility_audit.md`):

| property | value |
|---|---|
| T_min | 25.0 °C |
| T_max | 81.10 – 83.21 °C (architecture-dependent) |
| **ΔT** | **56.1 – 58.2 K** |
| T_mean | 53.05 – 54.11 °C |
| **dwell at each extreme** | **ZERO** — `*TEMPERATURE` carries no `AMPLITUDE=STEP`, so CalculiX ramps linearly across each 300 s step |
| ramp rate | ≈ 11.6 K/min |
| period | 600 s |
| waveform | symmetric triangle |

Because the waveform has no hold, the creep contribution accumulates entirely during the ramps.
Any life law whose calibration depends on dwell time is therefore not directly applicable — this
is tested explicitly in Sec. 15.
