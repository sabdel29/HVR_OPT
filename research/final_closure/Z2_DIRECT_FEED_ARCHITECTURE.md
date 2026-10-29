# Z2 direct-feed architecture — frozen before any new result

Machine-readable twin: `z2_direct_feed_architecture.json` (same content; the pipeline reads
the JSON). This file was written and committed **before** any electrical, thermal,
mechanical or local result of the corrected Z2 existed. Nothing below is tuned to a result.

## 1. What changes, and why

The previous primary Z2 routed its 48 V input through peripheral package BGA balls and a
package-level 48 V RDL sheet before reaching the backside regulator (HVR). That is not the
Z2 this paper means. The intended Z2 is a **direct-fed backside HVR inside the PCB cutout**:

- The 48 V input reaches the regulator through a dedicated external connection on the
  cutout side.
- Conversion happens below the substrate.
- Only the 1 V supply and return, at about 1 kA, cross the substrate.

| | **Z1 (embedded)** | **Z2 (direct-fed backside, primary)** |
|---|---|---|
| where 48 V enters | PCB → 48 V BGA field → package 48 V RDL sheet → 48 V TSV field → HVR | external 48 V connection on the cutout side → HVR input terminals |
| what crosses the substrate | **48 V** at about 24 A (HV-S0 average), before conversion | **1 V** at about 1 kA, after conversion |
| where conversion happens | above the substrate, between substrate and die | below the substrate, inside the PCB cutout |
| where 1 V begins | HVR output RDL → microbumps → die | HVR output RDL → explicit VR-to-substrate attach → 1 V TSVs → top RDL → microbumps → die |

The superseded construction is kept only as **`Z2_BGA_FED_CONTROL`** (code key `Z2BF`). It
is a controlled experiment and an appendix comparison, never the primary Z2.

## 2. Power path, platform to die (Z2 primary, code key `Z2`, variant `Z2_DIRECT_FEED`)

| # | element | rail | owner in the model |
|---:|---|---|---|
| 0 | 48 V platform / motherboard supply | 48 V | outside every boundary |
| 1 | dedicated external / backside power connection, reached through the PCB cutout | 48 V | **`R_Z2_direct_feed_loop`**, a swept parameter (§5) |
| 2 | backside-HVR 48 V input terminals: the VIN pad on the high-side RDL of each cell | 48 V | **package-internal boundary** |
| 3 | high-ratio / switching stage: the high-side GaN | 48 V → V_mid | `P_conv_hs` |
| 4 | flying-capacitor stage | SC | `P_conv_cap_esr` (+ flying-cap loop in `P_intraVR_metal`) |
| 5 | buck / low-side switching stage | SW | `P_conv_ls` |
| 6 | inductor + Cout | LV | `P_conv_inductor_dcr`, `P_conv_cap_esr` |
| 7 | internal HVR metal and vertical HVR vias | mixed | `P_intraVR_metal`, `P_intraVR_vertical` |
| 8 | 1 V HVR output plane / attach RDL (`conv_0_land_side_attach_rdl`) | 1 V | `P_intraVR_metal` (R2 output plane) |
| 9 | **explicit VR-to-substrate attachment** (§4) | 1 V | **`P_VR_attach_VDD`, `P_VR_attach_GND`** |
| 10 | substrate 1 V VDD TSV field (1444 vias per cell, VDD/GND checkerboard) | 1 V | `P_TSV_VDD` |
| 11 | substrate GND TSV field | 1 V | `P_TSV_GND` |
| 12 | top 1 V RDL (`z2_top_rdl`) | 1 V | `P_pkg_RDL_LV_*`, structurally absent (pads sit over the tile); alternative quantified |
| 13 | microbumps / die-interface pads | 1 V | `P_pad_VDD`, `P_pad_GND` |
| 14 | compute die (load) | 1 V | 1000 W |

**Return path.** Compute-die GND → die/package ground interface (`P_pad_GND`) → top ground
RDL → substrate GND TSV field (`P_TSV_GND`) → VR attach GND (`P_VR_attach_GND`) →
backside-HVR ground → direct backside input-return connection (inside `R_Z2_direct_feed_loop`)
→ platform ground.

**Removed from the primary Z2 ledger:** `P_pkg_RDL_HV_supply`, `P_pkg_RDL_HV_return`,
`P_BGA_supply`, `P_BGA_return`. They belong only to `Z2_BGA_FED_CONTROL`. A regression test
refuses any of these terms in a `Z2_DIRECT_FEED` ledger.

**Energy-flow order, not a series circuit.** Read from the deepest tier upward, the Z2 stack is:

direct 48 V input → high-side GaN → interlayer RDL → flying capacitors → interlayer RDL →
low-side GaN → interlayer RDL → inductors + Cout → 1 V output/attach RDL → Cu-pillar attach →
substrate (VDD + GND TSVs) → top 1 V RDL → die interface → die.

This is the order energy flows through the tiers. It is not an electrical series chain: the
converter has switch-node, flying-capacitor, ground and phase connections between tiers.

## 3. Z1 power path (unchanged construction)

48 V platform → PCB 48 V distribution → **BGA 48 V power field**: 54 supply + 54 return balls,
the matched count. Then → package 48 V RDL sheet (voltage-fed refined FV network) → **48 V
TSV field** (1444 vias per cell) → bottom-substrate RDL, which is the high-side landing →
converter tiers → output RDL → microbumps (`interface`) → die. Return is symmetric. Z1's
converter is built up on the substrate top, so it has no solder attach between converter
and substrate. Its 1 kA interface is the converter-to-die microbump row, which is explicit.

## 4. The explicit VR-to-substrate attachment (Z2)

**Technology: Cu pillar + SnAg solder cap + underfill, as a VDD/GND checkerboard over each
cell footprint.** It carries only the 1 V supply and return. The 48 V input does not cross
it (ARM US20260059645A1 [0040], quoted below).

| quantity | nominal | bounds (class-B) | basis | class |
|---|---|---|---|---|
| joint height (substrate pad to HVR attach RDL) | 30 µm | 20 / 40 µm | framework allowance "cell-to-substrate attach solder + underfill 30 µm" (`research/PCB_THICKNESS_Z2_AUDIT.md`), already reserved in the clearance budget; 40 µm Sn bumps on Cu posts (Na et al. 2022) | BOUNDED / CLOSE_ANALOG |
| pillar diameter / pitch | 15 µm / 30 µm | 30 µm / 80 µm (Na et al. 2022: 30 µm bumps, 50 µm space) | Au et al., ECTC 2016, 10.1109/ECTC.2016.127: "30μm pitch micro Cu pillar bump (15μm diameter)" | CLOSE_ANALOG |
| solder-cap height | 16 µm | — | Au et al. 2016: "sufficient solder cap volume (16mm height)" (the abstract's typo for µm) | CLOSE_ANALOG |
| Cu pillar height | 14 µm (= 30 − 16) | — | derived from the allowance and the cap | DERIVED |
| all-solder alternative | — | pure-Sn microbump of the same envelope | Na et al. 2022, 10.3390/electronics12010144 | CLOSE_ANALOG |
| underfill | framework `underfill_homog` (k 0.6 W/mK; E 8 GPa; CTE 30 ppm/K, as the interface microbump layer) | declared stress bounds | same matrix as the existing microbump row | DERIVED / ASSUMPTION |
| bumps per rail per cell | ⌊s/p⌋² / 2 = 78² / 2 = 3042 | from the bounding pitch | checkerboard over the 2.3685 mm cell | DERIVED |

- **Thermal card.** The pillar column is Cu and solder in series. The array is homogenised by
  the method Phase 0M-R validated for the existing microbump row: Voigt through the
  thickness and Maxwell-Garnett in plane, each within about 0.6 % of an explicit RVE.
- **Mechanical card.** Underfill-dominated, the same convention as the existing `microbump`
  card. The column-stiffened (Voigt) card is a class-B bound.
- **Electrical.** Per bump, R = ρ_Cu·h_Cu/A + ρ_solder·h_cap/A, at the attach temperature,
  using the framework's ρ_Cu(T) and ρ_solder(T). The ρ_solder card stands in for SnAg
  (CLOSE_ANALOG). Contact and IMC resistance are not resolved; the all-solder bound brackets them.
- **No reliability limit is transferred.** At nominal, each bump carries about 6.7 mA
  (20.4 A / 3042). No current-density allowable from these papers is claimed.

In the FE stack the attach is a new tier, `conv_attach_vr_substrate`, 30 µm, between
`conv_0_land_side_attach_rdl` and the substrate underside (`sub_lower`). It is present
inside the 49 cells, with the out-of-cell rule of the other converter tiers.

## 5. Electrical system boundary and the direct-feed parameter

- **A. Package-internal result (the ETM ledger).** For Z2 the boundary starts at the
  backside-HVR 48 V input terminals. It includes the HVR intrinsic losses, internal HVR
  RDL/vias, output plane, VR attach, 1 V TSVs, top RDL and die-interface pads. For Z1 it
  starts at the BGA pads on the PCB and includes the 48 V BGA field, the package 48 V RDL
  and the 48 V TSVs.
- **B. Platform-inclusive result.** **`R_Z2_direct_feed_loop`** is the complete external 48 V
  supply + return loop between the platform reference node and the HVR input terminals.
  - The reference node is the board-level 48 V node common to both architectures: where
    Z1's PCB distribution meets its BGA pads. Board distribution upstream of that node is
    common to both and excluded from both.
  - It includes the per-cell distribution to the 49 input terminals and any post through
    the high-side tier.
  - **No value is assumed.** ARM US20260059645A1 names connector *types* only (pin-and-sleeve,
    bullet, banana) and no dimension or resistance. The parameter is therefore swept over
    0.01 to 100 mΩ.
  - Loss: P_feed = I_48,rms² · R_feed, with I_48 solved self-consistently, because the feed
    loss raises the input current.
  - Reported: total loss and system efficiency against R_feed, and the crossover R* where
    P_Z2 = P_Z1, per named scenario. The design requirement is stated as "for Z2 to keep its
    electrical advantage, R_Z2_direct_feed_loop < R*".
  - Heat location. The nominal ETM deposits no feed loss inside the package. A class-B
    variant deposits the feed loss at R* in the deepest converter tier.
- **48 V waveform.** HV-S0/S1/S2 remain named scenarios. For Z2 they set the external-feed RMS
  loss and the HVR's internal 48 V nets; no package 48 V network exists in Z2.

## 6. BGA: mechanical function versus 48 V power function

| field | Z1 | Z2 (direct feed) | Z2_BGA_FED_CONTROL |
|---|---|---|---|
| `BGA_MECHANICAL_FIELD`: every package-to-PCB site in the mechanical model | 1369 sites (full lattice) | **528 sites** (all outside the cutout) | 528 sites |
| `BGA_48V_POWER_FIELD`: balls carrying the HVR 48 V input | 54 supply + 54 return | **none** | 54 supply + 54 return |

- The Z2 package still attaches to the PCB through its 528 surviving sites. They carry signal
  I/O, auxiliary rails, control and ground, and provide mechanical support and heat
  conduction.
- The critical-joint search runs over the whole mechanical field. Removing the 48 V
  electrical path removes no ball.

## 7. Geometry corrections fixed in the baseline

- **DEFECT #66 resolved in the baseline.** Between the 21.36 mm cell-grid bounding box and the
  23.36 mm PCB opening there is a **1.0 mm sidewall clearance**, and it is void. The
  encapsulant fills only between the cells (F1). Nothing bonds the converter to the PCB
  sidewall. The old sidewall-filled construction survives only as the class-B variant
  `f1_sidewall_filled`. F2 (void between the cells) remains a variant.
- **Explicit attach.** As §4.
- **Unchanged.** 23.36 mm cutout; 49 cells of 2.3685 mm on a 3.1652 mm pitch; converter
  tiers per the YAML. The converter descends 1993 µm (1963 + 30) into the 2700 µm opening,
  leaving 707 µm above the PCB backside.

## 8. The controlled BGA-fed experiment

`CONTROLLED_BGA_FED_Z1_VS_Z2_EXPERIMENT`: *This controlled experiment isolates the effect of
BGA placement/cutout when both architectures are forced to use an identical package-level
48-V feed. It is not the primary Z2 construction.*

- The experiment is the matched 54-ball-per-rail package network study.
- `Z2_BGA_FED_CONTROL` is run through the same ETM, with the same corrected geometry, at
  HV-S0.

**DEFECT #67 (control only).** In the BGA-fed control the 48 V enters at the land-side
(top) RDL, but the intra-VR routing model places VIN on the high-side RDL. The control
therefore omits a roughly 1.3 mm HV vertical traverse through the inductor, low-side and
flying-capacitor tiers. For Z1 and for the direct-fed Z2 the 48 V does enter at the
high-side RDL, so the model is physical there.

## 9. Sources and how far each one goes

| source | what it supports | class |
|---|---|---|
| ARM Ltd., US20260059645A1, claims 1, 6–9, 14–15; [0038], [0040], [0042] | VR on the substrate side opposite the die, at least partly inside a PCB hole (claim 1). A separate wire/power connector feeds the VR (claims 7, 14), at ≥ 1 kW (claim 8), with ≥ 10× voltage reduction (claims 9, 15). External connections "provided by a separate wire 324 rather than via the printed circuit board 314 and substrate 304 … to provide external input power and ground signals" ([0038]). With power through external connectors, the VR-to-substrate bumps can be "dedicated to providing power to integrated circuit 302 … no longer need to carry a high voltage power signal" ([0040]). Bumps "may comprise … metal pillars, such as solder-coated copper pillars" ([0042]). | **DIRECT** architectural precedent; no dimension, no performance, no qualification |
| ARM US20260059645A1 [0047] | the substrate may instead conduct power to the VR (the BGA-fed alternative) | DIRECT, for the control |
| Google LLC, US20210249384A1 (family US20230402430A1, US20250006706A1, US20250349802A1) | IVR on the backside of the die. Input power from the PCB through the package substrate RDL and through-mold/through-dielectric vias ([0034]–[0037]); output through a backside RDL into TSVs ([0038]). Input "at a higher voltage level and lower current level" ([0037]). | **CLOSE_ANALOG** for the 1 V output path (backside RDL → TSVs) and the high-voltage input principle. **Not** a direct-feed precedent: its input goes through the package. |
| Au et al., ECTC 2016, 10.1109/ECTC.2016.127 | 15 µm Cu pillars at 30 µm pitch with a 16 µm solder cap, TCB + NCP, on organic substrate | CLOSE_ANALOG interconnect precedent |
| Na et al., Electronics 12(1):144, 2022, 10.3390/electronics12010144 | 30 µm pure-Sn bumps, 40 µm tall, 50 µm space, on Cu post/Ni | CLOSE_ANALOG (bounds) |
| Lee et al., IEEE TCPMT 2017, 10.1109/TCPMT.2016.2641040 | Cu pillar/Sn-Ag microbumps with NCF for 3-D TSV interconnection | CONTEXT_ONLY (construction) |
| Dai et al., ICEPT 2018, 10.1109/ICEPT.2018.8480482 | 30 µm-pitch microbump material systems; single-bump Kelvin resistance measured (value not available to us) | CONTEXT_ONLY |
| Xu et al., Mater. Sci. Semicond. Process. 2026, 10.1016/j.mssp.2026.110744 | Cu-pillar bump review | CONTEXT_ONLY (abstract not retrievable) |
