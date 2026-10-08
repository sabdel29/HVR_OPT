# BC-B Support Model — Calibration and Sensitivity Envelope

Phase 0B's BC-B foundation stiffness was **PROVISIONAL and uncalibrated**, and Phase 0B
showed the support model changes the mechanics qualitatively. The Phase-0C brief requires
searching for real package/BGA data before inventing anything.

## 1. Data search result — geometry IS available

Searching the repository and the recorded primary-source extracts turns up source-backed
BGA geometry that Phase 0B had not exploited:

| Quantity | Value | Status | Source |
|---|---:|---|---|
| BGA ball diameter | 400 µm | **SOURCE_BACKED** | June-2026 Table III |
| BGA ball height | 300 µm | **SOURCE_BACKED** | June-2026 Table III |
| BGA pitch | 800 µm | **SOURCE_BACKED** | June-2026 Table III |
| Solder E | 20 GPa | **SOURCE_BACKED** | STAMP-2.5D material table (Tin-Lead 60-40) |
| Solder ν | 0.35 | **ASSUMPTION** | STAMP-2.5D omits Poisson's ratio entirely |
| Ball barrel profile | — | **NOT AVAILABLE** | not invented; see §2 |

So a genuine unit-cell calibration is possible for the *stiffness scale*, though not for the
exact ball shape.

## 2. Unit-cell calibration

An explicit equal-area-square solder column (side 354.5 µm, height 300 µm, cell pitch
800 µm, area fraction 0.1963) was solved with a bonded base and a rigid loaded pad:

| Quantity | FEA | closed form (E·f/h or G·f/h) |
|---|---:|---:|
| normal foundation stiffness k_z | **13 855 N/mm³** | 13 090 N/mm³ |
| shear foundation stiffness k_xy | 4 763 N/mm³ | 4 848 N/mm³ |

**This is an upper bound, and is labelled as such.** A real solder ball is barrel-shaped
with reduced pad contact and bends rather than shears; both make it substantially more
compliant than a straight column. No barrel profile was invented — instead the envelope
extends *downward* from this defensible bound.

Phase 0B's provisional value was k_z = 1000 N/mm³, i.e. ~14× more compliant than the column
bound. It sits inside the envelope below, so Phase-0B's BC-B was not unreasonable — merely
unjustified.

## 3. Sensitivity envelope

BC-B is implemented as a support layer of thickness t with k_z ≈ E/t. With t set to the
source-backed 300 µm ball height:

| envelope point | E_support (MPa) | k_z (N/mm³) |
|---|---:|---:|
| E/64 very compliant | 64.9 | 216 |
| E/16 compliant | 259.8 | 866 |
| E/4 moderate | 1 039.1 | 3 464 |
| E upper-bound column | 4 156.6 | 13 855 |

## 4. Results — die warpage p-v (µm)

| envelope point | C05 | C07 | C13 | C08 | placement effect | thickness effect |
|---|---:|---:|---:|---:|---:|---:|
| E/64 very compliant | 0.4498 | 0.4537 | 0.4372 | 0.4205 | +0.87 % | +6.5 % |
| E/16 compliant | 0.4008 | 0.4857 | 0.4074 | 0.4311 | +21.19 % | **−7.6 % (order flips)** |
| E/4 moderate | 0.3678 | 0.4373 | 0.3663 | 0.3539 | +18.91 % | +3.8 % |
| E upper-bound column | 0.3537 | 0.4024 | 0.3551 | 0.2913 | +13.77 % | +17.6 % |
| **BC-A (free warpage)** | **7.7720** | **12.4808** | **7.7739** | **3.3415** | **+60.6 %** | **+57.0 %** |

## 5. Interpretation — read this carefully

**Absolute magnitude is BC-dominated.** Restraining the board suppresses global bowing by
roughly **20×** (7.8 µm → 0.35–0.45 µm). Everything else follows from that.

**The apparent thickness "order flip" at E/16 is not a resolved physical reversal.** The
C05-vs-C08 difference there is 0.030 µm on values of ~0.40 µm. Mesh uncertainty on die
warpage is 0.50 %, which under BC-A is 0.04 µm — comparable to the entire BC-B difference
being measured. Under BC-B the architecture differences sit **at or below the numerical
floor of the model**, so the correct statement is *not resolvable*, not *reversed*.

**Crucially, this caveat is not specific to the thickness lever.** The generic placement
effect degrades in exactly the same way, from 60.6 % under BC-A to 0.87–21.2 % across the
envelope. Both the DVPD-specific lever and the already-accepted generic one are BC-A
phenomena. The support model does not discriminate between them; it suppresses both.

**Ordering, where resolvable:**

| effect | ordering preserved across the envelope? |
|---|---|
| placement (C07 > C05) | **yes, all 4 points** (magnitude 0.87 – 21.2 %) |
| thickness (C08 < C05) | 3 of 4 points; flips at E/16, where the difference is at the numerical floor |

## 6. Status and what is still open

**Improved but still not closed.** The stiffness *scale* is now anchored to source-backed
geometry rather than guessed, which is a real advance over Phase 0B. What remains open:

- **Ball barrel profile** — OPEN_DECISION. A column is a stiff upper bound; the true
  compliance is lower and unknown.
- **Board compliance below the balls** — not modelled at all. A real PCB adds series
  compliance that would push the effective support toward the compliant end.
- **Shear behaviour** — the solid support layer carries shear as a continuum, whereas a real
  ball field carries much less. BC-B therefore over-restrains in-plane motion.
- **A physically defensible operating point** — the envelope brackets the answer but does not
  select within it.

**Consequence for Phase-0C conclusions.** All lever rankings in this phase are stated as
**BC-A (free-warpage) results** and are explicitly labelled as such. The finding that the
mechanical relevance of DVPD architecture depends strongly on the support condition is
itself a substantive result, and it applies equally to the generic placement effect that
Phase 0B already accepted.
