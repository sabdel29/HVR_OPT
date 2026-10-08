# Part 10 — predeclared model-form robustness gate

**Declared 2026-09-16T06:31:06Z UTC, BEFORE any Z2/Z1 ratio under a new constitutive family (Garofalo,
Anand, piecewise-saturating) existed.** At the time of writing the only Z2/Z1 numbers in
existence are the Phase-0L Norton-family results (M0_COARSE, M0_FINE, M1, M1_NLO, M1_NHI),
which gave 1.17–1.39 at the operating baseline. No run under any other model family has been
performed.

## The quantity under test

For each defensible constitutive model $m$ in the Part-9 envelope, and each **native response
metric** $M$ (creep strain, inelastic energy, stress relaxation), the architecture ratio is

$$ r_m = M_{Z1}(m) \; / \; M_{Z2}(m) $$

written so that $r_m > 1$ means **Z2 accumulates less damage than Z1**. The model-form spread is

$$ S \;=\; \frac{\max_m r_m - \min_m r_m}{\mathrm{median}_m \, r_m} . $$

## The architecture effect it is measured against

The Phase-0L envelope is $r = 1.17$–$1.39$. The conservative (smallest) architecture effect is
therefore $E_{\min} = 0.17$.

## Predeclared classification

Evaluated in this order; the **first** matching row wins.

| # | Classification | Condition |
|---|---|---|
| 1 | **MODEL-FORM DEPENDENT** | any defensible model gives $r_m \le 1$ (an ordering reversal) |
| 2 | **INSUFFICIENT EVIDENCE** | fewer than **three** distinct model FAMILIES can be parameterised over the package stress range from source-defensible evidence |
| 3 | **MAGNITUDE ROBUST** | every $r_m > 1$ **and** $S \le 0.25\,E_{\min} = 0.0425$ |
| 4 | **ORDERING ONLY ROBUST** | every $r_m > 1$ **and** $0.0425 < S \le 1.00\,E_{\min} = 0.17$ |
| 5 | **ORDERING ROBUST, MAGNITUDE UNBOUNDED** | every $r_m > 1$ **and** $S > 0.17$ |

"Model FAMILY" means a distinct functional form — Norton power law, hyperbolic-sine/Garofalo,
Anand/unified viscoplastic, piecewise-saturating. Perturbing the parameters of one family
(M1_NLO, M1_NHI) does **not** create a second family; that is parametric, not model-form,
uncertainty, and row 2 is written to prevent a parametric sweep being presented as a model-form
result.

## Justification of the thresholds

Row 1 is decisive on its own: the claim being defended is an **ordering**, so a single defensible
reversal withdraws it regardless of how tight the spread is.

Row 2 exists because this phase begins with only one family parameterisable at package stresses.
Declaring "robust" from one family, or from one family plus perturbations of its own exponent,
would be circular — it would test the parameters and report on the form. Three families is the
minimum at which the word "model-form" is honest.

Rows 3 and 4 use the same 4:1 signal-to-nuisance ratio the project already applies elsewhere to
separate a real effect from a nuisance term, now against the smaller Phase-0L effect floor of
0.17 rather than Phase-0L's 0.21.

Row 5 is new relative to Phase 0L and is deliberately weaker than "ordering only robust": if the
spread exceeds the whole architecture effect, the sign may still survive every model tested, but
nothing about the magnitude may be quoted, not even as an envelope.

## Commitments

- These thresholds are frozen. They will not be revised after results are seen.
- A result landing near a boundary follows the inequality as written.
- $S$ is computed over the model set fixed by Part 9 before any ratio is computed, not over a
  subset chosen afterwards.
- If row 2 fires, no robustness claim of any kind is made from this phase's model-form work, and
  the Phase-0L parametric result stands unchanged as the maximum defensible statement.
