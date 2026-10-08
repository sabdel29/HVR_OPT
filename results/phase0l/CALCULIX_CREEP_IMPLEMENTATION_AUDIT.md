# CalculiX 2.23 viscoplastic implementation audit

**Phase 0L, Part III.** What the solver actually integrates when `*ELASTIC`, `*PLASTIC` and
`*CREEP, LAW=NORTON` appear in one material definition and the step is `*VISCO`.

Nothing in this document is taken from prior HVR_OPT prose. Every statement is traced either to
the CalculiX 2.23 source, to the CalculiX 2.22 User's Manual, or to a controlled solver probe
run against the production material card.

## 0. Provenance

| Item | Value |
|---|---|
| Solver binary | `/home/beams0/MGHARIB/envs/etm/bin/ccx`, reports `This is Version 2.23` |
| Binary md5 | `210ee00fe6c6610666b47838780efe19` |
| Source | `http://www.dhondt.de/ccx_2.23.src.tar.bz2` |
| Source sha256 | `9c88385c10fb04f5dc6c4e98027a51bebdd8aee3920e05190d6c1dd08357d6e7` |
| Manual | `http://www.dhondt.de/ccx_2.22.pdf` (2.23 manual not published separately) |
| Probe artifact | `results/phase0l/calculix_creep_probe.csv` (2556 increments) |

The conda binary was not built from this tarball, so the source is a *hypothesis* about the
binary, not proof. The link is empirical: the law derived below reproduces the binary's output
to a median relative error of 2e-5 over 960 independent increments (Part IV, TEST C). Source
and binary are treated as agreeing only because they were measured to agree.

## 1. Relevant manual definition

Manual §7.29 `*CREEP` (p. 448) states the Norton law as

> ε̇ = A σ^n t^m &nbsp;&nbsp;(863)
> where ε is the equivalent creep strain, **σ is the true Von Mises stress** and t is the total
> time.

Manual §6.8.x, "Incremental (visco)plasticity" (p. 261) states something different:

> The viscoplastic model implemented in CalculiX is an **overstress model, i.e. creep only
> occurs above the yield stress**. For a lot of materials this is not realistic. At high
> temperatures creep is frequently observed well below the yield stress. **To simulate this
> behavior one can set the yield stress to zero.**

**These two passages are inconsistent, and the inconsistency is the origin of DEFECT #40.**
§7.29 is the page a user reads when writing a `*CREEP` card; it says the driving variable is the
von Mises stress. §6.8 is the page that describes what is integrated; it says creep is driven by
the excess over yield. The source (§4 below) implements §6.8. A calibration performed against
§7.29 — which is what `scripts/phase0i/solder_model.py` did — produces a card that the solver
then consumes under a different definition.

Two further manual statements, both confirmed by probe:

- "Notice that creep behavior is switched off in a `*STATIC` step." (confirmed, §3)
- "If for LAW=NORTON the temperature data points under the `*CREEP` card are not the same as
  those under the `*ELASTIC` card, the creep data are interpolated at the `*ELASTIC` temperature
  data points." (confirmed, §7)

## 2. Relevant source routines

| File | Role |
|---|---|
| `src/creeps.f` | parses `*CREEP`; sets `nelcon(1,nmat) = -52`; pre-interpolates A,n,m onto the `*ELASTIC` temperature points |
| `src/materialdata_me.f` | interpolates the material constants to the integration-point temperature at run time |
| `src/incplas.f` | **the constitutive integration** — trial state, yield test, coupled Newton solve for the consistency parameter |
| `src/creep.f` | the `LAW=USER` hook only; *not* used for `LAW=NORTON` |

`src/creep.f` is a template user subroutine containing a hard-coded ε̇ = σ⁵/1e10. It is reached
only when `elconloc(3) < 0`, the marker `creeps.f:217-222` writes for `LAW=USER`. The production
decks use `LAW=NORTON`, so `creep.f` is never called and its contents are irrelevant.

## 3. Input variables and the *STATIC / *VISCO switch

`incplas.f:122-126`

```fortran
      if((nmethod.ne.1).or.(ithermal(1).eq.3)) then
         ivisco=1
      else
         ivisco=0
      endif
```

`nmethod = 1` is `*STATIC`. `incplas.f:136` then gates the creep constants on
`(kode.eq.-52).and.(ivisco.eq.1)`, and `incplas.f:572` routes a `*STATIC` step to the
rate-independent plastic branch. So the **same material card behaves as two different models**:

- `*VISCO` step → viscoplastic overstress law, stress may exceed the `*PLASTIC` curve
- `*STATIC` step → rate-independent plasticity, stress capped at the `*PLASTIC` curve, no creep

All HVR_OPT thermal-cycling decks use `*VISCO`.

The Norton constants, `incplas.f:141-144`:

```fortran
            xxa=elconloc(3)*(ttime+time)**elconloc(5)
            if(xxa.lt.1.d-20) xxa=1.d-20
            xxn=elconloc(4)
            a1=xxa*dtime
```

`elconloc(1..5)` = E, ν, A, n, m (`materialdata_me.f:180-182` maps `nelconst = -52` → 5
constants). `ttime+time` is total elapsed analysis time, **not** step time.

## 4. Exact creep-rate expression

Trial state and yield test, `incplas.f:310-311`:

```fortran
      ftrial=dxitril-dsqrt(2.d0/3.d0)*fiso
      if((ftrial.le.1.d-10).or.(ielas.eq.1).or.(ielastic.eq.1)
     &    .or.(dtime.lt.1.d-30)) then
```

`dxitril = ‖ξ_trial‖ = sqrt(2/3)·σ_vm,trial` and `fiso = σ_y(ε̄_p)`, so
`ftrial = sqrt(2/3)·(σ_vm,trial − σ_y)`. **If σ_vm,trial ≤ σ_y the branch is taken and the
increment is purely elastic: the inelastic strain increment is exactly zero, not merely small.**

Driving stress inside the Newton loop, `incplas.f:599-604`:

```fortran
               qtild=(ftrial-c2*(fiso-fiso0)
     &              -umbb*(2.d0*cop+c4*(fkin-fkin0)))/(c2*vj)
               if(qtild.lt.1.d-10) qtild=1.d-10
               decra(1)=a1*qtild**xxn
```

with `c1 = 2/3`, `c2 = sqrt(2/3)`, `c4 = c2/μ` (`incplas.f:506-509`), `umbb → G` and `vj → 1` in
the small-strain limit, `cop` the consistency parameter and `Δε̄_in = sqrt(2/3)·cop`. Substituting
and using the radial return σ_vm = σ_vm,trial − 3G·Δε̄_in:

> **q̃ = σ_vm − σ_y(ε̄_in)** — the **overstress at the end of the increment**, not the von Mises
> stress.

The integrated flow rule is therefore

> **Δε̄_in = A · (t_total)^m · Δt · ( σ_vm − σ_y(ε̄_in) )^n ,&nbsp;&nbsp; and ε̇ = 0 identically
> whenever σ_vm ≤ σ_y.**

Manual Eq. 863 is recovered only in the special case σ_y ≡ 0.

## 5. Order of the plastic update versus the creep update

There is no ordering, because **there are not two updates**. In a `*VISCO` step with
`kode = -52` the branch at `incplas.f:572` (`if((kode.eq.-51).or.(ivisco.eq.0))`) is never
taken, so the rate-independent plastic corrector never executes. A single consistency parameter
`cop` is solved from the Norton residual, and it carries the entire inelastic increment.

Consequently **the model produces no rate-independent plastic strain at all**. The `*PLASTIC`
card does not define a plastic flow rule here; it supplies the threshold function σ_y(ε̄) and its
hardening slope to the viscoplastic law. This is a Perzyna/Norton overstress model, and the
split between "plastic" and "creep" strain that the metric names M1/M3 imply does not exist in
the solution — there is one inelastic strain measure.

The Newton solve is `incplas.f:511-619`; on non-convergence in 15 iterations or a negative
`cop` it falls back to bracketed bisection (`incplas.f:620-757`), and if that fails within 100
iterations it returns `pnewdt = 0.25` to force increment cutback.

## 6. PEEQ accumulation

`incplas.f:516` and `incplas.f:1032`:

```fortran
         ep=epini+c2*cop
      ...
      xstate(1,iint,iel)=ep
```

PEEQ is the monotonically accumulated equivalent inelastic strain, ε̄ = Σ sqrt(2/3)·cop over
increments. Because `cop > 0` always (a negative root triggers the bisection fallback), **PEEQ
is non-decreasing**: it is a path length, never a within-cycle range. This is what makes the M1
metric an accumulated path and M2 a genuinely separate measurement.

Internal state variables (manual p. 261; `creeps.f:214` allocates 14, the manual documents 13):

| Index | Content |
|---|---|
| 1 | accumulated equivalent inelastic strain ε̄ (PEEQ) |
| 2–7 | (I − C_p⁻¹)/2, i.e. the infinitesimal inelastic strain tensor at small strain |
| 8–13 | back stress Γ |
| 14 | inelastic strain **rate** at the end of the increment, used only for CETOL |

`incplas.f:1040-1041` shows variable 14 driving the `*VISCO, CETOL` increment control:
`depvisc = max(depvisc, |decra(1) − dtime·rate_prev|)`. CETOL therefore limits the change in
inelastic strain *rate* across an increment, not the strain increment itself.

## 7. Temperature interpolation

Two successive linear interpolations, both confirmed by probe (TEST D):

1. **Card load time** (`creeps.f:300-330`): A, n, m are interpolated **linearly in A, n and m**
   from the `*CREEP` temperature rows onto the `*ELASTIC` temperature rows. Outside the `*CREEP`
   temperature range the values are **clamped** (`id.eq.0` → first row, `id.eq.ntmat` → last
   row), i.e. constant extrapolation.
2. **Run time** (`materialdata_me.f:413-429`): the resulting constants are interpolated
   **linearly in A, n, m** between the `*ELASTIC` temperature rows, again clamped outside.

There is no Arrhenius, no log-space, and no interpolation of the *rate*. The yield stress is
likewise interpolated linearly between `*PLASTIC` card rows (via `plmix`, `materialdata_me.f:367`).

The production card writes `*ELASTIC`, `*PLASTIC` and `*CREEP` at the **same** temperatures
(45/80/115/150 °C, `solder_model.inp_material`), so step 1 is exact at the nodes and only step 2
is active between them.

**Consequence.** `solder_model.norton_at()` builds intermediate-temperature cards by Arrhenius
interpolation of the rate at a reference stress — physically the right thing to do — but the
solver then interpolates **linearly in A** between whatever rows the card contains. Probe TEST D
at 62.5 / 97.5 / 132.5 °C measures the solver's rate at 1.000, 1.000 and 0.917 times the
linear-in-A prediction, against 1.334, 2.799 and 18.34 times the Arrhenius prediction. The
solver is unambiguously linear-in-A; the residual 0.917 at 132.5 °C is fully explained (to 0.08 %)
by σ_y interpolation, see below. **Whenever the card carries rows only at the four data
temperatures, every intermediate temperature the solver evaluates is a linear-in-A blend, and at
132.5 °C that is 18× the Arrhenius value.**

A second, smaller finding from TEST D: `sigma0_of_T()` interpolates the raw Chaboche table
(nodes at −40/−20/40/80/122 °C, clamped above 122 °C) while the solver interpolates the
`*PLASTIC` card rows (45/80/115/150 °C). At 132.5 °C these give σ_y = 10.50 vs 10.91 MPa. The
predicted rate ratio (29.09/29.50)^6.158 = 0.9173 matches the measured 0.9166. **Any Python-side
reconstruction of the solver's behaviour must use the card nodes, not the source table.**

## 8. Do creep and rate-independent plasticity share an internal effective stress?

Yes, and that is the whole point. Both the yield test (`ftrial`) and the viscous flow rule
(`qtild`) are built from the same scalar `dxitril = sqrt(2/3)·σ_vm,trial` and the same
`fiso = σ_y(ε̄)`. The hardening state ε̄ advanced by the creep flow is the *same* ε̄ that raises
the threshold. There is one yield function, one hardening variable, one effective stress, and
one inelastic strain.

## 9. Probe confirmation (Part IV)

Artifacts: `results/phase0l/calculix_creep_probe.csv` (7603 increments),
`results/phase0l/calculix_creep_probe.log`, `scripts/phase0l/calculix_creep_probe.py`.

H1 = A·σ_vm^n (the variable the card was fitted in); H2 = A·(σ_vm − σ_y0)^n;
H3 = A·(σ_vm − σ_y(PEEQ))^n, the source-derived law, evaluated with the solver's own
linear-in-A temperature interpolation.

| Test | Question | Result |
|---|---|---|
| A | creep only, no yield surface: is it ε̇ = Aσ^n? | **Yes.** 1344 increments, median \|log10(meas / Aσ^n)\| = 3e-6, max 2.1e-5 |
| B | `*PLASTIC` + `*CREEP`: which variable? | **H3.** median \|log10\| = 1.2e-5 (max 3.9e-5). H1 median factor **14.4×**, max 1.8e6×. 480 of 1344 increments have zero measured creep where H1 predicts creep |
| C | below yield, does creep occur? | **No.** 20 states at σ/σ_y = 0.25…0.99, holds to 5.8e8 s (18 years of simulated time) chosen so that Aσ^n would give ε = 1e-3. Final PEEQ = 0.0000e+00 in **every** case |
| D | narrow sweep across σ_y | **Continuous, no discontinuity.** At σ_y+0.01 MPa the measured rate is 1.06e-34 /s and matches A(σ−σ_y)^n to 0.03 %. The rate → 0 smoothly as σ → σ_y⁺ because (σ−σ_y)^n → 0; below σ_y it is identically zero. Deviations at +2 and +5 MPa (0.83–0.91) are hardening, which the no-hardening reference ignores |
| E | temperature, incl. 125/150 °C | H3 ratio 0.99995–1.00001 at 45/80/115/125/150 °C |
| F | can the card reproduce its own calibration data? | **0 of 19.** 16 points give exactly zero; the 3 with positive overstress are low by 4.7e7×, 1.8e12× and 2.4e5× |
| G | form of the temperature interpolation | **Linear in A**, ratio 0.99963/0.99978/0.99986 at 62.5/97.5/132.5 °C. Arrhenius-in-rate is refuted: 1.33×, 2.80×, **20.0×** |
| H | time-hardening exponent m | **m = 0.** PEEQ bit-identical across total-analysis-time offsets of 0, 1e3, 1e6, 1e9 s |

**H3 is confirmed to five significant figures. H1 is refuted.**

## 10. Two implementation traps found while probing

**(a) Omitting `*PLASTIC` is undefined behaviour, not "zero yield".** The manual says that with
no `*PLASTIC` card "a zero yield surface without any hardening is assumed". What actually
happens: `materialdata_me.f:331-333` sets `plconloc(801) = 0.5`, `incplas.f:130` therefore takes
`user_hardening = 1`, and `incplas.f:288` calls `uhardening()`. The shipped `src/uhardening.f`
is an empty stub — `subroutine … ; return ; end` — that never assigns `fiso`, and `incplas.f`
never initialises it. The yield stress is then whatever the stack held.

In this build the two routes agree (TEST A: median \|log10\| = 3e-6 for both "omit `*PLASTIC`"
and "`*PLASTIC` with σ_y = 1e-6 MPa"), so the uninitialised value reads as zero here. That is an
observation about one binary, not a guarantee. **Rule adopted: to obtain a zero yield surface,
write an explicit flat `*PLASTIC` card at σ_y = 1e-6 MPa rather than omitting the card.**

**(b) The `*CREEP` card is only as good as its temperature grid.** Because the solver
interpolates linearly in A while `solder_model.norton_at()` builds rows on an Arrhenius basis,
the two agree only *at* the rows. The production decks
(`run_zcompare.py:36`, `run_convergence.py:27`) write rows at −40/0/25/50/75/100/125 °C.
Consequences, at σ = 60 MPa with no yield surface
(`results/phase0l/card_temperature_grid_audit.csv`):

- **between rows**, over 45–150 °C and 20–100 MPa, the solver's rate is **0.83× to 3.88×** the
  intended Arrhenius rate; the worst case anywhere on the grid is **8.94×** (−32.5 °C, 20 MPa);
- **above the top row the card clamps.** At 150 °C the solver uses the 125 °C row, and because
  the clamped exponent (n = 6.62 instead of 5.08) is wrong as well as the clamped coefficient,
  the error is strongly stress-dependent: 0.62× at 20 MPa rising to **8.70×** at 100 MPa.

Refining the grid to 18 rows spanning −40…150 °C (`scripts/phase0l/card_grid_audit.py`, grid
`proposed_fine`) reduces the between-row span over 45–150 °C from 0.83–3.88× to **0.81–1.51×**
and removes the clamping entirely.

The 110 → 150 °C candidate experiment profile runs 25 °C above the top card row for its entire
duration. Neither effect is a solver defect; both are card-construction defects, and both are
fixed by writing rows on a finer grid that spans the full profile.
