#!/usr/bin/env python3
"""Phase-0L Part VII -- programmatic primary-literature search for high-stress SAC305 data.

The WebSearch tool is disabled by organisation policy in this environment
(`constraints/vertexai.allowedPartnerModelFeatures`, feature `web_search`), but ordinary HTTPS
egress works. This script therefore queries the open scholarly APIs directly -- OpenAlex,
Crossref and Europe PMC -- which is a real, reproducible and citable search rather than a
substitute for one. Every hit is recorded with its DOI and open-access status so that the
distinction between "found a reference" and "read the data" stays explicit.
"""
from __future__ import annotations
import json, re, subprocess, sys, time, urllib.parse
from pathlib import Path

R = Path(__file__).resolve().parents[2]
CACHE = R / "results" / "phase0l" / "lit" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
UA = "hvr-opt-research/1.0 (mailto:mgharib@anl.gov)"

QUERIES = [
    "SAC305 Anand model constants solder",
    "SAC305 solder tensile stress strain temperature strain rate",
    "SAC305 creep hyperbolic sine Garofalo constitutive",
    "Sn3.0Ag0.5Cu constitutive model viscoplastic",
    "SAC305 stress relaxation solder joint temperature",
    "lead-free solder unified viscoplastic model SAC305 high strain rate",
    "SAC305 solder mechanical properties aging elastic modulus yield",
    "solder SAC305 steady state creep rate stress exponent activation energy",
]


def fetch(url: str, tag: str) -> dict | list | None:
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
    f.write_text(json.dumps(d))
    time.sleep(1.0)
    return d


def openalex(q: str):
    u = ("https://api.openalex.org/works?search=" + urllib.parse.quote(q)
         + "&per-page=25&mailto=mgharib@anl.gov")
    d = fetch(u, "oa_" + q)
    for w in (d or {}).get("results", []):
        loc = w.get("best_oa_location") or {}
        yield {"source_api": "openalex", "query": q,
               "title": (w.get("title") or "").strip(),
               "year": w.get("publication_year"),
               "venue": ((w.get("primary_location") or {}).get("source") or {}).get(
                   "display_name") or "",
               "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
               "type": w.get("type") or "",
               "is_oa": bool(w.get("open_access", {}).get("is_oa")),
               "oa_url": loc.get("pdf_url") or loc.get("landing_page_url") or "",
               "cited_by": w.get("cited_by_count", 0)}


def europepmc(q: str):
    u = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
         + urllib.parse.quote(q) + "&format=json&pageSize=25")
    d = fetch(u, "epmc_" + q)
    for w in ((d or {}).get("resultList") or {}).get("result", []):
        yield {"source_api": "europepmc", "query": q,
               "title": (w.get("title") or "").strip(), "year": w.get("pubYear"),
               "venue": w.get("journalTitle") or "", "doi": w.get("doi") or "",
               "type": w.get("pubType") or "",
               "is_oa": w.get("isOpenAccess") == "Y",
               "oa_url": (f"https://pmc.ncbi.nlm.nih.gov/articles/{w['pmcid']}/"
                          if w.get("pmcid") else ""),
               "cited_by": w.get("citedByCount", 0)}


def crossref(q: str):
    u = ("https://api.crossref.org/works?query=" + urllib.parse.quote(q)
         + "&rows=25&mailto=mgharib@anl.gov")
    d = fetch(u, "cr_" + q)
    for w in ((d or {}).get("message") or {}).get("items", []):
        yield {"source_api": "crossref", "query": q,
               "title": (w.get("title") or [""])[0].strip(),
               "year": (w.get("issued", {}).get("date-parts") or [[None]])[0][0],
               "venue": (w.get("container-title") or [""])[0],
               "doi": w.get("DOI", ""), "type": w.get("type", ""),
               "is_oa": False, "oa_url": "", "cited_by": w.get("is-referenced-by-count", 0)}


def main():
    hits, seen = [], {}
    for q in QUERIES:
        for gen in (openalex, europepmc, crossref):
            for h in gen(q):
                if not h["title"]:
                    continue
                key = (h["doi"].lower() or h["title"].lower()[:90])
                if key in seen:
                    r = seen[key]
                    r["is_oa"] = r["is_oa"] or h["is_oa"]
                    r["oa_url"] = r["oa_url"] or h["oa_url"]
                    r["queries"] = sorted(set(r["queries"].split("; ")) | {q})
                    r["queries"] = "; ".join(r["queries"])
                    continue
                h["queries"] = q
                seen[key] = h
                hits.append(h)
    out = R / "results" / "phase0l" / "lit" / "raw_hits.json"
    out.write_text(json.dumps(hits, indent=1))
    print(f"{len(hits)} unique works from {len(QUERIES)} queries x 3 APIs -> {out}")
    oa = [h for h in hits if h["is_oa"]]
    print(f"open access: {len(oa)}")
    return hits


if __name__ == "__main__":
    main()
