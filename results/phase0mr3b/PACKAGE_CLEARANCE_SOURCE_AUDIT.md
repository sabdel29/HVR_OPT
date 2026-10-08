# PHASE 0M-R3B SECTION 7 --- PACKAGE-CLEARANCE SOURCE AUDIT

Phase 0M-R2 searched for these three numbers and found none. This phase reached two new primary sources on embedded-component substrates, so the search was repeated against them rather than restated.

| clearance | where it applies | 0M-R2 | 0M-R3B | what was found |
|---|---|---|---|---|
| `die_to_component_gap_um` | between the top of the converter tier and the bottom of the compute die | OPEN | **SOURCE_BOUNDED** | RCC lamination over an embedded die: 'A thickness of 15-20 um over the chip surface is desirable for the subsequent microvia opening and filling' |
| `cavity_sidewall_um` | in plane, around every embedded component in ARCH_Z1's substrate cavity | OPEN | **OPEN** | nothing numeric. The chip-embedding source discusses cavity ASPECT RATIO for etched copper line cavities, a different feature entirely |
| `cooler_standoff_um` | between the top of the die/TIM stack and the cooler base | OPEN | **OPEN** | nothing. The five hits were unrelated fields |

### The one that moved

RCC lamination over an embedded die: 'A thickness of 15-20 um over the chip surface is desirable for the subsequent microvia opening and filling'

*Source:* Ostmann et al., 'Industrial and Technical Aspects of Chip Embedding Technology', Fraunhofer IZM / AT&S / IMEC-CMST 2008

*Is it the same feature?* NO -- that is the dielectric cap over an EMBEDDED die, not the gap between the compute-die underside and the tier below it. Closest sourced analogue, used as a bound and labelled as one

*Effect:* 15-20 um lies INSIDE the existing [10, 25, 50] um bound, so no corner of the 27-corner sweep moves and no verdict changes

### The two that did not

`cavity_sidewall_um` and `cooler_standoff_um` remain **OPEN**. Their bounds are unchanged and are still anchors, not sources.

## Are the clearances the only remaining blocker?

**No.** After the `ls_to_L` correction the vertical interconnect fails first, on sourced via rules, at every one of the 27 clearance corners. The clearance question is no longer the binding one.
