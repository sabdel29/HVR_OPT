"""No gate registry may contradict HEAD (final-closure Part 28).

The gate registry (research/phase0nw/physical_gates.json) and its document
(research/PHYSICAL_Z1_Z2_IMPLEMENTATION_AUDIT.md) are regenerated from artifacts, yet at
commit abba03e they still said that no physical ETM lineage may be created while one
existed, that Z1's network failed to converge after every network had converged, and that
Z1's current was a Phase-0M-R3C placeholder after the physical ledger had replaced it.
The guard below decides, from the artifacts, which claims HEAD makes false, and the
negative test feeds it the REAL stale sentences of abba03e. Rows explicitly marked
HISTORICAL / SUPERSEDED, and the document's "History" subsections, are exempt: they say
what was true at the time.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

R = Path(__file__).resolve().parents[2]
D = R / "research" / "final_closure"
GATES = R / "research" / "phase0nw" / "physical_gates.json"
DOC = R / "research" / "PHYSICAL_Z1_Z2_IMPLEMENTATION_AUDIT.md"

#: verbatim from research/PHYSICAL_Z1_Z2_IMPLEMENTATION_AUDIT.md and
#: research/phase0nw/physical_gates.json at commit abba03e
REAL_STALE = {
    "lineage": "**14 of 115 gates are OPEN.** No physical ETM result lineage may be created "
               "while that number is non-zero.",
    "network": "2 of 4 networks pass: Z2_return, Z2_supply. FAILING: Z1_return at 1.0688 %, "
               "Z1_supply at 1.4101 %.",
    "z1_open": "Z1 is still OPEN because its network fails the 1 % convergence test.",
    "placeholder": "Source: Phase-0M-R3C electronics LOSS + load (PLACEHOLDER). Stays "
                   "SPECIFIED, not IMPLEMENTED, until a physical loss ledger replaces the "
                   "historical placeholder.",
    "placeholder_doc": "Z1's current is **a placeholder**: Phase-0M-R3C electronics LOSS + "
                       "load (PLACEHOLDER).",
    "bracket": "F1 encapsulated (primary) and F2 void both build; bracket not run",
}


def J(p):
    return json.loads(p.read_text()) if p.exists() else None


def state():
    pn = J(D / "package_network.json") or {}
    prov = J(D / "tool_provenance.json") or {"tools": []}
    cb = J(D / "classB_resolution.json") or {}
    runs = {c for g in cb.get("gates", []) if g.get("method") == "runs"
            for c in g.get("cases_run", [])}
    ice = next((t for t in prov["tools"] if t["name"] == "Ansys Icepak"), {})
    return {"lineage": (D / "final_results.json").exists(),
            "networks": bool(pn.get("convergence")) and all(
                c.get("converged") for c in pn["convergence"].values()),
            "ledger": (D / "final_results.json").exists(),
            "icepak": ice.get("status") == "EXECUTED",
            "bracket": {"f2_void", "f1_sidewall_filled"} <= runs}


#: (state key, pattern a current statement may not contain once that state holds)
RULES = [
    ("lineage", r"no physical etm result lineage may be created"),
    ("networks", r"failing: z1_|fails the 1 % convergence|z1 still fails|"
                 r"z1 (?:is still|remains) (?:open|unconverged)|inherits z1's convergence"),
    ("ledger", r"\(placeholder\)|is \*\*a placeholder\*\*|replaces the (?:historical )?"
               r"placeholder"),
    ("icepak", r"icepak[^.|]{0,80}(?:not run|not executed|was not)"),
    ("bracket", r"bracket not run"),
]


def violations(texts, st):
    """texts: iterable of (where, text) current statements."""
    bad = []
    for where, txt in texts:
        low = txt.lower()
        for key, pat in RULES:
            if st.get(key) and re.search(pat, low):
                bad.append(f"{where}: claims '{re.search(pat, low).group(0)}' but {key} "
                           f"holds at HEAD")
    return bad


def registry_texts():
    g = J(GATES)
    for r in g["gates"]:
        ev = str(r.get("evidence", ""))
        if r["status"] == "SUPERSEDED" or ev.startswith("HISTORICAL"):
            continue
        yield r["id"], ev


def doc_texts():
    hist = False
    for i, line in enumerate(DOC.read_text().splitlines(), 1):
        if line.startswith("#"):
            hist = "history" in line.lower()
            continue
        if hist or "HISTORICAL (superseded" in line or "**SUPERSEDED**" in line:
            continue
        yield f"audit doc line {i}", line


def test_registry_and_document_make_no_claim_head_contradicts():
    st = state()
    assert st["lineage"] and st["networks"] and st["ledger"]
    assert violations(registry_texts(), st) == []
    assert violations(doc_texts(), st) == []


def test_guard_catches_the_real_stale_claims_of_abba03e():
    st = {k: True for k, _ in RULES}
    for name, txt in REAL_STALE.items():
        assert violations([(name, txt)], st), f"stale claim not caught: {name}"


def test_historical_rows_stay_exempt():
    """The SUPERSEDED rows keep the old sentences on purpose; the guard must not force
    history to be rewritten."""
    g = J(GATES)
    hist = [r for r in g["gates"] if r["status"] == "SUPERSEDED"]
    assert hist, "the registry lost its superseded history rows"
    assert any("HISTORICAL" in str(r["evidence"]) for r in hist)


def test_direct_feed_architecture_gate_is_closed_on_artifacts():
    g = {r["id"]: r for r in J(GATES)["gates"]}
    r = g["arch.z2_direct_feed_power_path"]
    assert r["status"] == "IMPLEMENTED", r
    fin = J(D / "final_results.json")
    assert all(x["architecture_variant"] == "Z2_DIRECT_FEED" and not x["forbidden_terms"]
               for x in fin if x["arch"] == "Z2")
