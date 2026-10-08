#!/usr/bin/env python3
"""Phase-0M-R3B Section 3 --- the substrate-via source matrix.

Every row is a parameter the `ls_to_L` repair depends on, with what the sources actually
say and what remains OPEN. Nothing here is a blog, a calculator or a transferred TSV rule.

Provenance vocabulary:
  SOURCE_BACKED   a primary source states this value for THIS interconnect class
  SOURCE_BOUNDED  a primary source states it for a comparable class, so it bounds but does
                  not fix the value here
  OPEN            no source in reach states it
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3b"

S_OST = ("Ostmann, Manessis, Stahr, Beesley, Cauwe, De Baets, 'Industrial and Technical "
         "Aspects of Chip Embedding Technology', Fraunhofer IZM / AT&S / IMEC-CMST, 2008 "
         "(biblio.ugent.be/publication/2974727)")
S_CAU = ("Cauwe, Vandevelde, Nawghane, Van De Slyeke, Coulon, Heltzel, 'Challenges in "
         "introducing high-density interconnect technology in printed circuit boards for "
         "space applications', CEAS Space Journal 15:101-112 (2023), "
         "doi:10.1007/s12567-021-00403-2")
S_JUN = ("June-2026 DVPD source, arXiv 2606.28837 Sec. II: low-side switches, flying "
         "capacitors and inductors 'embedded within the subsequent substrate power layers'")
S_EPC = "EPC product table, Scalable_Integrated_VR/EPC-Product-Table.csv"
S_FW = "framework's own geometry: scripts/phase0mr/routing_production.py H_UM, RDL_UM"

ROWS = [
 dict(parameter="interconnect class", design_point="stacked build-up microvia through "
      "embedded-component substrate power layers",
      source_says="components are embedded in successive substrate power layers; contacts "
                  "to embedded dies are made by laser-drilled, metallised microvias",
      value_in_source="Chip-in-Polymer / chip-in-substrate", provenance="SOURCE_BACKED",
      source=f"{S_JUN}; {S_OST}"),
 dict(parameter="physical span to cross", design_point="120 um (3 dielectric layers)",
      source_says="tier extents give gan_ls top 1301 um, inductor bottom 1421 um",
      value_in_source="120 um = RDL 10 + cap tier 100 + RDL 10", provenance="SOURCE_BACKED",
      source=S_FW),
 dict(parameter="single via or chain", design_point="chain: >=3 levels, one per dielectric",
      source_says="microvias are formed one build-up layer at a time; multi-level "
                  "connections are stacked or staggered microvias",
      value_in_source="1 microvia per build-up layer", provenance="SOURCE_BACKED",
      source=S_CAU),
 dict(parameter="stacking limit", design_point="3 stacked levels required by the 3-layer gap",
      source_says="the qualified configuration is two stacked microvias plus one staggered; "
                  "'Stacking three levels of microvias is considered a reliability risk'",
      value_in_source="2 stacked + 1 staggered; 3 stacked = reliability risk",
      provenance="SOURCE_BOUNDED", source=S_CAU),
 dict(parameter="microvia pitch", design_point="70 um",
      source_says="microvia interconnection to embedded chip pads is demonstrated at "
                  "min. 150 um I/O pad pitch in production and 100 um at prototype level; "
                  "'For pitches smaller than 100 um ... vialess interconnection methods' "
                  "are indicated instead",
      value_in_source="150 um production, 100 um prototype, <100 um not by microvia",
      provenance="SOURCE_BOUNDED", source=S_OST),
 dict(parameter="microvia diameter", design_point="40 um (r = 20 um)",
      source_says="microvia diameters given are PCB-scale: 125 um and 175 um as-designed "
                  "for the two qualified HDI builds. No package-substrate-scale diameter "
                  "was reachable from this host",
      value_in_source="125-175 um (PCB HDI, coarser class)", provenance="OPEN",
      source=S_CAU),
 dict(parameter="minimum Cu in the via", design_point="liner 0.5 um, remainder Cu",
      source_says="'A minimum thickness of 10 um Cu is required in the microvias'; near-"
                  "complete filling achievable with dedicated plating chemistry",
      value_in_source="10 um minimum plated Cu", provenance="SOURCE_BACKED", source=S_OST),
 dict(parameter="capture / target pad", design_point="not modelled",
      source_says="enlarged Cu pads are added on the chip; 5 um Cu is applied to the bond "
                  "pads. Pad DIAMETER for this class is not stated",
      value_in_source="pad enlargement required, diameter unstated", provenance="OPEN",
      source=S_OST),
 dict(parameter="placement / overlay tolerance", design_point="not modelled",
      source_says="die placement accuracy +/-10 um at 3 sigma; alignment of the microvia to "
                  "the underlying Cu pattern is the yield-limiting step",
      value_in_source="+/-10 um at 3 sigma", provenance="SOURCE_BACKED", source=S_OST),
 dict(parameter="landing area at the die", design_point="whole 1.80 mm2 die footprint, "
      "areal packing 0.5",
      source_says="EPC2057 is an LGA 1.5 x 1.2 mm part, so vias can only land on its lands, "
                  "not on arbitrary points of its footprint. The land pattern is not in any "
                  "source held here",
      value_in_source="LGA 1.5 x 1.2 mm; land pattern unstated", provenance="OPEN",
      source=S_EPC),
 dict(parameter="via current-carrying limit", design_point="J_design = 1.0e8 A/m2",
      source_says="no current-density guidance for build-up microvias was found in any "
                  "source reachable from this host",
      value_in_source="-", provenance="OPEN", source="-"),
 dict(parameter="aspect ratio per microvia", design_point="AR = 10/40 = 0.25 (RDL) and "
      "100/40 = 2.5 (capacitor layer)",
      source_says="microvia AR is named as a primary reliability driver but no numeric "
                  "limit for this class was reachable; the HDI paper's AR statements apply "
                  "to CORE vias, a different structure",
      value_in_source="-", provenance="OPEN", source=S_CAU),
]


def main() -> int:
    p = OUT / "substrate_via_source_matrix.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ROWS[0])); w.writeheader(); w.writerows(ROWS)
    from collections import Counter
    c = Counter(r["provenance"] for r in ROWS)
    for r in ROWS:
        print(f"  {r['provenance']:15s} {r['parameter']:32s} {r['value_in_source'][:52]}")
    print(f"\n{len(ROWS)} parameters: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
