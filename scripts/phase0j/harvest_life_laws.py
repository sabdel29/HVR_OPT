#!/usr/bin/env python3
"""Phase-0J Sec.3 -- primary-literature harvest for SAC305 fatigue / life laws.

OpenAlex `filter=title_and_abstract.search:(...)` is used, NOT the loose `search=` parameter:
the loose one matches full text and returns thousands of irrelevant hits. Crossref is used as
an independent second index so the harvest is not a single vendor's view.
"""
from __future__ import annotations
import csv, json, time, urllib.parse, urllib.request
from pathlib import Path

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0j"
MAIL = "etm-dvpd-research@example.org"          # OpenAlex polite pool

QUERIES = [
    # -- strain-range family
    'SAC305 AND (Coffin-Manson OR "Coffin Manson")',
    '("SnAgCu" OR "SAC305" OR "SAC 305") AND "thermal cycling" AND ("fatigue life" OR "cycles to failure")',
    'Engelmaier AND solder AND fatigue',
    '"solder joint" AND "strain range" AND "fatigue life" AND "lead-free"',
    # -- energy family
    'Darveaux AND solder AND (crack OR "energy density" OR life)',
    '"strain energy density" AND "solder joint" AND (fatigue OR life)',
    'SAC305 AND "energy" AND "fatigue life" AND "thermal cycling"',
    '"inelastic work" AND solder AND fatigue',
    # -- creep / viscoplastic damage
    '"creep strain" AND "solder joint" AND "fatigue life" AND lead-free',
    'Syed AND solder AND (creep OR energy) AND life',
    # -- experimental calibration
    'SAC305 AND "accelerated thermal cycling" AND Weibull',
    '"lead-free" AND BGA AND "thermal cycling" AND "characteristic life"',
    '"flip chip" AND (C4 OR microbump) AND "solder" AND "fatigue life" AND lead-free',
    'SAC305 AND Anand AND "thermal cycling" AND "fatigue"',
    '"solder joint reliability" AND "acceleration factor" AND "dwell time"',
]


def openalex(q: str, per: int = 60) -> list[dict]:
    u = ("https://api.openalex.org/works?per-page=%d&mailto=%s&filter=%s"
         % (per, MAIL, urllib.parse.quote(f"title_and_abstract.search:({q})", safe=":()")))
    try:
        with urllib.request.urlopen(u, timeout=45) as r:
            d = json.load(r)
    except Exception as e:
        print(f"    openalex FAILED: {type(e).__name__}"); return []
    out = []
    for w in d.get("results", []):
        inv = w.get("abstract_inverted_index") or {}
        ab = " ".join(sorted(inv, key=lambda k: inv[k][0]))[:1200] if inv else ""
        pl = (w.get("primary_location") or {})
        out.append({"source": "openalex", "query": q, "id": w.get("id", ""),
                    "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                    "title": (w.get("title") or "").replace("\n", " "),
                    "year": w.get("publication_year") or "",
                    "cited_by": w.get("cited_by_count", 0),
                    "venue": ((pl.get("source") or {}).get("display_name") or ""),
                    "oa": (w.get("open_access") or {}).get("is_oa", False),
                    "oa_url": (w.get("best_oa_location") or {}).get("pdf_url") or "",
                    "type": w.get("type", ""), "abstract": ab})
    return out


def crossref(q: str, rows: int = 40) -> list[dict]:
    u = ("https://api.crossref.org/works?rows=%d&mailto=%s&query.bibliographic=%s"
         % (rows, MAIL, urllib.parse.quote(q)))
    try:
        with urllib.request.urlopen(u, timeout=45) as r:
            d = json.load(r)
    except Exception as e:
        print(f"    crossref FAILED: {type(e).__name__}"); return []
    out = []
    for w in d.get("message", {}).get("items", []):
        ti = (w.get("title") or [""])[0].replace("\n", " ")
        yr = ((w.get("issued") or {}).get("date-parts") or [[None]])[0][0] or ""
        out.append({"source": "crossref", "query": q, "id": w.get("URL", ""),
                    "doi": w.get("DOI", ""), "title": ti, "year": yr,
                    "cited_by": w.get("is-referenced-by-count", 0),
                    "venue": (w.get("container-title") or [""])[0],
                    "oa": "", "oa_url": "", "type": w.get("type", ""),
                    "abstract": (w.get("abstract") or "")[:1200]})
    return out


def main() -> int:
    rows, seen = [], set()
    for q in QUERIES:
        print(f"  {q[:70]}")
        for fn in (openalex, crossref):
            got = fn(q)
            new = 0
            for r_ in got:
                k = (r_["doi"] or r_["title"]).lower().strip()
                if k and k not in seen:
                    seen.add(k); rows.append(r_); new += 1
            print(f"    {fn.__name__:10} {len(got):3} returned, {new:3} new")
            time.sleep(0.4)
    f = OUT / "life_law_search_raw.csv"
    with f.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {f}  ({len(rows)} unique works from {len(QUERIES)} queries x 2 indices)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
