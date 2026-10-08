#!/usr/bin/env python3
"""Phase-0L-R Part 5 -- targeted search for SAC305 constitutive data in the ACTUAL gap.

The gap is 45-150 C at roughly 15-100+ MPa. Phase 0L searched mostly on the word "creep" and
found nothing retrievable there. High-stress constitutive information also lives in
multi-rate tensile curves, stress-relaxation tests and Anand/Chaboche calibrations, so this
search deliberately does NOT lead with "creep".

WebSearch is blocked by org policy in this environment; HTTPS egress is not. The search runs
against OpenAlex, Crossref and Europe PMC, which is reproducible and citable.
"""
from __future__ import annotations
import json, re, subprocess, time, urllib.parse
from pathlib import Path

R = Path(__file__).resolve().parents[2]
CACHE = R / "results" / "phase0lr" / "lit" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
UA = "hvr-opt-research/1.0 (mailto:mgharib@anl.gov)"

QUERIES = [
    # Anand / unified viscoplastic -- the family that reaches tensile stress levels
    "Anand constants SAC305 solder determination stress strain",
    "Anand model parameters lead-free solder nine constants temperature",
    "modified Anand constitutive model SAC305 elevated temperature",
    "Anand parameters SAC305 aging isothermal elevated temperature",
    # multi-rate tensile -- high stress without the word creep
    "SAC305 uniaxial tensile stress strain curves multiple strain rates temperatures",
    "lead-free solder constant strain rate tensile 125 C stress strain",
    "SAC305 mechanical properties elevated temperature tensile yield ultimate",
    "Sn-3.0Ag-0.5Cu tensile behaviour temperature dependence strain rate",
    # stress relaxation
    "SAC305 stress relaxation solder elevated temperature",
    "lead-free solder stress relaxation test constitutive parameter extraction",
    # creep at high stress / power-law breakdown
    "SAC305 steady state creep stress exponent power law breakdown",
    "Sn-3.0Ag-0.5Cu creep hyperbolic sine Garofalo activation energy",
    "double power law creep lead-free solder SnAgCu",
    # cyclic / Chaboche
    "SAC305 cyclic stress strain viscoplastic Chaboche parameters",
    "SAC305 cyclic hysteresis loop solder temperature strain rate",
    # groups known to produce this data
    "Suhling Lall SAC305 solder constitutive aging mechanical",
    "Motalab Anand constants SAC solders creep stress strain data",
    "Chiang SAC305 constitutive equation solder joint reliability",
]


def fetch(url: str, tag: str):
    f = CACHE / (re.sub(r"[^A-Za-z0-9_.-]", "_", tag)[:120] + ".json")
    if f.is_file():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    cp = subprocess.run(["curl", "-s", "--max-time", "60", "-A", UA, url],
                        capture_output=True, text=True)
    if cp.returncode != 0 or not cp.stdout.strip():
        return None
    try:
        d = json.loads(cp.stdout)
    except Exception:
        return None
    f.write_text(json.dumps(d)); time.sleep(1.0)
    return d


def openalex(q):
    d = fetch("https://api.openalex.org/works?search=" + urllib.parse.quote(q)
              + "&per-page=25&mailto=mgharib@anl.gov", "oa_" + q)
    for w in (d or {}).get("results", []):
        loc = w.get("best_oa_location") or {}
        prim = (w.get("primary_location") or {})
        yield {"api": "openalex", "query": q, "title": (w.get("title") or "").strip(),
               "year": w.get("publication_year"),
               "venue": ((prim.get("source") or {}).get("display_name") or ""),
               "publisher": ((prim.get("source") or {}).get("host_organization_name") or ""),
               "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
               "type": w.get("type") or "",
               "is_oa": bool(w.get("open_access", {}).get("is_oa")),
               "oa_url": loc.get("pdf_url") or loc.get("landing_page_url") or "",
               "cited_by": w.get("cited_by_count", 0),
               "authors": "; ".join((a.get("author") or {}).get("display_name", "")
                                    for a in (w.get("authorships") or [])[:6])}


def crossref(q):
    d = fetch("https://api.crossref.org/works?query=" + urllib.parse.quote(q)
              + "&rows=25&mailto=mgharib@anl.gov", "cr_" + q)
    for w in ((d or {}).get("message") or {}).get("items", []):
        yield {"api": "crossref", "query": q, "title": (w.get("title") or [""])[0].strip(),
               "year": (w.get("issued", {}).get("date-parts") or [[None]])[0][0],
               "venue": (w.get("container-title") or [""])[0],
               "publisher": w.get("publisher", ""), "doi": w.get("DOI", ""),
               "type": w.get("type", ""), "is_oa": False, "oa_url": "",
               "cited_by": w.get("is-referenced-by-count", 0),
               "authors": "; ".join(f"{a.get('given','')} {a.get('family','')}".strip()
                                    for a in (w.get("author") or [])[:6])}


def europepmc(q):
    d = fetch("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
              + urllib.parse.quote(q) + "&format=json&pageSize=25", "ep_" + q)
    for w in ((d or {}).get("resultList") or {}).get("result", []):
        yield {"api": "europepmc", "query": q, "title": (w.get("title") or "").strip(),
               "year": w.get("pubYear"), "venue": w.get("journalTitle") or "",
               "publisher": "", "doi": w.get("doi") or "", "type": w.get("pubType") or "",
               "is_oa": w.get("isOpenAccess") == "Y",
               "oa_url": (f"https://pmc.ncbi.nlm.nih.gov/articles/{w['pmcid']}/"
                          if w.get("pmcid") else ""),
               "cited_by": w.get("citedByCount", 0), "authors": w.get("authorString", "")}


def main():
    hits, seen = [], {}
    for q in QUERIES:
        for gen in (openalex, crossref, europepmc):
            for h in gen(q):
                if not h["title"]:
                    continue
                key = h["doi"].lower() or h["title"].lower()[:90]
                if key in seen:
                    seen[key]["is_oa"] = seen[key]["is_oa"] or h["is_oa"]
                    seen[key]["oa_url"] = seen[key]["oa_url"] or h["oa_url"]
                    seen[key]["publisher"] = seen[key]["publisher"] or h["publisher"]
                    seen[key]["queries"] = "; ".join(
                        sorted(set(seen[key]["queries"].split("; ")) | {q}))
                    continue
                h["queries"] = q
                seen[key] = h; hits.append(h)
    p = R / "results/phase0lr/lit/targeted_hits.json"
    p.write_text(json.dumps(hits, indent=1))
    print(f"{len(hits)} unique works from {len(QUERIES)} queries x 3 APIs -> {p}")
    print(f"open access: {sum(1 for h in hits if h['is_oa'])}")


if __name__ == "__main__":
    main()
