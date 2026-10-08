#!/usr/bin/env python3
"""Phase-0I Sec.9 -- harvest primary literature for a SOLDER CONSTITUTIVE + LIFE model.

What is needed is narrow and specific, so the queries are narrow and specific:
  * a temperature-dependent elastic modulus for a NAMED alloy;
  * a creep or viscoplastic law with an ACTUAL PARAMETER SET (Anand, Garofalo/hyperbolic-sine,
    or Norton) for that same alloy;
  * a fatigue correlation N_f = f(metric) with its constants, its metric definition and the
    package it was calibrated on.

Parameter sets must not be mixed across alloys, so the alloy is carried as a first-class field
and every row records which alloy it belongs to.
"""
from __future__ import annotations
import csv, json, time, urllib.parse, urllib.request
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0i"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "HVR-OPT-research/0.1 (mailto:mgharib@anl.gov)"}

QUERIES = [
    ('(Anand AND (SAC305 OR SnAgCu OR "Sn-Ag-Cu") AND (parameter OR constant OR '
     'calibrat))', "anand_params"),
    ('((Garofalo OR "hyperbolic sine" OR "hyperbolic-sine") AND creep AND (solder OR SAC))',
     "garofalo_creep"),
    ('(Norton AND creep AND solder AND (SnAgCu OR SAC305 OR SnPb OR eutectic))',
     "norton_creep"),
    ('(solder AND "elastic modulus" AND temperature AND (dependence OR dependent) AND '
     '(SAC OR SnAgCu OR SnPb))', "temperature_dependent_E"),
    ('(Darveaux AND (crack OR "energy density" OR correlation) AND solder)', "darveaux"),
    ('(solder AND "strain energy density" AND ("cycles to failure" OR "fatigue life") AND '
     'correlation AND (constant OR coefficient))', "sed_life_law"),
    ('(solder AND fatigue AND "plastic strain range" AND ("Coffin-Manson" OR "cycles to '
     'failure"))', "coffin_manson"),
    ('(microbump OR "copper pillar" OR "Cu pillar") AND solder AND (creep OR viscoplastic '
     'OR fatigue) AND (interposer OR "2.5D" OR "3D"))', "microbump_fatigue"),
    ('(solder AND joint AND (submodel OR "sub-model" OR "global-local") AND (fatigue OR '
     'thermal cycling))', "submodelling"),
    ('(volume AND averag AND (solder OR joint) AND ("strain energy" OR "inelastic") AND '
     '(mesh OR element OR convergence))', "volume_averaging"),
]


def get(url, tries=3):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=45) as fh:
                return json.load(fh)
        except Exception as e:
            if k == tries - 1:
                print(f"    ! {type(e).__name__}: {str(e)[:60]}")
                return None
            time.sleep(3 * (k + 1))


def openalex(q, n=40):
    flt = f"title_and_abstract.search:{q},type:article|preprint|review"
    u = ("https://api.openalex.org/works?filter=" + urllib.parse.quote(flt, safe=":,|") +
         f"&per-page={n}&sort=cited_by_count:desc")
    return (get(u) or {}).get("results", [])


def main():
    seen, rows = set(), []
    for q, tag in QUERIES:
        print(f"  [{tag:24s}] {q[:58]}", flush=True)
        for w in openalex(q):
            doi = (w.get("doi") or "").replace("https://doi.org/", "")
            key = doi or w.get("id")
            if key in seen:
                continue
            seen.add(key)
            oa = w.get("open_access") or {}
            loc = w.get("primary_location") or {}
            rows.append({
                "need": tag, "year": w.get("publication_year"),
                "title": (w.get("title") or "").replace("\n", " ")[:200],
                "venue": ((loc.get("source") or {}).get("display_name") or "")[:80],
                "cited_by": w.get("cited_by_count"), "doi": doi,
                "is_oa": oa.get("is_oa"), "oa_url": (oa.get("oa_url") or "")[:200]})
        time.sleep(0.4)
    rows.sort(key=lambda r: (r["need"], -(r["cited_by"] or 0)))
    with open(OUT / "solder_literature_raw.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    n_oa = sum(1 for r in rows if r["is_oa"])
    print(f"\n{len(rows)} unique works, {n_oa} open access")
    for tag, _ in [(t, q) for q, t in QUERIES]:
        pass
    from collections import Counter
    for t, c in Counter(r["need"] for r in rows).most_common():
        oa = sum(1 for r in rows if r["need"] == t and r["is_oa"])
        print(f"  {t:24s} {c:3d} works, {oa:2d} OA")
    print("\nmost-cited OA per need:")
    for t in dict.fromkeys(r["need"] for r in rows):
        best = [r for r in rows if r["need"] == t and r["is_oa"]][:2]
        for b in best:
            print(f"  [{t:22s}] {b['year']} [{b['cited_by']:>4}] {b['title'][:66]}")
            print(f"      {b['oa_url'][:104]}")
    print(f"\nwrote {OUT/'solder_literature_raw.csv'}")


if __name__ == "__main__":
    main()
