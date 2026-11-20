"""Attachment-density and loss-boundary closure: the twelve permanent guards of the final
brief (Part 29). Every guard that scans text is also run NEGATIVELY on the real offending
text a past version shipped (commit 4cf83c7 and the archived scope), so a guard that
silently stops matching fails here."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
D = R / "research" / "final_closure"
#: the results root in force (a campaign root through ETM_RESULTS_ROOT), as the attach study's
#: producer reads and writes it; D stays the frozen tree the round-2 texts were made from
RD = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure"
sys.path.insert(0, str(R / "scripts"))
sys.path.insert(0, str(R / "scripts" / "phase0nw"))
import final_closure_guards as G                                    # noqa: E402

TEX = R / "manuscript" / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex"
DECK = R / "presentation" / "prelim_hvr"
STUDY = RD / "vr_attach_density_study.json"

#: the active-scope sentence the pre-direct-feed scope used for Z2 (4cf83c7), and the
#: wording the final brief names
SUPERSEDED = ("48 V reaches them laterally through the package RDL",
              "48 V reaches Z2 laterally through the package RDL")
#: the exact generic loss rankings commit 4cf83c7 shipped (ordering.json statement, deck)
STALE_LOSS = ("Z2 has lower loss in every scenario for which a valid two-architecture "
              "comparison can be made;",
              "Electrical loss: Z2 has lower loss in every scenario for which a valid "
              "two-architecture comparison can be made;",
              "Loss: Z2 lower;", "There Z2 dissipates less;",
              "with the electrically minimal field (64 per cell) Z1 dissipates less.")
#: history: archived or superseded material, which may quote what it supersedes
HISTORY = ("research/final_closure/archive/", "research/final_closure/superseded",
           "results/archive/", "Scalable_Integrated_VR")


def J(name):
    f = D / name
    assert f.exists(), f"{name} not generated"
    return json.loads(f.read_text())


def study():
    assert STUDY.exists(), "vr_attach_density_study.json not generated"
    return json.loads(STUDY.read_text())


def _study_design(st):
    """The design an attach study was drawn on (TCPMT round 3: the study records it); None for
    the frozen round-2 study, the 49-cell lineage's (5.61-mm^2 cell)."""
    return (st.get("design") or {}).get("design")


def _require_design_in_force(st):
    """Model-vs-artifact checks need the study of the design in force (the code draws the
    lattice on the design record's cell; the frozen research/ study is the 49-cell lineage's)."""
    import design_record as DR
    if _study_design(st) != DR.name():
        pytest.skip("the attach study in the results root is of another design than the record "
                    "in force (frozen round-2 artifact): run with ETM_RESULTS_ROOT at a root "
                    "regenerated for the design")


def _tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=R, capture_output=True, text=True,
                         check=True).stdout.split()
    keep = (".md", ".tex", ".html", ".json", ".csv", ".txt", ".svg", ".yaml", ".bib")
    return [R / f for f in out if f.endswith(keep) and not f.startswith(HISTORY)]


# ------------------------------------------------------------------ 1
def test_primary_z2_has_no_48v_bga_or_rdl_term():
    spec = J("z2_direct_feed_architecture.json")["architectures"]["Z2"]
    forbidden = set(spec["forbidden_ledger_terms"])
    assert {"P_BGA_supply", "P_BGA_return", "P_pkg_RDL_HV_supply",
            "P_pkg_RDL_HV_return"} <= forbidden
    import final_closure_physical_etm as E
    for f in J("final_results.json"):
        if f["arch"] != "Z2":
            continue
        assert f["architecture_variant"] == "Z2_DIRECT_FEED"
        assert not f.get("forbidden_terms")
        rows = json.loads(E.case_path("Z2", f["scenario"]).read_text())["ledger_rows"]
        hit = [r["term"] for r in rows if r["term"] in forbidden and r["P_w"] != 0.0]
        assert not hit, (f["scenario"], hit)
    # the attach-density variants keep the direct feed: no package 48 V term either
    for v in ("attach_dense", "attach_sparse", "attach_sparse_stiff"):
        c = json.loads((D / "sensitivity" / f"etm_Z2_HV_S0__{v}.json").read_text())
        assert not [r["term"] for r in c["ledger_rows"] if r["term"] in forbidden], v


# ------------------------------------------------------------------ 2
def _brute_force_axis(side, p, d):
    """Sites of a centred square grid of pitch p whose bump keeps the inter-cell clearance
    (p - d) / 2 to the cell edge, counted by enumeration over both registrations."""
    lim = side / 2.0 - (p - d) / 2.0 - d / 2.0
    best = 0
    for off in (0.0, p / 2.0):
        n = sum(1 for k in range(-int(side / p) - 2, int(side / p) + 3)
                if abs(off + k * p) <= lim + 1e-9)
        best = max(best, n)
    return best


def test_attach_lattice_count_matches_pitch_diameter_and_cell():
    st = study()
    import final_closure_vr_attach as VA
    for name, c in st["cases"].items():
        side = c["cell_side_um"]
        if _study_design(st) is None:           # the round-2 lineage: the 5.61-mm^2 cell
            assert side == pytest.approx(math.sqrt(5.61) * 1e3)
        n = _brute_force_axis(side, c["pitch_um"], c["d_um"])
        assert c["n_per_axis"] == n, name
        assert c["n_total"] == n * n, name
        metal = n * n * math.pi * c["d_um"] ** 2 / 4.0
        assert c["metal_area_um2"] == pytest.approx(metal, rel=1e-12)
        assert c["area_fraction"] == pytest.approx(metal / side ** 2, rel=1e-12)
        assert c["edge_clearance_um"] >= c["edge_rule_um"] - 1e-9
        # the stored study is the code's output on the study's own cell, every mesh cell agrees
        L = VA.lattice(VA.CASES[name], side_um=side)
        assert (L["n_vdd"], L["n_gnd"]) == (c["n_vdd"], c["n_gnd"]), name
        assert c["all_cells"]["n_cells"] == st.get("n_vr", 49)
        assert c["all_cells"]["per_cell"] == [c["n_total"], c["n_vdd"], c["n_gnd"]]
    # the sparse published geometry really is sparser: a different lattice, not a rescale
    assert st["cases"]["sparse"]["n_per_axis"] < st["cases"]["dense"]["n_per_axis"]
    # model vs artifact: the study of the design in force is drawn on that design's cell
    _require_design_in_force(st)
    assert st["n_vr"] == VA.N_VR
    for name, c in st["cases"].items():
        assert c["cell_side_um"] == pytest.approx(VA.CELL_SIDE_UM), name
        L = VA.lattice(VA.CASES[name])
        assert (L["n_vdd"], L["n_gnd"]) == (c["n_vdd"], c["n_gnd"]), name


# ------------------------------------------------------------------ 3
def test_vdd_and_gnd_counts_follow_the_checkerboard_rule():
    st = study()
    assert "i + j is even" in st["allocation_rule"]
    import final_closure_vr_attach as VA
    for name, c in st["cases"].items():
        n = c["n_per_axis"]
        vdd = sum(1 for i in range(n) for j in range(n) if (i + j) % 2 == 0)
        assert (c["n_vdd"], c["n_gnd"]) == (vdd, n * n - vdd), name
        assert c["all_cells"]["total_vdd"] == st.get("n_vr", 49) * vdd
    # the counts the ETM variants actually carried in their ledgers (same results root)
    for v in ("attach_dense", "attach_sparse"):
        c = json.loads((RD / "sensitivity" / f"etm_Z2_HV_S0__{v}.json").read_text())
        rows = {r["term"]: r for r in c["ledger_rows"]}
        n_case = st["cases"][v.removeprefix("attach_")]
        assert f"{n_case['n_vdd']} " in rows["P_VR_attach_VDD"]["conductor"]
        assert f"{n_case['n_gnd']} " in rows["P_VR_attach_GND"]["conductor"]
    # model vs artifact: the ledger spec of the design in force installs the study's counts
    _require_design_in_force(st)
    for name, c in st["cases"].items():
        sp = VA.ledger_spec(VA.CASES[name])
        assert (sp["n_vdd"], sp["n_gnd"]) == (c["n_vdd"], c["n_gnd"]), name


# ------------------------------------------------------------------ 4
def test_attach_effective_properties_change_with_density():
    st = study()
    dn, sp = st["cases"]["dense"], st["cases"]["sparse"]
    assert sp["area_fraction"] < dn["area_fraction"]
    assert sp["k_z_W_mK"] < dn["k_z_W_mK"] and sp["k_xy_W_mK"] < dn["k_xy_W_mK"]
    assert sp["mech_bound_B"]["E_MPa"] < dn["mech_bound_B"]["E_MPa"]
    assert sp["electrical"]["P_attach_total_w"] > dn["electrical"]["P_attach_total_w"]
    # ... and the variants were really solved with those cards and ledgers (a degree of
    # freedom pinned to its baseline would leave the solved cases identical)
    cases = {v: json.loads((RD / "sensitivity" / f"etm_Z2_HV_S0__{v}.json").read_text())
             for v in ("attach_dense", "attach_sparse")}
    att = {v: sum(r["P_w"] for r in c["ledger_rows"] if r["term"].startswith("P_VR_attach"))
           for v, c in cases.items()}
    assert att["attach_sparse"] > att["attach_dense"] * 1.5
    assert cases["attach_sparse"]["thermal"]["T_max_C"] != cases["attach_dense"]["thermal"]["T_max_C"]
    for v, c in cases.items():
        assert c["et_converged"], v
        assert c["variant"]["gates"] == ["geom.vr_attach_density"]
    # the column-stiffened bound records the card its mesh carried: the sparse lattice's
    stiff = json.loads((RD / "sensitivity" / "etm_Z2_HV_S0__attach_sparse_stiff.json").read_text())
    card = stiff["materials"]["vr_attach_card"]
    assert card["k"] == pytest.approx(sp["k_z_W_mK"], rel=1e-9)
    assert card["E"] == pytest.approx(sp["mech_bound_B"]["E_MPa"], rel=1e-9)


# ------------------------------------------------------------------ 5
_N3042 = re.compile(r"(?<![\d.])3042(?![\d.])")


def _hardcoded_count(text):
    return [ln for ln in text.splitlines() if _N3042.search(ln)]


def test_no_hard_coded_3042_attach_count():
    srcs = subprocess.run(["git", "ls-files", "scripts"], cwd=R, capture_output=True,
                          text=True, check=True).stdout.split()
    for f in srcs:
        if f.endswith(".py") and (R / f).exists():
            assert _hardcoded_count((R / f).read_text()) == [], f
    # NEGATIVE: the scanner sees a literal count
    assert _hardcoded_count('n = 3042  # bumps per rail')
    assert not _hardcoded_count("T = 0.8709251940483042")
    # every user-facing count is the real lattice's, derived afresh -- on the cell the texts
    # describe: these are the frozen round-2 manuscript and deck, so the frozen study's cell
    # (TCPMT round 3 draws the code's lattice on the design record's cell)
    import final_closure_vr_attach as VA
    side = json.loads((D / "vr_attach_density_study.json").read_text())["cases"]
    n = VA.lattice(VA.CASES["dense"], side_um=side["dense"]["cell_side_um"])["n_vdd"]
    mac = (R / "manuscript" / "final_lineage_macros.tex").read_text()
    assert re.search(r"\\newcommand\{\\AttachNbump\}\{(\d+)\}", mac).group(1) == str(n)
    assert re.search(r"\\newcommand\{\\AttSparseNvdd\}\{(\d+)\}", mac).group(1) == str(
        VA.lattice(VA.CASES["sparse"], side_um=side["sparse"]["cell_side_um"])["n_vdd"])
    html = (DECK / "index.html").read_text()
    assert re.search(r"pillars per cell, VDD \+ GND</td><td class='num'>(?:<[^>]+>)*(\d+)",
                     html).group(1) == str(n)


# ------------------------------------------------------------------ 6
def test_direct_feed_crossover_is_regenerated_from_the_current_cases():
    import final_closure_physical_etm as E
    import final_closure_direct_feed as DF
    import final_closure_results as FR
    cx = J("direct_feed_crossover.json")["scenarios"]
    s0 = cx["HV_S0"]
    for a, k in (("Z1", "P_Z1_internal_w"), ("Z2", "P_Z2_internal_w")):
        assert s0[k] == json.loads(E.case_path(a, "HV_S0").read_text())["P_loss_w"]
    for k in ("advantage_at_zero_feed_w", "I_48_rms_a", "P_feed_per_mohm_w", "R_star_mohm",
              "efficiency_Z2_at_R_star"):
        assert isinstance(s0[k], float), k
    assert s0["P_feed_per_mohm_w"] == pytest.approx(s0["I_48_rms_a"] ** 2 * 1e-3)
    # at R* both architectures dissipate the same platform-to-load loss
    assert s0["efficiency_Z2_at_R_star"] == pytest.approx(s0["efficiency_Z1"], rel=1e-9)
    # R* is recomputed, not stored: the current Z2 state and Z1 loss give the stored value,
    # and a different Z2 internal loss (here: Z1 reference moved by its gap) moves it
    c2 = json.loads(E.case_path("Z2", "HV_S0").read_text())
    temps = DF.converged_temps(c2)
    assert DF.crossover("HV_S0", temps, s0["P_Z1_internal_w"]) * 1e3 == pytest.approx(
        s0["R_star_mohm"], rel=1e-6)
    assert DF.crossover("HV_S0", temps, s0["P_Z1_internal_w"] - 0.5) * 1e3 < s0["R_star_mohm"]
    assert FR.crossover_stale() == []
    # the attach-density sensitivity of R* uses each variant's own state
    ad = s0["attach_density_R_star"]
    for name in ("dense", "sparse"):
        v = json.loads((D / "sensitivity" / f"etm_Z2_HV_S0__attach_{name}.json").read_text())
        assert ad[name]["P_Z2_internal_w"] == v["P_loss_w"]
    assert ad["sparse"]["R_star_mohm"] < ad["dense"]["R_star_mohm"]


# ------------------------------------------------------------------ 7
def _user_texts():
    out = {"manuscript": TEX.read_text(), "decision": (D / "FINAL_PAPER_DECISION.md").read_text(),
           "scope": (D / "FINAL_PAPER_SCOPE.md").read_text()}
    for f in ("index.html", "SPEAKER_NOTES.md"):
        if (DECK / f).exists():
            out[f] = (DECK / f).read_text()
    od = J("ordering.json")["orderings"]
    out["ordering statements"] = "\n".join(o.get("statement", "") for o in od.values())
    return out


def test_no_generic_lower_loss_claim_without_its_boundary():
    for name, t in _user_texts().items():
        assert G.generic_loss_claims(t) == [], name
    # NEGATIVE: every real stale ranking 4cf83c7 shipped is caught
    for t in STALE_LOSS:
        assert G.generic_loss_claims(t), t
    # ... and the bounded forms are not
    for t in ("Package-internal loss: Z2 lower in HV-S0;",
              "Z2 dissipates less inside the package, an advantage it keeps only while R* "
              "is not exceeded;",
              "Platform-inclusive: Z2 lower only below R* = 1.77 mOhm;"):
        assert not G.generic_loss_claims(t), t
    od = J("ordering.json")["orderings"]
    assert "P_loss_w" not in od
    assert od["P_loss_platform_inclusive_w"]["favoured"] == []


# ------------------------------------------------------------------ 8
def _superseded_hits(text):
    flat = " ".join(text.split()).lower()
    return [p for p in SUPERSEDED if p.lower() in flat]


def test_active_scope_defines_the_direct_fed_z2():
    import final_closure_results as FR
    scope = (D / "FINAL_PAPER_SCOPE.md").read_text()
    head = scope.split("## The paper MAY claim")[0]
    assert "`Z2_DIRECT_FEED`" in head and "directly" in head
    assert "`Z1_EMBEDDED`" in head and "`Z2_BGA_FED_CONTROL`" in head
    assert FR.active_scope_stale() == []
    for f in _tracked_text_files():
        assert _superseded_hits(f.read_text(errors="ignore")) == [], f.relative_to(R)
    # NEGATIVE: the archived scope (real text) is caught, and so is the brief's wording
    arch = D / "archive" / "FINAL_PAPER_SCOPE_PRE_DIRECT_FEED.md"
    assert _superseded_hits(arch.read_text())
    assert _superseded_hits("Z2 — backside: 48 V reaches Z2 laterally\nthrough the package RDL.")
    assert FR.SUPERSEDED_Z2_SCOPE in arch.read_text()


# ------------------------------------------------------------------ 9
def test_bga_fed_z2_is_control_only():
    fin = J("final_results.json")
    assert {f["arch"] for f in fin} == {"Z1", "Z2"}
    assert all(f["architecture_variant"] == "Z2_DIRECT_FEED" for f in fin if f["arch"] == "Z2")
    od = J("ordering.json")["orderings"]
    for k, o in od.items():
        assert "Z2BF" not in (o.get("favoured") or []), k
    spec = J("z2_direct_feed_architecture.json")["architectures"]["Z2BF"]
    assert spec["primary"] is False and spec["variant"] == "Z2_BGA_FED_CONTROL"
    ctrl = J("control_results.json")
    assert "Z2BF_HV_S0" in json.dumps(list(ctrl.get("cases", {})))
    scope = (D / "FINAL_PAPER_SCOPE.md").read_text()
    assert "never the primary Z2" in scope


# ------------------------------------------------------------------ 10
def test_local_solder_is_not_ranked_from_point_values(monkeypatch):
    import final_closure_results as FR
    od = J("ordering.json")["orderings"]["d_eps_in_per_cycle"]
    lm = J("local_mesh_study.json")
    z = {a: lm["cases"][f"{a}_HV_S0"] for a in ("Z1", "Z2")}
    gap = abs(z["Z1"]["production_value"] - z["Z2"]["production_value"]) / max(
        z["Z1"]["production_value"], z["Z2"]["production_value"])
    if gap <= 2 * max(z["Z1"]["U"], z["Z2"]["U"]):
        assert od["per_scenario"]["HV_S0"] == "unresolved"
    # the generator, on the brief's point values (Z1 6.28e-3, Z2 7.24e-3: a 13 % gap):
    # without a quantified U, or with the bounded Z2 U, they stay unresolved; only a U
    # below half the gap would rank them -- the rule decides, never the two numbers
    rows = []
    for arch, v in (("Z1", 6.28e-3), ("Z2", 7.24e-3)):
        for s in ("HV_S0", "HV_S1"):
            rows.append({"arch": arch, "scenario": s, "P_loss_w": 1.0, "T_max_C": 1.0,
                         "die_warpage_pv_um": 1.0, "du_c_um": 1.0, "d_eps_in_per_cycle": v,
                         "T_joint_at_or_above_solder_solidus": False,
                         "T_joint_outside_norton_calibration": False})
    real = FR.J

    def with_u(u):
        ls = {"cases": {f"{a}_{s}": {"U": u} for a in ("Z1", "Z2") for s in ("HV_S0", "HV_S1")}}
        return lambda n: ls if n == "local_mesh_study.json" else real(n)
    verdicts = {}
    for u in (None, z["Z2"]["U"], 0.01):
        monkeypatch.setattr(FR, "J", with_u(u))
        o = FR.ordering(rows, {"cases": {}})["orderings"]["d_eps_in_per_cycle"]
        verdicts[u] = set(o["per_scenario"].values())
    assert verdicts[None] == {"unresolved"} and verdicts[z["Z2"]["U"]] == {"unresolved"}
    assert verdicts[0.01] == {"Z1 lower"}               # positive control of the rule
    # no text ranks it from the two numbers either
    monkeypatch.setattr(FR, "J", real)
    for name, t in _user_texts().items():
        flat = " ".join(t.split())
        assert not re.search(r"7\.24\s*(?:\\times|x|×)?\s*10\^?\{?-3", flat), name


# ------------------------------------------------------------------ 11
def test_classb_b1_count_includes_attach_density():
    cb = J("classB_resolution.json")
    g = {x["gate"]: x for x in cb["gates"]}
    assert "geom.vr_attach_density" in g
    a = g["geom.vr_attach_density"]
    assert a["new_subtype"] == "B1" and a["declared_subtype"] == "B1"
    assert set(a["cases_run"]) == {"attach_dense", "attach_sparse", "attach_sparse_stiff"}
    b1 = [x for x in cb["gates"] if x["new_subtype"] == "B1"]
    assert cb["summary"]["b1_total"] == len(b1)
    assert cb["summary"]["subtypes"]["B1"] == len(b1)
    mac = (R / "manuscript" / "final_lineage_macros.tex").read_text()
    assert re.search(r"\\newcommand\{\\NbOne\}\{(\d+)\}", mac).group(1) == str(len(b1))
    # classified B; once its runs close it, it leaves the OPEN rows and is listed as closed
    cls = J("paper_gate_classification.json")
    assert (any(r["id"] == "geom.vr_attach_density" and r["class"] == "B" for r in cls["rows"])
            or "geom.vr_attach_density" in cls["classified_but_no_longer_open"])
    import final_closure_gate_classes as GC
    assert GC.CLASSES["geom.vr_attach_density"][0] == "B"
    # the engineering sweep is judged with the same rule but is never a gate case
    x = cb["attach_density_crossover"]
    assert x["class"] == "ENGINEERING_SENSITIVITY"
    assert not any(c.startswith("attach_eng") for gg in cb["gates"] for c in gg["cases_run"])


# ------------------------------------------------------------------ 12
def test_paper_ready_fails_without_attach_density_evidence(monkeypatch):
    import final_closure_results as FR
    gates = [{"gate": "geom.vr_attach_density", "new_subtype": "B1", "resolved": True}]
    assert FR.attach_density_missing(gates) == []
    # the gate itself missing from the class-B record
    assert any("absent" in w for w in FR.attach_density_missing(
        [{"gate": "board.h1_meshed", "new_subtype": "B1", "resolved": True}]))
    real = FR.J

    def without(*names):
        return lambda n: None if n in names else real(n)
    monkeypatch.setattr(FR, "J", without("vr_attach_density_study.json"))
    assert any("lattice" in w for w in FR.attach_density_missing(gates))
    monkeypatch.setattr(FR, "J", without("reference_attach_rve.json"))
    assert any("RVE" in w for w in FR.attach_density_missing(gates))
    # a study whose sparse case lacks its mechanical bounds is not evidence either
    st = real("vr_attach_density_study.json")
    st["cases"]["sparse"].pop("mech_bound_B")
    monkeypatch.setattr(FR, "J", lambda n: st if n == "vr_attach_density_study.json" else real(n))
    assert any("sparse" in w for w in FR.attach_density_missing(gates))
    # end to end: everything else satisfied, the attach evidence absent -> not ready
    monkeypatch.setattr(FR, "J", without("vr_attach_density_study.json"))
    pol = json.loads((D / "local_mesh_policy.json").read_text())
    lm = {"acceptance": {"pass": True}, "cases": {f"{a}_{s}": {"U": 0.01, "production_value": 1.0}
                                                  for a, s in FR.local_cases(pol)}}
    final = [{"arch": "Z2", "architecture_variant": "Z2_DIRECT_FEED", "forbidden_terms": []}]
    ok, why = FR.paper_ready(True, True, True, True, True, {"gates": gates}, lm, final)
    assert not ok and any("attach-density study" in w for w in why)


# ------------------------------------------------------------------ registries (Part 20)
def test_no_registry_claims_an_unknown():
    """No registry may claim a Z2 48 V BGA field, a known feed-loop resistance, a qualified
    attach, a known current-density allowable or a resolved local ranking."""
    spec = J("z2_direct_feed_architecture.json")["architectures"]
    assert spec["Z2"]["bga_48v_power_field"] is None
    cx = J("direct_feed_crossover.json")
    assert cx["assumed_value"] is None
    pg = {g["id"]: g for g in json.loads(
        (R / "research/phase0nw/physical_gates.json").read_text())["gates"]}
    assert pg["elec.direct_feed_loop_resistance"]["status"] == "OPEN"
    for gid in ("mat.vr_attach_material", "mat.vr_attach_underfill"):
        assert pg[gid]["status"] == "OPEN", gid          # bounded, never a sourced card
    st = study()
    assert "no electromigration-safe current density" in st["current_density_note"]
    for c in st["cases"].values():
        assert c["mechanical_status"].startswith("BOUNDED")
        assert not any("allowable" in k.lower() for k in c["electrical"])
    acc = {r["stage"]: r for r in J("accuracy_speed_matrix.json")["rows"]}
    assert acc["vr_attach_mechanical"]["status"] == "BOUNDED"
    assert acc["vr_attach_mechanical"]["evidence_class"] == "UNVALIDATED"
    od = J("ordering.json")["orderings"]["d_eps_in_per_cycle"]
    lm = J("local_mesh_study.json")["cases"]
    for s, v in od["per_scenario"].items():
        if v.endswith("lower"):
            z = [lm[f"{a}_{s}"] for a in ("Z1", "Z2")]
            gap = abs(z[0]["production_value"] - z[1]["production_value"]) / max(
                z[0]["production_value"], z[1]["production_value"])
            assert gap > 2 * max(x["U"] for x in z), s
    dec = (D / "FINAL_PAPER_DECISION.md").read_text().lower()
    for bad in ("attach is qualified", "qualified attach process is", "r_feed is known",
                "feed-loop resistance is known", "em-safe current density is"):
        assert bad not in dec, bad
