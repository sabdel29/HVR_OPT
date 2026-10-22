# Z2-CUTOUT — BGA capacity, power and return

Phase 0N-R Task D.

## 1. The path

```
PCB 48 V / GND
  -> peripheral BGA power + ground balls (around the cutout)
  -> land-side HV RDL / plane on the package substrate underside
  -> each local HVR cell input (3 x HS EPC2014C)
  -> conversion in the cell (two switching phases, K = 3 branches)
  -> local 1 V / GND at the cell's top RDL
  -> explicit supply + return TSV field through the 0.30 mm substrate
  -> top RDL / microbumps
  -> die POL
```

Peer-reviewed support for the first and third legs: Xu 2019 connects "the BGA power pins
directly to the VRs" for the high-voltage network and states the low-voltage current "is
transferred vertically from the bottom to the top" of the package.

## 2. BGA capacity after the cutout

The 48 V input is the **only** rail on the BGA. The 1 V output never touches it — it rises
through the substrate TSVs. That is the whole point of the architecture, and it is what
makes the cutout affordable.

| | value |
|---|---:|
| system 48 V input current | **23.43 A** |
| ball cross-section (400 µm dia.) | 0.1257 mm² |
| per ball at `J_design` = 1 × 10⁸ A/m² (framework provisioning) | 12.57 A |
| balls needed for 48 V at `J_design` | **2** |
| balls needed for 48 V at 1.5 A/ball (conservative electromigration-style bound) | **16** |
| with an equal return allocation, conservative | **32** |
| sites remaining at 1.0 mm sidewall clearance | 528 |
| **utilisation** | **6.1 %** |

**BGA capacity is not a constraint.** Even on the conservative bound and after removing
841 of 1369 sites to the cutout, the power and return allocation uses about
6 % of what is left. The remainder is available for signals, additional ground
and mechanical attach.

Two caveats. The per-ball current limit is **not sourced** — `J_design` is the framework's
own design-side provisioning density and 1.5 A/ball is an engineering bound, so this is a
feasibility check, not a qualification. And ARM's patent separately contemplates external
high-current wiring to free substrate balls, which this design does not need.

## 3. Return

The present electrical model accounts return as `R_loop = 2 × R_field` — a **factor, not
geometry**. For a construction being called a physical package that is no longer adequate.

**Required for Z2-CUTOUT**, in increasing order of fidelity:

1. **Minimum (this phase):** explicit homogenised **supply** and **return** regions in the
   0.30 mm substrate, with the copper fraction split between them and placed at the actual
   cell footprints rather than smeared over 900 mm². This preserves copper volume and
   location, so the mechanical and thermal effect is right even though individual vias are
   not resolved.
2. **Preferred:** explicit allocation of supply and ground via counts per cell from the
   current and `J_design`, with ground planes in the land-side and top RDLs.

Neither is implemented yet. **Until one is, Z2-CUTOUT is a geometry proposal, not a
production model**, and no ETM result may be generated from it (Task G gate).

## 4. Pin alignment and current crowding

Xu 2019 cautions that bottom placement changes BGA pinout and creates **area congestion on
the package bottom** — in that work some decoupling capacitors had to move to the top. The
task asked whether our geometry suffers the corresponding problem: are the cell outputs
laterally misaligned with the die POLs they feed?

Measured on the actual tile placement:

| | value |
|---|---:|
| die | 22.36 mm, partitioned 7 × 7 for POL regions |
| POL region pitch | 3.194 mm |
| cell-centre pitch | 3.165 mm |
| cell-centre → POL-region-centre offset, mean | **77 µm** |
| offset, max (corner cell) | **123 µm** |

The cell grid and the POL partition are concentric and almost co-pitched, so the worst
residual low-voltage lateral run is **123 µm against a 1963 µm vertical stack**. The current
path is vertical to within about 6 % of its own length.

**So Xu's misalignment concern does not bite in this geometry** — but that is a property of
the 7 × 7 uniform placement, not of land-side VR in general. If the cell grid were
re-pitched, or cells were displaced to clear the cutout sidewall, the offsets would grow
and the lateral RDL spreading would have to be re-evaluated. The congestion half of Xu's
warning **does** apply: the land side now hosts the VR grid, its RDL and the peripheral
BGA, and nothing else has been allocated there.
