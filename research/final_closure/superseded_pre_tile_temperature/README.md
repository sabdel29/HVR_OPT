# Superseded: the direct-fed lineage before the E-T coupling fix (DEFECT #68)

The first results of the corrected (direct-fed) lineage were computed with an E-T coupling
that fed the converter loss model the node mean of the **whole** converter tiers,
encapsulant between the cells included, while the device losses were deposited only inside
the 49 cell footprints. `diagnostic_conv_mean.txt` gives the two means on the converged
HV-S0 fields:

| architecture | node mean, whole tiers (used) | node mean, inside the cells |
|---|---:|---:|
| Z1 | 111.81 C | 110.58 C |
| Z2 (direct-fed) | 104.48 C | 112.32 C |

The bias had opposite signs in the two architectures, so it moved the loss comparison: the
pre-fix HV-S0 package-internal losses were 146.47 W (Z1) and 141.22 W (Z2), a 5.2 W Z2
advantage and a crossover R* of 9.19 mOhm (`direct_feed_crossover.json` here).

Every ledger temperature is now the mean over the region its terms deposit in, each device
term at its own tier's in-cell temperature (`final_closure_physical_etm.temperature_regions`),
and every case, sensitivity and reference was re-run. The three files here are kept for
provenance only; no current result reads them.
