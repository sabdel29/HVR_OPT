#!/usr/bin/env python3
"""Phase-0L Part VII -- build high_stress_sac305_sources.csv.

Two tiers, kept strictly separate:
  EXAMINED  -- full text retrieved and read in this environment; every field is verified.
  SCREENED  -- found by the API search; only bibliographic metadata is known.  Content fields
               are recorded as 'not retrieved', never guessed.
"""
from __future__ import annotations
import csv, json, re
from pathlib import Path

R = Path(__file__).resolve().parents[2]
NR = "not retrieved"

EXAMINED = [
    dict(key="Yuan2023", citation="Yuan C., Su Q., Chiang K.-N., Materials 16(14):4922 (2023)",
         doi="10.3390/ma16144922", alloy="Sn3.9Ag0.6Cu (creep/Garofalo); SAC305 (Anand/Chaboche)",
         temperature_C="45, 80, 115, 150 (creep); -40..122 (Chaboche)",
         stress_MPa="7.51-15.92 (creep Table 5)",
         strain_rate_1_per_s="1.4e-9 .. 8.1e-7 (creep); 1e-3..1e-5 (Anand source)",
         test_type="tabulation of others' tensile creep + tensile stress-strain",
         constitutive_law="Garofalo (Table 6); Anand 9-param (Tables 7,9); Chaboche (Tables 10,11)",
         parameters=("Garofalo EINN+BI C1=0.443 C2=0.482 C3=1.073 Q=65 kJ/mol; "
                     "Anand EINN+BI A=1649 n=1.64e-4 m=0.53 beta=4.16 xi=17.66 s0=57.45 "
                     "a=2.26 h0=828822 Q=65 kJ/mol; Chaboche sigma0 39.32/33.80/21.35/15.43/10.50"),
         sample_geometry=NR, primary_secondary="SECONDARY (tabulates [10] and [12])",
         availability="OPEN ACCESS, full text read (PMC10381129)",
         relevance="HIGH - it is the actual source of the current card",
         admissibility=("Chaboche/Anand admissible as SAC305; Garofalo and the 19 creep points "
                        "are Sn3.9Ag0.6Cu and NOT admissible as SAC305 without transferability "
                        "evidence, which was not found")),
    dict(key="XiaoArmstrong2005",
         citation="Xiao Q., Armstrong W.D., J. Electron. Mater. 34:196-211 (2005)",
         doi="10.1007/s11664-005-0233-z", alloy="Sn3.9Ag0.6Cu",
         temperature_C="45, 80, 115, 150", stress_MPa="7.51-15.92",
         strain_rate_1_per_s="1.4e-9 .. 8.1e-7", test_type="bulk tensile creep",
         constitutive_law="Garofalo (fitted by the authors)",
         parameters="C1=0.184 C2=0.221 C3=2.89 Q=62 kJ/mol (as tabulated by Yuan 2023 Table 6)",
         sample_geometry="bulk specimens", primary_secondary="PRIMARY",
         availability="PAYWALLED (Springer); values known only via Yuan 2023 Tables 5 and 6",
         relevance="HIGH - the actual measurements behind the current creep card",
         admissibility=("NOT SAC305. Ag 3.9 wt% vs 3.0 wt%. Stress window 7.5-15.9 MPa, far "
                        "below package stresses. Inadmissible as a SAC305 high-stress source")),
    dict(key="Motalab2012",
         citation="Motalab M., Cai Z., Suhling J.C., Lall P., Proc. ITherm 2012",
         doi="", alloy="SAC305", temperature_C="-40 .. 122 (per Yuan's use of the data)",
         stress_MPa=NR, strain_rate_1_per_s="1e-3, 1e-4, 1e-5",
         test_type="tensile stress-strain / creep",
         constitutive_law="Anand 9-parameter",
         parameters=("A=3501 n=1.00e-2 m=0.25 beta=7.55 xi=4 s0=21 a=1.78 h0=18000 "
                     "(Yuan 2023 Tables 7,9); activation energy NOT reported by Yuan"),
         sample_geometry=NR, primary_secondary="PRIMARY",
         availability="PAYWALLED (IEEE); parameters known only via Yuan 2023",
         relevance="HIGH - the only SAC305 source covering tensile stress levels",
         admissibility=("CONDITIONAL. Correct alloy and stress range, but the parameter set is "
                        "incomplete here (no Q) and its source data could not be retrieved, so "
                        "the Part X reproduction test cannot be run on it")),
    dict(key="Micromachines2018",
         citation="Calibration of a Constitutive Model from Tension and Nanoindentation for "
                  "Lead-Free Solder, Micromachines 9(11):608 (2018)",
         doi="10.3390/mi9110608", alloy="SAC305", temperature_C="27 only",
         stress_MPa="representative stress ~25.23 MPa after 210 C anneal",
         strain_rate_1_per_s="0.05 (nanoindentation)",
         test_type="uniaxial tension + instrumented nanoindentation",
         constitutive_law="power-law hardening (representative stress / hardening exponent)",
         parameters="sigma_R ~ 25.23 MPa stabilised; n and R reported graphically",
         sample_geometry="bulk tensile specimens + indentation", primary_secondary="PRIMARY",
         availability="OPEN ACCESS, full text read (PMC6266157)",
         relevance="LOW for our window - room temperature only",
         admissibility="NOT ADMISSIBLE for 45-150 C; no elevated-temperature data"),
    dict(key="Materials2021",
         citation="Grain-Scale Anisotropic Analysis of Steady-State Creep in Oligocrystalline "
                  "SAC Solder Joints, Materials 14(20):5973 (2021)",
         doi="10.3390/ma14205973", alloy="SAC (Sn3.0Ag0.5Cu joints)",
         temperature_C="room temperature", stress_MPa="<12 (explicitly low-stress fit)",
         strain_rate_1_per_s=NR, test_type="grain-scale virtual tests + joint-scale testing",
         constitutive_law="Hill-Norton (anisotropic)",
         parameters="A=9.51e-12, n=3.05, F=G=1, H=2.75, L=M=2.24, N=2.15",
         sample_geometry="oligocrystalline joints", primary_secondary="PRIMARY",
         availability="OPEN ACCESS, full text read (PMC8541237)",
         relevance="LOW for our window - fitted explicitly for stresses below 12 MPa",
         admissibility="NOT ADMISSIBLE as a high-stress source; authors restrict it to <12 MPa"),
]


def main():
    hits = json.load(open(R / "results/phase0l/lit/raw_hits.json"))
    ALLOY = re.compile(r"\bSAC\s?-?305\b|Sn\s?-?3\.0\s?Ag\s?-?0\.5\s?Cu|Sn3\.0Ag0\.5Cu|SnAgCu"
                       r"|SAC\b|lead-?free solder|Pb-?free solder", re.I)
    CONST = re.compile(r"anand|constitutive|creep|viscoplastic|stress[- ]strain|strain rate"
                       r"|relaxation|garofalo|hyperbolic sine|plasticity|yield|elastic modulus"
                       r"|mechanical propert", re.I)
    cols = ["tier", "key", "citation", "doi", "alloy", "temperature_C", "stress_MPa",
            "strain_rate_1_per_s", "test_type", "constitutive_law", "parameters",
            "sample_geometry", "primary_secondary", "availability", "relevance",
            "admissibility"]
    rows = [dict(tier="EXAMINED", **e) for e in EXAMINED]
    seen = {e["doi"].lower() for e in EXAMINED if e["doi"]}
    for h in hits:
        if not (ALLOY.search(h["title"]) and CONST.search(h["title"])):
            continue
        if h["doi"].lower() in seen:
            continue
        seen.add(h["doi"].lower())
        rows.append(dict(tier="SCREENED", key="", doi=h["doi"],
                         citation=f"{h['title']} ({h['year']}) {h['venue']}".strip(),
                         alloy=NR, temperature_C=NR, stress_MPa=NR,
                         strain_rate_1_per_s=NR, test_type=NR, constitutive_law=NR,
                         parameters=NR, sample_geometry=NR, primary_secondary=NR,
                         availability=("OPEN ACCESS (not retrieved)" if h["is_oa"]
                                       else "PAYWALLED / not retrievable here"),
                         relevance="title-screened only", admissibility="NOT ASSESSED"))
    p = R / "results/phase0l/high_stress_sac305_sources.csv"
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"wrote {p}")
    print(f"  EXAMINED (full text read): {sum(1 for r in rows if r['tier']=='EXAMINED')}")
    print(f"  SCREENED (metadata only) : {sum(1 for r in rows if r['tier']=='SCREENED')}")
    oa = sum(1 for r in rows if r["tier"] == "SCREENED" and "OPEN" in r["availability"])
    print(f"    of which open access    : {oa}")


if __name__ == "__main__":
    main()
