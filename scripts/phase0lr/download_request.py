#!/usr/bin/env python3
"""Phase-0L-R Part 6 -- the institutional-access escalation file.

The user has institutional IEEE/journal access. Papers Claude cannot fetch are therefore
ACCESS-GATED, not absent, and must be listed with enough metadata to be pulled in one sitting.
Every field here comes from the search APIs or from a retrieved full text -- nothing is guessed.
"""
from __future__ import annotations
import json, re
from pathlib import Path

R = Path(__file__).resolve().parents[2]
HITS = json.load(open(R / "results/phase0lr/lit/targeted_hits.json"))
BY_DOI = {h["doi"].lower(): h for h in HITS if h.get("doi")}

# (doi, priority, why it matters, what is needed from it)
WANTED = [
 ("10.2139/ssrn.7320629", "P0",
  "Title promises thermoviscoplastic characterisation of SAC305 over WIDE ranges of temperature "
  "and rate -- exactly the axis the project is missing. Unpaywall reports it OPEN, but SSRN "
  "returns HTTP 403 to scripted fetches, so a browser download closes this in one click.",
  "Every stress-strain / relaxation curve with its temperature and strain rate; any fitted "
  "constitutive constants and the stated validity domain."),
 ("10.2139/ssrn.5288590", "P0",
  "Temperature- AND stress-dependent creep of SAC305 from tensile testing. This is the exact "
  "missing measurement: SAC305 in the creep-rate regime. Unpaywall reports it OPEN; SSRN 403s.",
  "The creep-rate table (T, sigma, rate), the stress exponent(s) and activation energy, and the "
  "stress range actually tested."),
 ("10.1109/impact.2010.5699529", "P0",
  "Stress-strain relationship of SAC305 at ELEVATED temperatures. Directly supplies the "
  "temperature-dependent flow curves the Anand/Chaboche halves of the card currently inherit "
  "through two model layers.",
  "Stress-strain curves per temperature and rate; tabulated yield and UTS versus temperature."),
 ("10.1108/ssmt-08-2016-0017", "P0",
  "SAC305 deformation under VARIED tensile strain rates -- multi-rate data is what identifies "
  "the rate-sensitivity exponent that Anand fits are currently non-identifiable in.",
  "Stress-strain curves at each rate and temperature; any fitted rate-sensitivity parameter."),
 ("10.1109/ectc.2016.345", "P1",
  "Cyclic stress-strain of SAC305 with aging, temperature and strain rate as explicit variables. "
  "Cyclic data would let the Chaboche half be calibrated directly instead of from synthetic "
  "Anand-generated curves.",
  "Hysteresis loops per temperature/rate; extracted kinematic/isotropic hardening constants."),
 ("10.1109/itherm45881.2020.9190596", "P1",
  "Anand parameters for SAC305 at EXTREME HIGH temperature -- would extend the plasticity domain "
  "above the present 122 C ceiling, which is the limit that makes the 110-150 C experiment "
  "profile severely extrapolated.",
  "The nine Anand constants and the temperature range they were fitted over."),
 ("10.1115/ipack2020-2690", "P1",
  "Anand parameters determined from CREEP testing of SAC305 joints. Anand-from-creep is the "
  "bridge between the tensile-rate and creep-rate regimes that no retrieved source spans.",
  "The nine Anand constants, the creep test matrix (T, sigma, duration) and the fit residuals."),
 ("10.1109/itherm.2017.7992639", "P1",
  "Evolution of cyclic stress-strain and constitutive behaviour of SAC305.",
  "Constitutive constants and the temperature/rate grid they were fitted on."),
 ("10.1109/tcpmt.2012.2227481", "P1",
  "Constitutive modelling of JOINT-SCALE SAC305 shear samples. Joint-scale rather than bulk "
  "matters because the current model applies bulk constants to a 25 um joint layer.",
  "Joint-scale constitutive constants and the size/microstructure of the samples."),
 ("10.1109/itherm.2014.6892272", "P2",
  "Aging effects on the SAC305 Anand model. Aging is unmodelled in this framework; this bounds "
  "how much it could matter.",
  "Anand constants before and after aging."),
 ("10.1016/j.microrel.2016.03.014", "P2",
  "High strain-rate constitutive behaviour of SAC105 and SAC305. Impact-rate work is explicitly "
  "OUT of the creep framework, but it bounds the elastic/plastic response at the top of the "
  "rate axis.",
  "Elastic modulus and yield versus temperature; use for bounding only, not for creep."),
]


def main() -> int:
    L = ["# High-stress SAC305 primary sources — institutional download request", "",
         "**Phase 0L-R, Part 6.**", "",
         "Phase 0L concluded that no suitable high-stress SAC305 data was retrievable and, being "
         "careful, did not conclude that none exists. Phase 0L-R re-searched on axes other than "
         "the word *creep* (multi-rate tensile, stress relaxation, Anand and Chaboche "
         "calibrations) and found a substantial, directly relevant corpus. Almost all of it is "
         "behind IEEE, ASME, Emerald or SSRN access that refuses scripted retrieval.", "",
         "> **HIGH-STRESS CONSTITUTIVE CLOSURE IS ACCESS-GATED, NOT EVIDENCE-NEGATIVE.**", "",
         "The user has institutional access. Each entry below names exactly what is needed from "
         "the PDF, so nothing has to be read twice.", "",
         "One search result was retrieved and has already changed the phase result: **Yamin et "
         "al. 2025** (open access, Jurnal Teknologi) supplied a well-identified SAC305 Anand "
         "parameter set which re-admits the Anand family that Phase 0L had rejected. That is "
         "direct evidence that the remaining gap is retrieval, not existence.", ""]
    n0 = n1 = 0
    for pri in ("P0", "P1", "P2"):
        block = [w for w in WANTED if w[1] == pri]
        if not block:
            continue
        L += [f"## {pri} — " + {"P0": "potentially closes the constitutive gap",
                                "P1": "materially useful",
                                "P2": "background / bounding"}[pri], ""]
        for doi, _p, why, need in block:
            h = BY_DOI.get(doi.lower(), {})
            n0 += pri == "P0"; n1 += pri == "P1"
            L += [f"### {h.get('title') or '(title not in API cache)'}", "",
                  f"| field | value |", "|---|---|",
                  f"| authors | {h.get('authors') or 'not in API cache'} |",
                  f"| year | {h.get('year') or '?'} |",
                  f"| venue | {h.get('venue') or '?'} |",
                  f"| publisher | {h.get('publisher') or '?'} |",
                  f"| DOI | `{doi}` |",
                  f"| link | https://doi.org/{doi} |",
                  f"| open access per API | {'yes' if h.get('is_oa') else 'no'} |",
                  f"| Claude's retrieval result | refused (403/paywall) |", "",
                  f"**Why it matters.** {why}", "",
                  f"**What is needed from the PDF.** {need}", ""]
    L += ["## Coverage this would buy", "",
          "| axis | current coverage | after P0 |", "|---|---|---|",
          "| alloy | creep half is Sn3.9Ag0.6Cu | SAC305 throughout |",
          "| temperature | creep 45–150 °C; plasticity −40…122 °C | plasticity extended above 122 °C |",
          "| stress | 7.51–15.92 MPa measured | tensile flow levels, roughly 15–50 MPa |",
          "| strain rate | 1e−9…8e−7 (wrong alloy) or 1e−5…1e−3 (right alloy) | both regimes on SAC305 |",
          "",
          f"**{n0} P0 and {n1} P1 papers are behind institutional access.** Retrieving the four "
          "P0 entries would, on their stated scope, let the creep card be refitted on SAC305 in "
          "the package's own stress regime and would let Phase 0L-R's verdict be revisited.", ""]
    p = R / "results/phase0lr/HIGH_STRESS_PAPER_DOWNLOAD_REQUEST.md"
    p.write_text("\n".join(L))
    print(f"wrote {p}  ({n0} P0, {n1} P1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
