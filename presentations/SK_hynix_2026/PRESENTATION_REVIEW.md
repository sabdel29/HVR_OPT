# Presentation review

A critical read of `SK_HYNIX_HVR_TRANSIENT_ETM_2026.pptx` before it is given.
Written against the built deck, not the plan.

- 33 main slides, 15 backup, 41.5 min prepared, intended for a 50 min slot.
- Every main slide has presenter notes with `[~N s]`, spoken prose, the key
  numbers, a transition, and at least one `If asked:` pair.
- Every number is loaded from a frozen artifact at build time by `sources.py`.

---

## 1. Does the deck do what was asked?

**One story, not two talks.** The thesis slide (5) is placed before either half
and repeated as the synthesis (29). Both halves are framed as the same failure
mode: a cheap proxy gives a confident wrong ordering. Part I's proxy is steady
state; Part II's proxy is peak temperature. That is a real connection, not a
rhetorical one, and it is the strongest part of the structure.

**Audience fit.** The brief said not to assume converter or
mechanical-reliability specialists. Concretely:

- The converter is introduced topologically (slide 18) with the duty-ratio
  reason for the intermediate rail spelled out, rather than assuming hybrid
  converter fluency.
- Slide 24 exists solely to separate warpage, driver, response, damage and life
  before any mechanical number is shown. For a packaging/PI audience this is the
  slide that prevents the most likely misreading.
- A notation table is in backup (B10) covering the terms that differ most across
  packaging, PI, thermal and architecture groups.

**Claim discipline.** Limitations are on slide 2 (before results), slides 15 and
28 (per half) and slide 31 (consolidated), plus inside four figures. The
counter-case to the headline speed-up is in the same figure as the speed-up, not
in a footnote.

---

## 2. What is weakest

Listed honestly, because these are what a sharp audience will reach for.

1. **Neither study is validated.** Cross-solver verification is a real result but
   it is not evidence that the physics matches a part. This is stated four times;
   it is still the single biggest limitation.
2. **The mechanical magnitude is conditional and the bracket is one-sided.** The
   solder card is evaluated at 15–17x yield against a fit over a much lower stress
   window, and no tolerance tighter than production converges. The *ordering* is
   defensible; the third digit is not. Slide 27 says so.
3. **The two halves use different vehicles.** Part I is a GPU + 6 HBM module;
   Part II is a logic die with a distributed regulator. The connection is
   methodological, not physical. If someone pushes on this, concede it plainly —
   the deck never claims a shared geometry.
4. **The policy traces are published and were not rerun** after a later solver
   correction. Slide 14's notes say this out loud and B9/B14 repeat it.
5. **Z1's TSV loss is a negative number in the ledger.** It is 0.17 mW in
   magnitude and the sign is a small-signal artefact of an FV transition
   correction on a 74 µm path. Reported as "below 0.2 mW". If asked directly,
   say exactly that — do not quote a negative loss.
6. **18.4 % is a modest effect.** The argument does not rest on its size, it
   rests on its *sign* relative to temperature. Keep that distinction crisp;
   claiming significance for the magnitude would be the easiest way to lose the
   room.

---

## 3. Ten questions SK hynix is likely to ask

**Q1. Is this validated against measurement?**
No. Both studies are modelling. The transient work is verified against MOOSE and
Ansys Icepak on one shared physical contract — three independent implementations
of the same stated physics agreeing to within 0.452 K. That tells you the
implementations are right, not that the physics matches a part. No hardware was
measured in either study, and an instrumented vehicle is the natural next step.

**Q2. Does the 13.6x hold for our problems?**
Only if your problem is repeated transient stepping on a fixed mesh with constant
properties. It comes from factorising the operator once and back-substituting per
step, so the advantage grows with step count — about 2.3x at 25 steps,
13.6x at 400. For a single steady solve the same code is about
21x *slower*. Strong temperature-dependent conductivity, a moving mesh or a
changing boundary-condition type all break the reuse.

**Q3. Are you telling us to put regulators on the backside?**
No. This is a two-point comparison on one vehicle, frozen before solving, and
there is no optimiser behind it. What transfers is the method: evaluate placement
on the real stack across all four domains, because the thermal and mechanical
answers can disagree. Nothing here is a recommendation about any product, and I
am not making any claim about what SK hynix does today.

**Q4. 18.4 % lower response — does Z2's solder last longer?**
I can't say that, and I want to be careful here. 18.4 % is a change in an
inelastic strain *response* per cycle. Turning that into life needs a damage
correlation fitted for this alloy, this joint and this loading, and I do not have
one. A response is not damage, damage is not life, and life is not failure. What
I will defend is the ordering and its sign.

**Q5. Why should we trust a creep result that only converges at a loose tolerance?**
You should trust the ordering and treat the magnitude as conditional — which is
what the deck says. Of five tolerances, only 5e-2 and 1e-1 converge, and they are
bit-identical: same 336 increments, zero cutbacks, identical to twelve printed
digits. So the result is not an artefact of loosening. But the bracket is
one-sided — nothing tighter converges — so agreement with a tight-tolerance
reference is not demonstrated. The root cause is constitutive, not the integrator:
the joint runs at 15–17x yield against a card fitted far below that.

**Q6. Is the package buildable?**
Geometrically, yes, at a source-bounded 150 µm microvia pitch — and a pure tier
permutation takes the worst aspect ratio from 5.05 to 0.833 at constant
parts, area and stack height. But the verdict is GEOMETRICALLY REALIZABLE /
PROCESS-CONDITIONAL. Three manufacturing inputs are open: the microvia current
allowable, the capture-pad diameter, and a vendor design rule for this build-up
technology, plus two package clearances. This is not a manufacturing
qualification and should not be read as one. Backup B13 lists each input and its
status.

**Q7. Your TSV number looks too small for Z1. What is it really?**
Below 0.2 mW — effectively zero, and I report it as a bound rather than a number.
The ledger value is actually a very small negative figure, which is a known
small-signal artefact of adding a finite-volume transition correction to a
74 µm bulk path. The physical reason it is tiny is the rail: Z1's vertical
path carries the 48 V input at about 23 A, Z2's carries the 1 V output at
1000 A. That is 43x the current, and Z1's path is also 4.1x shorter.

**Q8. How much of the 2.4 W penalty is really the TSV?**
About 42 %. The rest is thermal feedback — Z2 runs +8.14 K hotter, so switch
conduction and inductor DCR rise. That split only exists because the model is
coupled; an uncoupled calculation returns the TSV term alone and under-predicts
the penalty by more than half. It is a good example of the coupling earning its
cost.

**Q9. Does any of this apply to an HBM stack specifically?**
The method does; the numbers do not. Part II's vehicle is a logic die with a
distributed regulator, not a memory stack — different geometry, different
materials, different joint. What I would carry over is the three-way separation
of warpage, local driver and local response, and the use of conductor-plane
topology rather than layer count when screening stack-ups. Part I's vehicle *is*
a GPU with six HBM stacks, so the gating and screening result is closer to your
setting.

**Q10. What about electromagnetics / power integrity at these currents?**
There is no full-wave result here. A full-wave HFSS attempt on this structure did
not converge, and I did not substitute a simplified model and present it as one.
The electrical side is a lumped and sheet-resistance network with
temperature-dependent properties and a geometry-derived vertical interconnect.
For PI questions at 1000 A that is a real gap, and I would rather name it than
paper over it.

---

## 4. Rehearsal notes

- **Three slides must not be cut:** 15, 28 and 31 (the claim boundaries). If the
  talk runs long, cut 11 (verification checks) and 19 (cooling) first — both are
  supported by backup.
- **Slide 12 is the one to slow down on.** Say the counter-case out loud; do not
  let the 13.6x travel on its own.
- **Slide 25 is the payoff.** Pause after "the three mechanical panels all go
  down". Resist the urge to oversell 18.4 %.
- **Slide 24 earns slide 25.** If the vocabulary does not land, the result reads
  as a life claim.
- Backup B1 answers most numerical questions in one place; B13 answers every
  manufacturability question; B14 answers every provenance question.

---

## 5. Build and regeneration

```
cd SK_HYNIX_HVR_TRANSIENT_ETM_2026_SOURCE
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
python figures.py                      # figs/       (titled, standalone)
FIG_DECK_MODE=1 python figures.py      # figs/deck/  (untitled, for slides)
python build_deck.py                   # the .pptx + deck_manifest.json
python make_docs.py                    # timing, source audit, claim matrix
soffice --headless --convert-to pdf --outdir .. ../SK_HYNIX_HVR_TRANSIENT_ETM_2026.pptx
```

`sources.py` fails loudly if an artifact is missing or a column is renamed, so a
stale deck cannot be built silently. `PRESENTATION_TIMING.md`,
`PRESENTATION_SOURCE_AUDIT.md` and `PRESENTATION_CLAIM_MATRIX.csv` are generated
from `deck_manifest.json` and must not be hand-edited.
