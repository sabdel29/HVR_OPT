"""Keep research/final_closure/tool_provenance.json consistent with what was executed.

The file is curated (official-source quotes fetched and machine-checked when it was
written). This script applies the deterministic corrections a later state requires and
REFUSES to write a file in which any tool is in an EXECUTED state and a not-executed lane
(or the reverse). It is idempotent.

  * Icepak was executed in the final closure. Its record still carried the lane and
    version text of the earlier "not executed" state.
  * The primary Z2 is direct-fed. Tool roles that described a Z2 package 48 V network now
    name Z1 and the BGA-fed control instead.
  * The meta block named an old HEAD and listed files as untracked that are tracked now.
"""
from __future__ import annotations

import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
F = R / "research" / "final_closure" / "tool_provenance.json"
ICEPAK_ART = "research/final_closure/reference_artifacts/icepak"

NOT_EXECUTED_LANES = {"not_executed", "considered"}


def lane_violations(tools):
    """A tool may not be EXECUTED and sit in a not-executed lane, or the reverse."""
    bad = []
    for t in tools:
        executed = str(t.get("status", "")).upper() == "EXECUTED"
        lane = t.get("lane")
        if executed and lane in NOT_EXECUTED_LANES:
            bad.append(f"{t['name']}: EXECUTED but in lane {lane!r}")
        if not executed and lane not in NOT_EXECUTED_LANES:
            bad.append(f"{t['name']}: {t.get('status')!r} but in lane {lane!r}")
        if executed and "not run" in str(t.get("version_used", "")).lower():
            bad.append(f"{t['name']}: EXECUTED but version_used says 'not run'")
    return bad


def fix(p):
    t = {x["name"]: x for x in p["tools"]}
    ref = json.loads((R / "research/final_closure/reference_cooling_icepak.json").read_text())
    lv = ref["levels"]
    ic = t["Ansys Icepak"]
    ic["lane"] = "reference"
    ic["version_used"] = ("Ansys Electronics Desktop 2026 R1 Icepak (AnsProductVersion 26.1); "
                          "steady laminar conjugate CFD, PyAEDT-driven")
    ic["status_detail"] = (
        "Executed in the final closure: the matched conjugate-CFD benchmark of one cold-plate "
        "channel half-pitch at the production heat load, %d mesh levels (%s cells). Result: "
        "research/final_closure/reference_cooling_icepak.json. Project files: %s (sha256 in "
        "its MANIFEST.json; the solved .aedtresults stay outside the repository). Evidence: "
        "presentation/prelim_hvr/tool_evidence/cooling_icepak/."
        % (len(lv), " / ".join(f"{lv[k]['cells']:,}".replace(",", " ")
                               for k in sorted(lv, key=lambda k: lv[k]["cells"])), ICEPAK_ART))
    ic["mesh_levels"] = {k: {"cells": v["cells"], "solved": v.get("solved")}
                         for k, v in lv.items()}
    ic["result_json"] = "research/final_closure/reference_cooling_icepak.json"
    ic["project_artifacts"] = ICEPAK_ART
    paths = ic.setdefault("evidence_paths", [])
    for q in (f"{ICEPAK_ART}/MANIFEST.json", f"{ICEPAK_ART}/README.md"):
        if q not in paths:
            paths.append(q)
    t["In-house package-network FV solver"]["role_in_study"] = (
        "Production model of Z1's package 48 V network (per-ball current split, effective "
        "resistance, pad drops, the exhaustive ball-count screen) and of the controlled "
        "BGA-fed experiment, where Z1 and Z2_BGA_FED_CONTROL are both forced onto an "
        "identical package-level 48 V feed. The primary, direct-fed Z2 has no package 48 V "
        "network.")
    t["In-house electrical ledger"]["role_in_study"] = (
        "Production electrical model: supplies the tier-by-tier heat map to the CalculiX "
        "thermal solve at every electrothermal iteration and takes the temperatures back; "
        "the 48 V current is solved self-consistently. For the direct-fed Z2 the "
        "package-internal boundary is the HVR input terminals; the external feed is the "
        "swept parameter R_Z2_direct_feed_loop (research/final_closure/direct_feed_crossover.json).")
    t["MOOSE heat_transfer module (heat_transfer-opt)"]["role_in_study"] = (
        "Independent open-source FE reference, never in the production path: (a) 3-D thermal "
        "column of one interior package cell (Z1, Z2) on MOOSE's own hex meshes at two "
        "resolutions, compared with CalculiX; (b) 2-D package-RDL DC conduction solved as the "
        "analogous heat-conduction problem on Gmsh meshes, compared with the in-house FV "
        "network, for Z1's package 48 V RDL and for the BGA-fed control network (the primary "
        "direct-fed Z2 has no package 48 V RDL).")
    # the attach-density unit cells (geom.vr_attach_density) are AEDT Mechanical references
    am = t["AEDT Mechanical (thermal, structural)"]
    for q in ("scripts/reference_tools/aedt_attach_rve.py",
              "research/final_closure/reference_attach_rve.json",
              "presentation/prelim_hvr/tool_evidence/attach_rve/01_geometry_dense_kz_fine.png",
              "presentation/prelim_hvr/tool_evidence/attach_rve/01_geometry_sparse_kz_fine.png"):
        if q not in am["evidence_paths"]:
            am["evidence_paths"].append(q)
    tail = (" Attach: explicit unit cells of the VR-to-substrate attach at both published "
            "densities (k_z, k_xy) against the homogenised card.")
    if tail not in am["role_in_study"]:
        am["role_in_study"] += tail
    pa = t["PyAEDT (ansys.aedt.core)"]
    if "scripts/reference_tools/aedt_attach_rve.py" not in pa["evidence_paths"]:
        pa["evidence_paths"].append("scripts/reference_tools/aedt_attach_rve.py")
    ed = t["Ansys Electronics Desktop 2026 R1"]
    ed["role_in_study"] = ed["role_in_study"].replace(
        "Icepak is licensed but its matched benchmark was not run.",
        "Icepak is licensed and ran the matched cold-plate benchmark "
        "(research/final_closure/reference_cooling_icepak.json).")
    m = p["meta"]
    m["repo_head"] = "the commit that carries this file (a file cannot name its own SHA)"
    m["untracked_evidence_paths"] = []
    m["revised"] = ("2026-10-28: Icepak lane/version/status fields made consistent with its "
                    "execution; Z2 roles updated for the direct-fed architecture; meta block")
    return p


def main():
    p = fix(json.loads(F.read_text()))
    bad = lane_violations(p["tools"])
    if bad:
        raise SystemExit("refusing to write an inconsistent provenance file:\n" + "\n".join(bad))
    F.write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    print("tool_provenance.json consistent:", len(p["tools"]), "tools")


if __name__ == "__main__":
    main()
