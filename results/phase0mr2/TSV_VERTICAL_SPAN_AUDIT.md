# PHASE 0M-R2 SECTION 3 --- TSV VERTICAL-SPAN AUDIT

## The question

Phase 0M-R reported that at a 300 um span and a 10:1 aspect limit only r >= 15 um is
buildable, and that at 1300 um no radius in the swept range works. The 1300 um rung was
read as a warning about the 1.30 mm substrate that ARCH_Z1 uses.

**No architecture traverses 1300 um.** ARCH_Z1 has a 1.30 mm substrate, but 1226 um of it
is the embedded converter cell, and the cell sits ON TOP of the via field. Its TSVs
traverse the remaining 74 um.

## What each architecture actually traverses

| architecture | h_sub | converter cell | TSV start | TSV end | **span** | d | AR | d_min at AR 10 | rail | feasible |
|---|---|---|---|---|---|---|---|---|---|---|
| Z1_EMBEDDED | 1300 um | 1226 um | 0 um | 74 um | **74 um** | 30 um | 2.47 | 7.4 um | HV | yes |
| Z2_BACKSIDE | 300 um | 0 um | 0 um | 300 um | **300 um** | 30 um | 10.00 | 30.0 um | LV | yes |
| Z4_POWER_DIE | 300 um | 0 um | 0 um | 300 um | **300 um** | 30 um | 10.00 | 30.0 um | HV | yes |
| Z5_2P5D_LATERAL | 300 um | 0 um | 0 um | 300 um | **300 um** | 30 um | 10.00 | 30.0 um | HV | yes |

The rule for each span is the architecture's own declared power path:

* **Z1_EMBEDDED** --- h_sub - t_cell: the embedded cell sits ON TOP of the via field
* **Z2_BACKSIDE** --- the full substrate: the 1 V rail crosses it from the backside VR
* **Z4_POWER_DIE** --- the full substrate: the 48 V rail rises to the power die above it
* **Z5_2P5D_LATERAL** --- the full substrate: the 48 V rail rises to the lateral VR field

## Three domains, three answers --- the inconsistency that was there

The TSV length was being decided independently in three places:

| domain | where | ARCH_Z2 length |
|---|---|---|
| electrical | `zpower.evaluate_z` | 300 um |
| mechanical / thermal | `etm.mesh`, the meshed `tsv_homog` region | **280 um** |
| feasibility | `tsv_production.sweep` | a hard-coded 100 / 300 / 1300 ladder tied to no architecture |

The mechanical model gave the field only `sub_lower` = h_sub - t_tile. For ARCH_Z2 and
ARCH_Z4 a 20 um band is reserved at the substrate top even though those architectures put
no converter in the substrate, so 20 um of the via field was missing: a 6.67 %
disagreement between the domains, on the same physical via.

## What was done

`configs/phase0mr2/architecture_geometry.yaml` is now the single source, and
`scripts/phase0mr2/arch_geometry.py::assert_consistent` fails if any two domains disagree
by more than 0.5 %. For the architectures that do not embed their converter, the band at
the substrate top is a routing layer that the field passes THROUGH, so it is marked as a
TSV host and the meshed field spans the full substrate.

| architecture | contract | electrical | mechanical | agreement |
|---|---|---|---|---|
| Z1_EMBEDDED | 74.0 um | 74.0 um | 74.0 um | OK (0.000 %) |
| Z2_BACKSIDE | 300.0 um | 300.0 um | 300.0 um | OK (0.000 %) |
| Z4_POWER_DIE | 300.0 um | 300.0 um | 300.0 um | OK (0.000 %) |
| Z5_2P5D_LATERAL |  um | -- | -- | NOT CHECKED: KeyError: 'ARCH_Z5_2P5D_LATERAL' |

## Is the 30 um reference TSV valid everywhere it is used?

**Yes, and two of the three sit exactly on the limit.**

* ARCH_Z1 at 74 um: AR = 2.47, with large margin. A 30 um via is comfortable here, and
  the smallest diameter the span would permit is 7.4 um.
* ARCH_Z2, ARCH_Z4 and ARCH_Z5 at 300 um: AR = 10.00, **exactly** the demonstrated
  capability. There is no margin: any increase in substrate thickness, or any reduction
  in via diameter, makes these architectures unbuildable at the sourced capability.

That is a tighter statement than Phase 0M-R's. The alarming 1300 um case does not exist;
the real exposure is that three of the four architectures sit ON the limit rather than
near it.
