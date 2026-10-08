# Phase 0H Sec. 4/5 — Standards applicability audit

## 1. What this section is for

Phase 0G could not retrieve any standard and therefore rejected the whole class on reasoning
alone. Phase 0H has outbound network access, so the question is reopened properly: **what do
the package-warpage standards actually govern, and can any number in them legitimately become
a design constraint for a mounted DVPD system at steady-state operating temperature?**

The four categories that must never be mixed (Sec. 4):

| # | category | what it governs | may it become a design constraint? |
|---|---|---|---|
| 1 | **Manufacturing / solderability limit** | package or board shape during reflow, so joints form | **No**, not directly. It bounds assembly yield, not operating life. |
| 2 | **Component qualification test** | pass/fail after an accelerated stress (thermal cycling, shock) | **No**, not directly. It is an acceptance protocol, not a field allowable. |
| 3 | **Material failure criterion** | a constitutive threshold (plastic strain, fracture energy) | **Only with a calibrated model** that computes the same quantity. |
| 4 | **Operational design allowable** | a threshold usable directly in the steady-state mounted design problem | **Yes** — this is the only category that can enter G2. |

## 2. What was retrievable, and what was not

| source | retrieval | evidence used |
|---|---|---|
| **IPC-9641**, *High Temperature Printed Board Flatness Guideline* | **PRIMARY — front matter, Purpose, Scope and Definitions retrieved in full** | direct quotation below |
| JESD22-B112C, JESD22-B108B, JEP95, SPP-024 | **NOT RETRIEVABLE.** jedec.org returns HTTP 403 to this environment, as does the ANSI webstore. | characterised from **peer-reviewed open-access secondary literature that applies them**, clearly labelled as secondary |
| JEITA ED-7306 | not retrievable (HTTP 404 on the publisher's catalogue) | none — excluded |

No standard is cited here from memory. Where a standard could not be read, what is recorded
is *another paper's description of it*, and the description is attributed to that paper.

## 3. IPC-9641 — read directly, and inapplicable

IPC-9641 §1.1 (Introduction), verbatim:

> "During the surface mount assembly process of an electronic package to a printed board
> through a reflow temperature profile, the flatness behavior of both the package and printed
> board are critical for the integrity of solder joint formation and reliability. ... controlling
> the printed board flatness is equally important for preventing subsequent assembly-related
> issues, including **open or bridging joints**"

§1.2 (Scope), verbatim:

> "The purpose of this **test method** is to measure the shape and relative change in shape of a
> local area of interest (e.g., flip-chip ball grid array (FCBGA) land area) **of printed
> boards** through a range of temperatures typical during surface mount and through-hole builds
> of integrated circuit packages to printed boards."

§1.3.5 defines the metric it uses:

> "**Dynamic Warpage** The full-field difference in flatness of a component (package, printed
> board, etc.) between **initial ambient and reflow temperature**"

**Verdict: CATEGORY 1, and not even a limit.** It is a measurement method for *printed board*
flatness through a *reflow* profile, aimed at *solder joint formation defects*. It contains no
allowable, governs the board rather than the package, and references its metric to reflow
temperature. It cannot supply a design constraint for this project.

## 4. JEDEC family — characterised from open secondary literature

The following is how a 2025 peer-reviewed open-access study of a 21 × 21 mm lidded flip-chip
CSP describes the applicable standards. **This is a secondary description; the standards
themselves could not be read.**

> "industry standards have been established to define acceptable limits for **coplanarity at
> room temperature** and **warpage at high temperature**. **JESD22-B108B** provides a
> coplanarity testing method at room temperature by measuring the distance of the **apex of
> solder balls relative to a reference plane**. The recommended flatness requirements for
> packages with body sizes equal or less than 21 mm are presented in table I of **JEP95**. For
> warpage during high-temperature reflow process, **JESD22-B112C** provides detailed
> **measurement methods**, including thermal shadow moiré, 3D digital image correlation and
> laser reflection method, etc. For package sizes greater than 15 mm, the recommended warpage
> limit values can be found in table II of **SPP-024**."

and it reports the numbers that follow for its own 21 × 21 mm body size:

> "the maximum allowable coplanarity at room temperature is **80 µm**, while the acceptable
> warpage range at reflow temperature for this package body size and ball pitch is between
> **−120 µm to 170 µm**."

Three things follow, and only the third is about magnitude:

1. **JESD22-B112C is a measurement method, not an allowable.** The allowables live in **JEP95**
   (room-temperature coplanarity) and **SPP-024** (reflow warpage). Naming JESD22-B112C as the
   source of a limit — which Phase 0G's reasoning implicitly did — is wrong.
2. **Both allowables are CATEGORY 1.** They exist so that solder joints form correctly during
   surface-mount assembly. Their failure mechanism is opens and bridging at reflow.
3. The numbers are 80 µm at 25 °C on the **ball plane**, and −120/+170 µm at **245 °C peak
   reflow** on the package.

## 5. The admissibility test applied (Sec. 15)

Against this project's quantity — **incremental operational P-V warpage of a die surface, in a
mounted assembly, at steady-state 84 °C, referenced to a 25 °C stress-free state**:

| condition | JEP95 / SPP-024 allowable | this project | match? |
|---|---|---|---|
| package state | package **as supplied**, not yet attached | **mounted** on a board, in service | **NO** |
| temperature / load state | 25 °C static, or 245 °C peak reflow transient | steady-state 84 °C operation | **NO** |
| failure mechanism | solder joint **formation** defects — opens, bridging, yield | operational deformation and long-term reliability | **NO** |
| metric definition | ball-plane coplanarity, or full-field package warpage referenced ambient→reflow | die-surface P-V referenced to a 25 °C stress-free state | **NO** |
| geometry / interconnect scale | 21 mm body, BGA | 22.36 mm die, BGA on 0.8 mm pitch | **YES** |
| source-backed value | yes (via secondary description) | — | yes |

**One of six conditions is satisfied — the one that matters least.** The package state, the
temperature state, the failure mechanism and the metric definition all differ.

**REJECTED as a design constraint.** These are category-1 manufacturing limits and cannot be
promoted to category-4 operational design allowables.

## 6. Consequence for Sec. 18

The retrieved numbers make the Phase-0G wording worse, not better, and it is now retracted.
Phase 0G wrote that the computed range sits "one to two orders of magnitude below the
hundreds-of-micrometres band conventional for this package class". The only comparable
published values actually found are **80 µm** (room-temperature ball-plane coplanarity) and
**−120/+170 µm** (peak-reflow package warpage) — tens to low hundreds of micrometres, not
"hundreds", and in any case measuring a different quantity in a different state.

The supportable statement is therefore exactly, and only:

> Simulated mounted **incremental operational** warpage stays **below 40 µm** over the tested
> envelope. No admissible operational allowable exists for comparison, so whether that value is
> safe, marginal or constraining is **UNKNOWN**.

## 7. What would close this gap

A category-4 allowable would have to be defined for the **operational** state: a maximum
permitted die-surface or package deformation, or a maximum interconnect strain, at operating
temperature for a mounted assembly, tied to a service-life requirement. Nothing in the
standards family surveyed here does that — by design, because operating-life limits are set by
qualification testing on a specific product (category 2), not by a package-outline document.

This pushes the search towards **local interconnect reliability metrics with calibrated
life models** (Sec. 6, 8), which are category 3 and can become category 4 given a calibration.

## Sources

1. **IPC-9641**, *High Temperature Printed Board Flatness Guideline*, IPC Printed Board
   Coplanarity Subcommittee (6-11), June 2013. Front matter, §1.1, §1.2, §1.3.5 retrieved
   directly from `https://www.ipc.org/TOC/IPC-9641.pdf`. **PRIMARY.**
2. *Warpage Analysis of Lidded Flip Chip CSP: Impact of Material Properties and Dimensional
   Variations*, IMAPSource, 2025, open access, `https://imapsource.org/article/147117.pdf`.
   Used only for its description of JESD22-B108B, JEP95, JESD22-B112C and SPP-024 and for the
   allowable values it quotes for a 21 × 21 mm body. **SECONDARY.**
3. *Methodology for Predicting BGA Warpage by Incorporating Metal Layer Design*, IMAPSource,
   2014, open access, `https://imapsource.org/article/57023.pdf`. Confirms JESD22-B112 is
   applied as a measurement specification ("heaters as per JEDEC Spec JESD22B112").
   **SECONDARY.**
4. Non-retrieval evidence: `jedec.org` and `webstore.ansi.org` both return HTTP 403 to this
   environment; the JEITA catalogue entry returns HTTP 404. Recorded 2026-09-10.
