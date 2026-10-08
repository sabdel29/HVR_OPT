# PRIMARY SOURCES THAT COULD NOT BE DOWNLOADED FROM THIS HOST

Each would close a parameter that is currently OPEN. Crossref, OpenAlex, Unpaywall and Europe PMC are reachable; MDPI, IEEE Xplore and ScienceDirect full text are not (every route returns a ~415-byte block page).

| # | source | DOI / locator | parameter it would close |
|---|---|---|---|
| 1 | *A Short Review of Through-Silicon Via (TSV) Interconnects: Metrology and Analysis*, Applied Sciences 13(14):8301, 2023 | `10.3390/app13148301` | TSV diameter, depth and taper manufacturing tolerance (Section 8) |
| 2 | *Advanced 3D Through-Si-Via and Solder Bumping Technology: A Review*, Materials 16(24):7652, 2023 | `10.3390/ma16247652` | TSV liner and plating tolerance (Section 8) |
| 3 | *Fan-Out Panel-Level PCB-Embedded SiC Power MOSFETs Packaging*, IEEE JESTPE, 2019 | `10.1109/JESTPE.2019.2952238` | microvia diameter, pad and current-carrying capability for an embedded POWER device -- the closest published analogue to `ls_to_L` |
| 4 | *A Review of Polymer Dielectrics for Redistribution Layers in Interposers and Package Substrates*, Polymers 15(19):3895, 2023 | `10.3390/polym15193895` | modern package-substrate build-up via diameter and pitch, to replace the 2008 chip-embedding numbers used here as a bound |
| 5 | substrate-vendor / OSAT design-rule manual (any of Ibiden, Shinko, AT&S, Unimicron) | released under NDA; no public copy | capture-pad diameter, stacking limit and minimum annular ring for package-substrate microvias |
| 6 | EPC2057 land-pattern drawing | EPC datasheet, not in this repository | the switch-node land area, which bounds how many vias can land on the die at all |

Items 3, 5 and 6 are the ones that would actually decide this gate. Without them the microvia diameter, the capture pad, the landing area and the via current limit all stay OPEN, and the `ls_to_L` repair cannot be qualified.
