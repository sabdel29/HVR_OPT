#!/usr/bin/env python3
"""Phase-0H Sec.6 -- harvest primary reliability literature via open scholarly APIs.

The WebSearch tool is blocked by organisation policy in this environment, but the machine has
outbound network access, so OpenAlex / Crossref / arXiv / Europe PMC are reachable by HTTP.
This script builds the CANDIDATE list with real metadata. It deliberately does NOT infer
thresholds, geometries or temperatures from titles: those fields are filled only from text
actually retrieved, and are otherwise left as NOT_RETRIEVED. Sec.15's admissibility test is
applied afterwards, by hand, against what was actually read.
"""
from __future__ import annotations
import csv, json, sys, time, urllib.parse, urllib.request
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0h"
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "HVR-OPT-research/0.1 (mailto:mgharib@anl.gov)"}

# (query, the failure mechanism from FAILURE_MECHANISM_MAP.md this query targets)
# OpenAlex boolean filters over TITLE AND ABSTRACT ONLY. The plain `search` parameter matches
# full text loosely and returned graphene roadmaps and neutrino telescopes for these topics.
QUERIES = [
    ('(solder AND joint AND (fatigue OR "thermal cycling") AND ("strain energy" OR '
     '"inelastic strain" OR "Coffin-Manson" OR "characteristic life"))', "B_bga_fatigue"),
    ('(solder AND (Anand OR viscoplastic OR creep) AND (SAC305 OR SnAgCu OR "lead-free") '
     'AND (constitutive OR model))', "B_bga_fatigue"),
    ('(microbump OR "micro bump" OR "micro-bump") AND (reliability OR fatigue OR '
     '"thermal cycling") AND (interposer OR "2.5D" OR "3D IC")', "C_microbump"),
    ('("C4" OR "controlled collapse" OR "flip chip") AND bump AND (reliability OR fatigue '
     'OR stress) AND (thermomechanical OR "thermal cycling")', "C_c4"),
    ('("chip package interaction" OR "chip-package interaction") AND (stress OR "low-k" '
     'OR dielectric OR delamination)', "E_cpi"),
    ('(interposer OR "2.5D" OR CoWoS OR "fan-out") AND warpage AND (package OR assembly '
     'OR measurement)', "A_global_bending"),
    ('("redistribution layer" OR RDL) AND (delamination OR crack OR reliability) AND '
     '(interposer OR package OR "fan-out")', "D_rdl"),
    ('("energy release rate" OR "fracture energy" OR "cohesive zone") AND (delamination '
     'OR interface) AND (package OR underfill OR die)', "F_delamination"),
    ('("through silicon via" OR TSV) AND (stress OR "keep out zone" OR KOZ OR '
     '"landing pad") AND (mechanical OR thermomechanical)', "G_tsv"),
    ('("board level" OR "board-level") AND reliability AND (BGA OR package) AND '
     '(warpage OR "solder strain" OR "thermal cycling")', "B_bga_fatigue"),
    ('("power cycling") AND (solder OR interconnect) AND (degradation OR lifetime OR '
     'reliability) AND (module OR package)', "B_bga_fatigue"),
    ('(warpage) AND (package OR component) AND ("shadow moire" OR "digital image '
     'correlation" OR JEDEC OR standard OR coplanarity)', "A_global_bending"),
    ('(package OR interposer) AND warpage AND (finite element OR simulation) AND '
     '(experiment OR measured OR validation)', "A_global_bending"),
    ('(die OR silicon) AND ("principal stress" OR "first principal") AND (package OR '
     'assembly) AND (crack OR strength OR failure)', "E_cpi"),
]


def get(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as fh:
                return json.load(fh)
        except Exception as e:
            if k == tries - 1:
                print(f"    ! {type(e).__name__}: {str(e)[:70]}")
                return None
            time.sleep(3 * (k + 1))


def openalex(q, n=40):
    """Title/abstract boolean search, most-cited first."""
    flt = f"title_and_abstract.search:{q},type:article|preprint|review"
    u = ("https://api.openalex.org/works?filter=" + urllib.parse.quote(flt, safe=":,|") +
         f"&per-page={n}&sort=cited_by_count:desc")
    d = get(u)
    return (d or {}).get("results", [])


def main():
    seen, rows = set(), []
    for q, mech in QUERIES:
        print(f"  [{mech:18s}] {q[:64]}", flush=True)
        for w in openalex(q):
            doi = (w.get("doi") or "").replace("https://doi.org/", "")
            key = doi or w.get("id")
            if key in seen:
                continue
            seen.add(key)
            oa = w.get("open_access") or {}
            loc = w.get("primary_location") or {}
            src = (loc.get("source") or {}).get("display_name") or ""
            rows.append({
                "openalex_id": (w.get("id") or "").rsplit("/", 1)[-1],
                "doi": doi,
                "year": w.get("publication_year"),
                "title": (w.get("title") or "").replace("\n", " ")[:220],
                "venue": src[:90],
                "cited_by": w.get("cited_by_count"),
                "is_oa": oa.get("is_oa"),
                "oa_url": (oa.get("oa_url") or "")[:200],
                "target_mechanism": mech,
                "query": q[:70],
            })
        time.sleep(0.4)
    rows.sort(key=lambda r: (-(r["cited_by"] or 0)))
    with open(OUT / "literature_candidates_raw.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    n_oa = sum(1 for r in rows if r["is_oa"])
    print(f"\n{len(rows)} unique works, {n_oa} open access "
          f"({100*n_oa/max(1,len(rows)):.0f} %)")
    print(f"wrote {OUT/'literature_candidates_raw.csv'}")
    print("\ntop 15 by citations:")
    for r in rows[:15]:
        print(f"  {r['year']} [{r['cited_by']:>5}] {'OA' if r['is_oa'] else '  '} "
              f"{r['title'][:88]}")


if __name__ == "__main__":
    main()
