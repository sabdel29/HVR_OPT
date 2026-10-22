# Z2 land-side / cutout construction — source audit

Phase 0N-R Task I. **Every source is classified, and a patent embodiment is never
upgraded into demonstrated hardware.**

## Classification

| # | source | type | read in full? | what it establishes for Z2 | what it does NOT establish |
|---:|---|---|---|---|---|
| 1 | Xu, Vaisband, Sizikov, Li, Friedman, "Power Noise and Near-Field EMI of High-Current SiP With VR Top and Bottom Placements," IEEE TCPMT 9(4):712–718, 2019. `10.1109/TCPMT.2019.2903285` | **peer-reviewed** | **yes** | Bottom-side package VR is a studied package topology. BGA power pins connect **directly to the VRs** for the high-voltage network. The low-voltage current "is transferred vertically from the bottom to the top" of the package. Bottom placement uses **16 metal layers** vs 28 for top placement, and gives the better worst-case IR drop. | No PCB cutout. No clearance analysis for a ~2 mm discrete stack. Its VR is a 12 V→0.8 V module, not a 48→1 V discrete HVR. |
| 2 | Hossen *et al.*, "Design Space Exploration of Power Delivery For Advanced Packaging Technologies," arXiv:2008.03124 | **preprint** | partial | Backside-of-package VRM is an analysed advanced-packaging configuration; package/board PDN path is modelled. | No construction, no dimensions, no cutout. |
| 3 | Krishnakumar *et al.*, IEEE TCPMT 2026. `10.1109/TCPMT.2026.3724907` / arXiv:2606.28837 | **peer-reviewed** | **yes** | The one direct sentence: "when fabricated as individual chiplets, VR components can be vertically stacked on the **backside of a substrate** and interconnected through TSVs." Also the DVPD definition and `I_o/M` scaling. | **No dimensions, no BGA relationship, no board interface, no cutout.** |
| 4 | ARM Ltd., **US20260059645A1**, "Vertical integrated voltage regulator with circuit board cutout" | **patent** | yes (claims + description) | Die on the first substrate surface; VIVR assembly on the **opposite** surface, vertically overlapping the die. A **hole/cutout in the PCB** receives the assembly "at least partially" (claim 1). Attachment by **BGA, metal pillars (solder-coated copper, higher current), or socket** with an aligned hole. Underfill against thermal stress. **Multiple VR assemblies** in a repeatable pattern. Claim 8: power **≥ 1 kW**; claim 9: voltage reduction **≥ 10×**. FIG. 3 shows a heat sink on the inductor dissipating **through the cutout**. External high-current wiring can feed input power, "freeing substrate balls for output current." | **No dimensions whatsoever** — drawings expressly "not necessarily drawn to scale." Not hardware. Not peer-reviewed. |
| 5 | Intel Corp., **US20250233088A1**, "Vertical power delivery in space-constrained system-on-package" | **patent** | yes (to 100 k chars) | VR chiplet on the **bottom/land side of the package interposer**, interposer bottom to motherboard top, load die above. Board shown as two regions surrounding **"a cutoff region 221 … which provides room for the VR chiplet"**. BGA attachment; described as **"land side attachment"**. Multiple/ganged chiplets with current sharing. Package-embedded coax magnetic inductors. 12–48 V → 1–2 V, hundreds of amperes, **multi-kW**; lateral delivery "infeasible for systems exceeding 750 W". | **No numeric dimensions.** The cutout appears **only in the description, not in the claims**, and the document elsewhere markets solutions that "do not require custom cutouts." A **no-cutout embodiment is expressly contemplated**. Not hardware. |
| 6 | Meyer, Moghimi, Sturcken, "Package Voltage Regulators," IMAPS 2019. `10.4071/2380-4505-2019.1.000438` | **peer-reviewed (industry)** | no | Context only: conversion can move into the package; thin-film-inductor PVRs below 0.2 mm. | Not our discrete GaN/passive stack. No land-side geometry for us. |
| 7 | Ferric integration / product pages (Fe1767) | **vendor** | n/a | "Land Side Package Attach" is commercially offered; a dual-sided IVR ≈ 8.9 × 5.6 mm, ≈ 1.2 mm thick, 145 A. | Vendor marketing. Not a geometry match: 1.2 mm packaged module vs our 1.963 mm discrete stack. |
| 8 | Krishnakumar & Partin-Vaisband, SOCC 2023. `10.1109/SOCC58585.2023.10256973` / arXiv:2309.10141 | **peer-reviewed** | **yes** | Four VPD architectures A0–A3; **Z1 maps onto A2**. | **None of A0–A3 is a land-side/below-substrate construction**, so it does not support Z2. |
| 9 | Swaminathan *et al.*, "Integrated VPD – Review & Challenges," IEEE TCPMT 2026. `10.1109/TCPMT.2026.3716987` | **peer-reviewed review** | no | — | Not reachable in full; no claim drawn from it. |
| 10 | Wang *et al.*, "A Review of System-in-Package Technologies," Micromachines 14(6):1149, 2023 | **peer-reviewed review** | partial | Secondary discussion of top/bottom VR placement. | Cite Xu 2019 for the primary result, not this. |

## What the evidence supports, and at what strength

| element of Z2-CUTOUT | strongest support | strength |
|---|---|---|
| VR on the land side of the package substrate, under the die | Xu 2019 (peer-reviewed) + Krishnakumar 2026 (peer-reviewed) | **peer-reviewed** |
| BGA power pins feeding the high-voltage network to that VR | Xu 2019 | **peer-reviewed** |
| Low-voltage current travelling vertically bottom→top to the IC | Xu 2019 | **peer-reviewed** |
| VR components vertically stacked on the backside, TSV-interconnected | Krishnakumar 2026 | **peer-reviewed** |
| Many distributed cells rather than one module | Krishnakumar 2026 (DVPD, `I_o/M`); ARM and Intel both show multiple assemblies | peer-reviewed + patent |
| **PCB through-cutout receiving the land-side assembly** | ARM US20260059645A1 claim 1; Intel US20250233088A1 "cutoff region 221" | **patent only — industry construction precedent, not demonstrated hardware** |
| Attachment by BGA / pillars / socket around the cutout | ARM (explicit list) | patent only |
| Backside heat sink dissipating through the cutout | ARM FIG. 3, claims 16/19 | patent only |
| **Any dimension at all** | — | **NONE. Neither patent gives a single number.** |

## The honest limit

The cutout is **patent-precedented, not demonstrated**. No source supplies a thickness, a
cutout size, a sidewall clearance or a standoff. Every dimension in
`research/Z2_CUTOUT_GEOMETRY.md` is therefore derived from **our own** sourced component
heights and the framework's own BGA/PCB values, not from the patents. The patents justify
the *topology*; they do not validate the *numbers*.

**Terminology.** The construction is a **land-side / backside distributed VR assembly with
a PCB through-cutout**. It is **not** a "PMIC in a cavity": there is no cavity in the
package substrate, and our converter is 11 discrete components per cell, not a packaged
power-management IC. That rejection from Phase 0N stands.
