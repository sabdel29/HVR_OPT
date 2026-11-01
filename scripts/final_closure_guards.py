"""Claim guards shared by the rebuild pipeline and the test suite.

Each guard takes TEXT (and the artifact it must agree with) and returns a list of
violations, so a test can feed it the real file and, negatively, the real offending text
that a past defect shipped -- never a paraphrase of it.
"""
from __future__ import annotations

import re

OBS_ORDER = ("P_loss_package_internal_w", "P_loss_platform_inclusive_w", "T_max_C",
             "die_warpage_pv_um", "du_c_um", "d_eps_in_per_cycle")
FORBIDDEN_MESH = ("mesh-converged", "mesh converged", "mesh- and cycle-converged",
                  "mesh and cycle converged", "cycle-converged")


def decision_table(md):
    """{scenario: [cells in OBS_ORDER]} from FINAL_PAPER_DECISION.md."""
    sec = md.split("## Architecture ordering per scenario", 1)
    if len(sec) < 2:
        return {}
    rows = {}
    for line in sec[1].split("\n## ", 1)[0].splitlines():
        if line.startswith("| HV_S"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows[cells[0]] = cells[1:]
    return rows


def decision_vs_ordering(md, ordering):
    """Every ordering cell and robustness claim of the decision report must equal
    ordering.json. Returns the mismatches."""
    od = ordering["orderings"]
    bad = []
    rows = decision_table(md)
    if not rows:
        return ["decision report has no ordering table"]
    for s, cells in rows.items():
        for k, cell in zip(OBS_ORDER, cells):
            want = od[k]["per_scenario"].get(s, "n/a")
            if cell != want:
                bad.append(f"{s} {k}: report says {cell!r}, ordering.json says {want!r}")
    rob = md.split("## Robustness", 1)[1].split("\n## ", 1)[0] if "## Robustness" in md else ""
    if "ORDERING HOLDS IN EVERY SCENARIO" in rob:
        for k in OBS_ORDER:
            if not od[k].get("robust_across_scenarios") and f"`{k}`" in rob and \
                    "ORDERING HOLDS IN EVERY SCENARIO" in rob.split(f"`{k}`", 1)[1].split("\n")[0]:
                bad.append(f"{k}: robustness claimed but ordering.json says not robust")
    if re.search(r"\[[^\]]*'n/a'[^\]]*\]", rob):
        bad.append("'n/a' counted as a favoured architecture")
    t = od["T_max_C"]["per_scenario"].get("HV_S0")
    if t == "unresolved" and "no thermal architecture ranking is drawn for HV-S0" not in md:
        bad.append("HV-S0 thermal ordering is unresolved but the required sentence is absent")
    return bad


def hv_s0_thermal_claims(text, ordering):
    """Sentences that rank Z1/Z2 by temperature at HV-S0 while ordering.json says the
    HV-S0 thermal gap is unresolved."""
    od = ordering["orderings"]["T_max_C"]["per_scenario"]
    if od.get("HV_S0") != "unresolved":
        return []
    out = []
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    for sent in re.split(r"(?<=[.;!?])\s+", flat):
        s = sent.lower()
        if not re.search(r"hv[-_ ]?s0", s):
            continue
        if not re.search(r"peak temperature|t_?max|thermal|temperature|cooler|hotter", s):
            continue
        if re.search(r"z[12] (is |runs |stays )?(lower|cooler|hotter|higher)", s) and not \
                re.search(r"unresolved|within the measured|no thermal architecture ranking|"
                          r"not resolved|cannot be ranked", s):
            out.append(sent.strip()[:200])
    return out


def mesh_wording_violations(text, local_study, policy):
    """'mesh-converged' and its variants are allowed only if EVERY policy case passed the
    declared convergence rule (A)."""
    cases = [f"{a}_{s}" for a, s in policy["cases"]]
    st = [((local_study or {}).get("cases") or {}).get(k, {}).get("status") for k in cases]
    if st and all(x == "converged" for x in st):
        return []
    low = re.sub(r"\s+", " ", text.lower().replace("\\-", "").replace("~", " "))
    return [w for w in FORBIDDEN_MESH if w in low]


def na_never_favourable(ordering):
    """'not rankable' / 'unresolved' / 'n/a' never counts for either architecture."""
    bad = []
    for k, o in ordering["orderings"].items():
        per = o.get("per_scenario", {})
        ranked = {s: v for s, v in per.items() if v.endswith("lower")}
        fav = sorted({v.split()[0] for v in ranked.values()})
        if sorted(o.get("favoured") or []) != fav:
            bad.append(f"{k}: favoured {o.get('favoured')} != ranked {fav}")
        if any(x not in ("Z1", "Z2") for x in (o.get("favoured") or [])):
            bad.append(f"{k}: non-architecture entry in favoured: {o.get('favoured')}")
        if o.get("robust_across_scenarios") and len(ranked) != len(per):
            bad.append(f"{k}: robust across scenarios while some scenario is not ranked")
    return bad


def inadmissible_ranking_claims(text, ordering):
    """No text may rank Z1/Z2 inside a scenario ordering.json marks inadmissible (a critical
    joint at or above the solder melting onset), nor claim an ordering 'in every (named)
    scenario' while such a scenario exists: that operating point is an infeasibility result,
    not an operating comparison (brief Part 5)."""
    sc = ordering.get("scenario_classes", {})
    inad = [s for s, c in sc.items() if c.get("inadmissible")]
    if not inad:
        return []
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    bad = [m.group(0).strip()[:200] for m in re.finditer(
        r"[^.]*\b(?:lower|less|cooler|holds)\b[^.]*?\bin every (?:named )?scenario\b"
        r"(?! (?:for which|that admits))", flat)]
    for s in inad:
        lab = s.replace("_", "-")
        bad += [m.group(0)[:200] for m in re.finditer(
            rf"\b{lab}:? (?:Z1|Z2) lower|(?:Z1|Z2)(?: has)? lower [^.]*?\b{lab}\b, where the gap",
            flat)]
    return bad


#: a Z1/Z2 loss ranking; it must carry its boundary in the same sentence or bullet
_LOSS_RANK = re.compile(
    r"(?:\b(?:Z1|Z2|embedded|backside)\b[^.;\n]{0,60}?\b(?:lower|less)\s+(?:electrical\s+)?"
    r"loss\b|\bloss(?:es)?\b\s*[:=-]\s*(?:Z1|Z2)\s+lower\b|\b(?:Z1|Z2)\s+lower\s+loss\b|"
    r"\b(?:Z1|Z2|backside|embedded)\b[^.;\n]{0,40}?\bdissipates?\s+less\b)", re.I)
_BOUNDARY = re.compile(r"package[- ]internal|internal|inside the (?:declared )?package|"
                       r"platform|R\^?\{?\*|R\*|feed|boundary|HVR input", re.I)


def generic_loss_claims(text):
    """Sentences or bullets that rank Z1/Z2 by 'loss' without saying WHICH loss: the
    package-internal loss (from each architecture's own input boundary) and the platform-
    inclusive loss (with Z2's unsourced external feed) are different quantities, and a bare
    'Z2 has lower loss' reads as if that feed were lossless."""
    flat = re.sub(r"<[^>]+>", " ", text)
    bad = []
    for piece in re.split(r"(?<=[.;])\s+|\n+", flat):
        if _LOSS_RANK.search(piece) and not _BOUNDARY.search(piece):
            bad.append(" ".join(piece.split())[:200])
    return bad
