# Z2 Backside/Land-Side VR Research Handoff

Prepared 2026-10-22 for the HVR_OPT / ETM-DVPD architecture audit.

## Bottom line

The strongest source-backed physical direction for Z2 is **not** an undefined full-area converter slab and not a generic “PMIC in a cavity.” It is a **land-side/backside distributed VR assembly attached to the underside of the package substrate and extending into a PCB/motherboard cutout, with BGA/LGA/metal-pillar board attachment around the cutout**.

This construction has multiple independent precedents:

1. Peer-reviewed IEEE packaging work explicitly studies **bottom-side package VR placement** with BGA power pins feeding the VR and low-voltage current flowing vertically from package bottom to the IC.
2. Advanced-package PDN research explicitly studies **backside-of-package VRM** configurations.
3. The 2026 DVPD framework explicitly states that VR components may be vertically stacked on the **backside of a substrate and interconnected through TSVs**.
4. Recent ARM and Intel patents explicitly show VR assemblies/chiplets on the package land side extending into a **PCB/motherboard cutout**, while the package remains attached through BGA/LGA/pillars around the cutout.
5. Ferric currently markets **land-side package attach** IVRs and a 1.2-mm-thick dual-sided IVR, establishing commercial feasibility of land-side conversion as a packaging direction (not as a direct geometry match to the discrete 48-to-1 HVR).

## Critical correction to audit before implementing Z2

The current Phase-0N-R document calls the corrected backside cell 1258 um tall. That 1258 um is the `embedded_cell` quantity (LS + inductor + MLCC + two RDLs) and **excludes the 685 um high-side EPC2014C**.

If Z2 means all HVR components are stacked on the substrate backside using the same four-tier physical component stack, the corrected serial component height is approximately:

- EPC2014C high side = 685 um
- EPC2057 low side = 638 um
- inductor = 500 um
- MLCC = 100 um
- 3 x RDL = 30 um
- total = **1953 um**

Therefore Claude must first determine where the high-side device is in Z2. Do not use 1258 um as the complete Z2 backside protrusion unless the high-side device is explicitly placed elsewhere.

With the current 300-um BGA and assumed 1.6-mm PCB:

- package underside to PCB bottom through a through-board cutout ~= 300 + 1600 = 1900 um
- a 1953-um serial VR stack would extend about **53 um beyond the PCB backside**, before additional clearances/interfaces

This makes a through-board cutout surprisingly plausible dimensionally, but this is only a first-order height closure. The true candidate must include clearances, solder/underfill, thermal interface, package-side attachment, board cutout sidewall clearance, and explicit BGA placement.

## Recommended Z2 candidate to test

Name it something like:

**Z2-CUTOUT: land-side distributed VR cells with motherboard/PCB cutout**

Do NOT call it a PMIC unless the discrete HVR is redesigned into an actual packaged PMIC/module.

Conceptual cross-section:

```
       cold plate
=======================
       compute die
=======================
 microbumps / top RDL
-----------------------
  0.30-mm power substrate
  explicit 1-V supply + return TSV fields
=======================
    distributed HVR cells
  HS / Cf / LS / L / Co
  (actual component stack)
       |         |
       | PCB CUTOUT |
   o o |           | o o     <- peripheral BGA / LGA / pillars
=======|===========|=======   <- motherboard/PCB
       |           |
       | VR may    |
       | extend    |
       | partly    |
       | through   |
       | cutout    |
```

Electrical path:

PCB 48 V / GND -> peripheral BGA power/ground balls -> package land-side HV RDL/plane -> local HVR cell input -> conversion -> local 1 V/GND output -> explicit TSV supply/return field through 0.30-mm substrate -> microbump/RDL -> corresponding die POL.

This preserves the DVPD principle: distribute high-voltage/low-current power laterally, then convert locally so the low-voltage/high-current path is predominantly vertical and short.

## Must-read sources

### 1. Xu et al., IEEE TCPMT 2019 — direct peer-reviewed bottom-placement precedent

Kan Xu, Boris Vaisband, Gregory Sizikov, Xin Li, Eby G. Friedman, “Power Noise and Near-Field EMI of High-Current System-in-Package With VR Top and Bottom Placements,” IEEE Transactions on Components, Packaging and Manufacturing Technology, vol. 9, no. 4, pp. 712-718, 2019.

DOI: https://doi.org/10.1109/TCPMT.2019.2903285
Open PDF: https://www.hajim.rochester.edu/ece/sites/friedman/papers/CPMT_19.pdf

Inspect especially Fig. 2 and Sections II-III.

What it establishes:
- bottom-side package VR is a peer-reviewed package topology;
- BGA power pins feed the high-voltage network to the bottom VR;
- the low-voltage high-current path goes vertically from bottom VR to the IC;
- bottom VR placement changes BGA pinout and competes for bottom-side package area;
- package contains 16 metal layers for the bottom-placement example;
- package vertical VR-to-IC distance is about 2 mm.

What it does NOT establish:
- clearance for a ~2-mm-tall discrete HVR between package and motherboard;
- a PCB cutout;
- our exact 48-to-1 converter.

### 2. Hossen et al., 2020 — backside-of-package VRM precedent

Md Obaidul Hossen et al., “Design Space Exploration of Power Delivery For Advanced Packaging Technologies,” arXiv:2008.03124.

ArXiv: https://arxiv.org/abs/2008.03124
PDF: https://arxiv.org/pdf/2008.03124
ArXiv DOI: https://doi.org/10.48550/arXiv.2008.03124

Inspect the benchmark configurations including backside-of-package VRM and 3D chip-on-VRM.

What it establishes:
- backside-of-package VRM is an analyzed advanced-packaging architecture;
- package/through-package interconnect and board solder-bump path are part of the PDN model.

### 3. Krishnakumar & Partin-Vaisband, SOCC 2023 — VPD architecture taxonomy / Z1

“Vertical Power Delivery for Emerging Packaging and Integration Platforms — Power Conversion and Distribution.”

DOI: https://doi.org/10.1109/SOCC58585.2023.10256973
ArXiv: https://arxiv.org/abs/2309.10141
PDF: https://arxiv.org/pdf/2309.10141

Use for Z1 architecture family and VPD taxonomy. It does not itself close the Z2 land-side/board interface.

### 4. Krishnakumar et al., IEEE TCPMT 2026 — DVPD and backside statement

“A Comprehensive Design Framework for Vertical Power Delivery in High-Performance Computing.”

DOI: https://doi.org/10.1109/TCPMT.2026.3724907
ArXiv: https://arxiv.org/abs/2606.28837
PDF: https://arxiv.org/pdf/2606.28837

Key sentence to locate: when fabricated as individual chiplets, VR components can be vertically stacked on the backside of a substrate and interconnected through TSVs.

Use this as the closest direct conceptual source for the current Z2 idea. It does NOT specify BGA/cutout dimensions.

### 5. ARM 2026 patent — strongest exact PCB-cutout construction

ARM Ltd., US20260059645A1, “Vertical integrated voltage regulator with circuit board cutout.”

Google Patents: https://patents.google.com/patent/US20260059645A1/en

Inspect Figs. 1-4 and the associated description.

What it establishes very explicitly:
- die on first side of package substrate;
- VR assembly on the opposite side;
- VR includes inductors + regulation circuits and can include additional layers/capacitors;
- PCB has a hole/cutout receiving the VR at least partially;
- package/substrate is connected to PCB by BGA, LGA, pillars, or similar connections;
- multiple VR assemblies can be accommodated in a repeated pattern;
- high-power variants can use external power/ground connections;
- patent explicitly discusses hundreds of watts / kilowatt-or-more variants and says the cutout enables VR assemblies larger than the normal package-to-board gap.

This is not peer-reviewed scientific evidence. Use it as **industry construction precedent**.

### 6. Intel 2025 patent — package interposer + VR chiplet + motherboard cutout

Intel Corp., US20250233088A1, “Vertical power delivery in space-constrained system-on-package.”

Google Patents: https://patents.google.com/patent/US20250233088A1/en

Inspect Fig. 2A/2B and Figs. 3-4.

What it establishes:
- VR chiplet on bottom side of package interposer;
- load die on top side;
- motherboard attachment by BGA;
- motherboard regions surround a cutout that provides room for the land-side VR chiplet;
- alternative embodiment allows no cutout and VR sits between board and package;
- multiple/ganged VR chiplets and package-embedded inductors are contemplated;
- intended application includes high-performance / AI SoP with hundreds of amperes and multi-kW capability.

Again, patent = industry architecture precedent, not peer-reviewed validation.

### 7. Ferric 2019 open paper — compact package VR technology

Joseph Meyer, Reza Moghimi, Noah Sturcken, “Package Voltage Regulators: The Answer for Power Management Challenges,” IMAPS 2019.

DOI: https://doi.org/10.4071/2380-4505-2019.1.000438
Open PDF: https://imapsource.org/article/56585.pdf

Important points:
- power conversion can be moved into the package;
- integrated thin-film inductors allow compact PVRs;
- paper reports PVR thicknesses below 0.2 mm and controllable thinned-die heights around 0.2-0.8 mm for its technology.

Not directly comparable to our discrete GaN/passive stack, but useful for alternative future Z2 implementations.

### 8. Ferric current integration/product pages — commercial land-side feasibility

Integration: https://www.ferric.com/integration
Products: https://www.ferric.com/products

Current site explicitly offers “Land Side Package Attach.” Fe1767 is advertised as a dual-sided IVR supporting land-side integration, ~8.9 x 5.6 mm, ~1.2 mm thick, 145 A TDC.

This is vendor information, not peer-reviewed evidence. It is useful to show that land-side package attach is commercially pursued and to benchmark feasible IVR thicknesses.

### 9. 2026 review — broad VPD survey

M. Swaminathan et al., “Integrated Vertical Power Delivery – Review & Challenges,” IEEE TCPMT, 2026.

DOI: https://doi.org/10.1109/TCPMT.2026.3716987
Author manuscript page: https://www.researchgate.net/publication/410805983_Integrated_Vertical_Power_Delivery_-_Review_Challenges

Use as high-level survey/taxonomy and to identify further architecture references.

### 10. 2023 SiP review — survey that summarizes top/bottom VR placement

H. Wang et al., “A Review of System-in-Package Technologies: Application and Reliability of Advanced Packaging,” Micromachines 14(6), 1149, 2023.

DOI: https://doi.org/10.3390/mi14061149
Open article: https://www.mdpi.com/2072-666X/14/6/1149
PDF: https://www.mdpi.com/2072-666X/14/6/1149/pdf?version=1685366895

The review reproduces/discusses top- versus bottom-package VR topology and is useful context, though the original Xu 2019 paper should be cited for the primary result.

## Evidence hierarchy for the paper/thesis

Use wording according to source type:

- Peer-reviewed IEEE / journal paper: “published architecture/model demonstrates/studies…”
- ArXiv preprint: “published preprint analyzes/proposes…”
- Patent: “industry patent discloses a construction in which…”; never say experimentally demonstrated unless it is.
- Vendor page: “commercial vendor offers/advertises…”; not independent validation.

## Proposed modeling checks for Z2-CUTOUT

1. Verify full component height including the HS device. Audit whether Z2 currently omits HS geometry.
2. Lay out 49 cells laterally (likely 7x7) rather than a full-area slab.
3. Compute exact VR-grid bounding box from real component/tile coordinates; do not assume square tiles unless code confirms it.
4. Choose cutout size = VR grid + sidewall/assembly clearance.
5. Place BGA outside the cutout and compute actual available ball count at sourced 0.8-mm pitch.
6. Allocate 48-V supply and ground balls explicitly; allocate signal balls separately if relevant.
7. Model board as an annulus/frame around the cutout, not a continuous full-area FR-4 slab below the VR.
8. Model BGA balls only where board exists, not beneath the cutout.
9. Model explicit 1-V and return TSV regions through the 0.30-mm substrate.
10. Model package land-side RDL that brings 48 V/GND from peripheral BGA to each distributed VR cell.
11. Add cutout-sidewall clearance and any underfill/encapsulant around cells as explicit sensitivity parameters.
12. Consider backside VR cooling boundary: adiabatic/open-air, heat sink through board cutout, or explicit bottom thermal solution. ARM patent explicitly allows a VR heat sink through the cutout.
13. Run mechanical assembly with a board that has a central cutout; this is structurally very different from the frozen full-board model and will change warpage/joint loading.
14. Do not compare local solder response until the BGA location used for the local joint corresponds to a real remaining BGA ball near the cutout/periphery.
15. Re-run electrical -> thermal -> global thermoelastic -> local solder after closure.

## Rough geometric sanity check (must be re-derived from code)

49 cells at 5.61 mm^2 each occupy 274.89 mm^2 total. If they were ideal square cells in a tight 7x7 grid, each side would be sqrt(5.61) ~= 2.37 mm, and the grid would be about 16.6 mm square. A ~18-20 mm central cutout under a 30-mm package would leave roughly 5-6 mm of package land around the opening, potentially enough for multiple peripheral BGA rows at 0.8-mm pitch. This is only a sanity check; use actual cell geometry and routing keep-outs from the repository.

## Recommended thesis terminology

Z1 candidate: “substrate/interposer-embedded distributed VR” (only after model matches the selected source-backed stack).

Z2 candidate: **“land-side/backside distributed VR assembly with PCB/motherboard cutout”**.

Do not call Z2 “PMIC in a cavity.” The current HVR is 11 discrete components per cell, not a PMIC. If the design is later re-packaged into a single VR chiplet/module, that becomes a distinct physical architecture and should be modeled as such.
