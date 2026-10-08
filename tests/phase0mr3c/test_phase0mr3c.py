#!/usr/bin/env python3
"""Phase-0M-R3C tests. Every semantic guard is negative-tested with the real sentence."""
from __future__ import annotations
import csv, importlib.util, math, os, re, subprocess, sys
from pathlib import Path

import pytest
import yaml

R = Path(__file__).resolve().parents[2]
OUT = R / "results" / "phase0mr3c"
HIST = R / "results" / "ETM_DVPD_FULL_TECHNICAL_REPORT.md"
STAND = R / "results" / "ETM_DVPD_CURRENT_FRAMEWORK_AUDIT_REPORT.md"
STATUS = R / "results" / "CURRENT_SCIENTIFIC_STATUS.yaml"
CONTRACT = R / "configs" / "phase0mr3" / "semantic_contract.yaml"
PHASE = "0M-R3C"


def _load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


sa = _load("sa", R / "scripts" / "phase0mr3" / "semantic_audit.py")


def rows(n, base=OUT):
    return list(csv.DictReader((Path(base) / n).open()))


@pytest.fixture(scope="module")
def status(): return yaml.safe_load(STATUS.read_text())


@pytest.fixture(scope="module")
def contract(): return yaml.safe_load(CONTRACT.read_text())


@pytest.fixture(scope="module")
def reports(): return {"historical": HIST.read_text(), "standalone": STAND.read_text()}


def inject(body, sentence):
    a = "**Method.**"
    assert a in body
    return body.replace(a, sentence + "\n\n" + a, 1)


# the real sentences this phase removed
STALE = [
    ("no_current_realizable_pair_claim",
     "On the CURRENT repaired realizable pair the backside architecture carries 16.3 % "
     "LESS local fatigue-relevant inelastic RESPONSE"),
    ("weighting_is_response_not_damage",
     "a convergent local solder viscoplastic damage metric (M2) added in Phase 0I"),
    ("weighting_is_response_not_damage",
     "the two architectures occupy nearly the same damage-weighted stress distribution"),
    ("lateral_delivery_is_lossy_not_impossible",
     "A 1 kW compute die drawing 1000 A at 1 V cannot be fed laterally."),
]


# ---------------------------------------------------------------- phase / provenance
def test_phase_is_0mr3c(status, contract, reports):
    assert status["meta"]["current_phase"] == PHASE
    assert status["current_state_contract"]["current_phase"]["state"] == f"{PHASE} complete"
    assert contract["meta"]["gates"][-1] == PHASE
    m = re.search(r"\|\s*Phase completed\s*\|\s*([^|]+)\|", reports["historical"])
    assert m and m.group(1).strip().startswith(PHASE)


def test_verdict_and_defect_registered(status):
    v = status["verdict"]
    assert v["phase0mr3c_option_letter"] == "B"
    assert "ORDERING" in v["phase0mr3c"]
    reg = {int(x["id"]): x for x in status["phase0g_defects"]}
    assert 64 in reg and "conductor" in yaml.safe_dump(reg[64]).lower()


# ---------------------------------------------------------------- Section 1 guards
@pytest.mark.parametrize("rule,sentence", STALE)
def test_stale_sentence_absent_and_guard_fires(reports, contract, rule, sentence):
    for name, body in reports.items():
        assert sentence not in body, f"{name}: {sentence[:50]}"
    hits = sa.audit(inject(reports["historical"], sentence), contract)
    assert any(f["rule_id"] == rule for f in hits), f"{rule} did not reject: {sentence[:60]}"


def test_the_weighting_is_still_dpeeq_times_volume():
    src = (R / "scripts" / "phase0lr" / "mechanism_audit.py").read_text()
    fn = src[src.index("def elementwise_damage"):src.index("def wq(")]
    assert 'float(d["P"]) - prev[1]' in fn and "dp*v" in fn
    for law in ("coffin", "manson", "darveaux", "cycles_to_fail"):
        assert law not in fn.lower()


def test_licensed_wording_is_present(reports):
    assert "inelastic-strain-weighted" in reports["historical"]
    assert "prohibitively lossy" in reports["standalone"]


# ---------------------------------------------------------------- conductor planes
def test_via_levels_come_from_conductor_planes_not_layer_count():
    cp = rows("conductor_plane_topology.csv")
    g = [r for r in cp if r["template"] == "T1_EMBEDDED_4LAYER" and r["net"] == "ls_to_L"]
    assert len(g) == 5, "terminal, RDL, dielectric, RDL, terminal"
    assert int(g[0]["via_levels_total"]) == 1, "one via level, not three"
    vias = [r for r in g if r["needs_via"] == "True"]
    assert len(vias) == 1 and float(vias[0]["thickness_um"]) == 100.0
    # the two RDLs are CONDUCTOR planes and must never be counted as dielectric regions
    rdl = [r for r in g if r["kind"] == "CONDUCTOR PLANE"]
    assert len(rdl) == 2 and all(r["needs_via"] == "False" for r in rdl)
    assert all("land here" in r["capture_land"] for r in rdl)


def test_material_layer_count_would_have_given_three():
    g = [r for r in rows("conductor_plane_topology.csv")
         if r["template"] == "T1_EMBEDDED_4LAYER" and r["net"] == "ls_to_L"]
    material = [r for r in g if float(r["thickness_um"]) > 0]
    assert len(material) == 3, "three material layers -- the count DEFECT #64 was based on"
    assert int(g[0]["via_levels_total"]) == 1, "but only one is a dielectric region"


# ---------------------------------------------------------------- repartition
def test_repartition_is_a_permutation_of_the_baseline():
    cand = {r["partition"]: r for r in rows("repartition_candidates.csv")}
    base = cand["gan_hs | gan_ls | cap_fly | cap_out,inductor"]
    new = cand["gan_hs | cap_fly | gan_ls | cap_out,inductor"]
    assert new["n_tiers"] == base["n_tiers"]
    assert new["max_tier_area_mm2"] == base["max_tier_area_mm2"]
    assert new["stack_height_um"] == base["stack_height_um"]
    assert int(new["ls_to_L_via_levels"]) == 0 < int(base["ls_to_L_via_levels"])
    assert float(new["worst_vertical_depth_um"]) < float(base["worst_vertical_depth_um"])
    assert new["source_order_compatible"] == "True"


def test_search_was_bounded_to_existing_components():
    import sys as _s
    _s.path.insert(0, str(R / "scripts" / "phase0mr"))
    _s.path.insert(0, str(R / "scripts" / "phase0m"))
    _s.path.insert(0, str(R / "scripts"))
    import routing_production as RP
    allowed = set(RP.H_UM)
    for r in rows("repartition_candidates.csv"):
        got = {c for t in r["partition"].split(" | ") for c in t.split(",")}
        assert got == allowed, "a component was invented or dropped"
        assert float(r["max_tier_area_mm2"]) <= RP.DESIGN["tile_side_mm"] ** 2 + 1e-9


# ---------------------------------------------------------------- feasibility contract
def test_framework_provisioning_is_separated_from_manufacturing():
    for r in rows("routing_feasibility.csv"):
        assert r["manufacturing_status"].startswith("OPEN"), \
            "a manufacturing qualification is being claimed"
        assert r["n_required_framework"] != "" or r["via_levels"] == "0"


def test_frozen_pair_passes_the_contract_at_a_sourced_pitch():
    sel = [r for r in rows("routing_feasibility.csv")
           if r["candidate"] == "repartition_C1" and r["pitch_um"] == "150.0"]
    assert len(sel) == 3
    for r in sel:
        assert r["feasible_framework"] == "True"
        assert int(r["n_required_framework"]) <= int(r["n_available"])
        assert r["pitch_provenance"] == "SOURCE_BOUNDED"
    assert max(float(r["AR_worst"]) for r in sel) < 1.0, "worst aspect ratio must be < 1"


def test_repartition_beats_the_baseline_on_aspect_ratio():
    f = rows("routing_feasibility.csv")
    b = max(float(r["AR_worst"]) for r in f
            if r["candidate"] == "baseline_T1" and r["pitch_um"] == "150.0")
    c = max(float(r["AR_worst"]) for r in f
            if r["candidate"] == "repartition_C1" and r["pitch_um"] == "150.0")
    assert b > 5.0 and c < 1.0, (b, c)


def test_n_req_reproduces_independently():
    J, TL = 1.0e8, 0.5
    for r in rows("routing_feasibility.csv"):
        if not r["n_required_framework"]:
            continue
        d, i = float(r["d_um"]), float(r["i_aggregate_a"])
        want = max(1, math.ceil(i / (J * math.pi * ((d / 2 - TL) * 1e-6) ** 2)))
        assert int(r["n_required_framework"]) == want


def test_per_device_current_is_within_the_datasheet_rating():
    ls = [r for r in rows("routing_feasibility.csv") if r["net"] == "ls_to_L"][0]
    # the CSV stores the current rounded to 4 dp
    assert float(ls["i_per_device_a"]) == pytest.approx(1000.0 / 49.0 / 3.0, abs=5e-5)
    assert float(ls["i_per_device_a"]) < 9.6, "EPC2057 continuous rating"


# ---------------------------------------------------------------- final pair and replay
def test_neither_architecture_is_proven_realizable(status):
    for r in rows("final_pair_status.csv"):
        assert r["proven_realizable"] == "False"
        assert r["verdict"] == "GEOMETRICALLY_REALIZABLE / PROCESS-CONDITIONAL"
        assert r["process_status"].startswith("OPEN")
    blob = (OUT / "PHASE0MR3C_REPARTITION_AND_PAPER_FREEZE.md").read_text()
    for m in re.finditer(r"PROVEN_REALIZABLE", blob):
        win = blob[max(0, m.start() - 120):m.end() + 60]
        assert re.search(r"not|never|NOT", win), f"PROVEN_REALIZABLE asserted: {win[:90]}"


def test_the_replay_ran_once_on_a_pair_frozen_first():
    etm = {r["case"]: r for r in rows("final_etm_replay.csv")}
    assert set(etm) == {"Z1", "Z2"}, "exactly one solve per architecture"
    for tag in ("Z1", "Z2"):
        fz = yaml.safe_load(
            (R / f"configs/phase0mr3c/frozen_pair_{tag}.yaml").read_text())
        assert fz["frozen"] is True and "before any ETM result" in fz["frozen_by"]
        assert etm[tag]["template"] == fz["partition"]["template"]
        assert abs(float(etm[tag]["energy_residual_pct"])) < 1.0


def test_ordering_survives_and_the_magnitude_barely_moves():
    fp = {r["case"]: r for r in rows("final_pair_status.csv")}
    etm = {r["case"]: r for r in rows("final_etm_replay.csv")}
    d = float(etm["Z1"]["response_driver_um"]) / float(etm["Z2"]["response_driver_um"])
    assert d == pytest.approx(float(fp["Z1"]["D_driver_final"]), abs=5e-5)
    assert d > 1.0, "Z2 must carry the lower response"
    assert abs(100 * (d - 1.1943) / 1.1943) < 1.0, "magnitude moved more than 1 %"
    assert float(etm["Z2"]["T_max_C"]) > float(etm["Z1"]["T_max_C"]), "Z2 stays hotter"


# ---------------------------------------------------------------- paper freeze
def test_paper_freeze_artifacts_exist_and_are_consistent():
    dec = (R / "results" / "PAPER_FREEZE_DECISION.md").read_text()
    plan = (R / "results" / "PAPER_FIGURE_TABLE_PLAN.md").read_text()
    cm = rows("PAPER_CLAIM_MATRIX.csv", R / "results")
    assert len(cm) >= 10
    for c in cm:
        assert c["source_status"] in ("SOURCE_BACKED", "SOURCE_BOUNDED", "MODEL", "OPEN")
        assert c["permitted_wording"] and c["forbidden_wording"] and c["manuscript_section"]
    assert "**No.**" in dec, "question 8 must be answered"
    assert "None." in dec, "question 6 must be answered"
    nf = len(re.findall(r"\| \*\*Fig\. ", plan))
    nt = len(re.findall(r"\| \*\*Tab\. ", plan))
    assert 6 <= nf <= 8, nf
    assert 3 <= nt <= 4, nt


def test_the_paper_does_not_claim_mechanics_changes_the_optimum():
    dec = (R / "results" / "PAPER_FREEZE_DECISION.md").read_text()
    assert "**not** framed as" in dec
    m = re.search(r"mechanics CHANGES the optimal DVPD architecture", dec)
    assert m, "the forbidden framing must be named explicitly so it can be checked"
    assert "must NOT be claimed" in dec


# ---------------------------------------------------------------- reports
def test_reports_clean_and_current(reports, contract):
    for name, body in reports.items():
        assert sa.audit(body, contract) == [], name
    assert re.search(r"(?m)^# Phase 0M-R3C .*\(current authoritative\)", reports["historical"])
    for name, body in reports.items():
        assert len(re.findall(r"(?m)^# .*\(current authoritative\)", body)) <= 1


def test_gate_roll_agrees(reports, contract):
    gates = contract["meta"]["gates"]
    for name, body in reports.items():
        m = re.search(r"([\w-]+) sequential falsification gates\s*\(([^)]*)\)",
                      re.sub(r"\s+", " ", body))
        assert m, name
        assert m.group(1) == sa.NUMWORD[len(gates)], (name, m.group(1))
        assert [x.strip() for x in m.group(2).split(",")] == gates, name


def test_next_work_is_manuscript_freeze(status):
    nw = status["current_state_contract"]["current_next_work"]["state"]
    assert nw.startswith("MANUSCRIPT FREEZE")
    assert "Phase 0N is NOT authorised" in nw
    for done in ("adopt the phase-0m physical cooling model",
                 "put the rdl in the mechanical mesh"):
        assert done not in nw.lower()


def test_reports_regenerate_idempotently():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PHASE0MR3_", "PHASE0MR3B_"))}

    def run():
        p = subprocess.run([sys.executable,
                            str(R / "scripts/phase0mr3b/rebuild_reports.py")],
                           capture_output=True, text=True, cwd=str(R), env=env)
        assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-1500:]
        return HIST.read_text(), STAND.read_text()

    first = run()
    assert run() == first, "the rebuild chain is not idempotent"


def test_phase0mr3b_baseline_untouched():
    import hashlib
    B = R / "results" / "phase0mr3b" / "_baseline_phase0mr3a"
    ok = bad = 0
    for line in (B / "MD5SUMS.txt").read_text().splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        got = hashlib.md5((B / name.strip().lstrip("*")).read_bytes()).hexdigest()
        ok, bad = (ok + 1, bad) if got == digest else (ok, bad + 1)
    assert bad == 0 and ok >= 14, f"{bad} baseline files changed"


# --------------------------------------------------------- manuscript guards


MANUSCRIPT = R / "manuscript" / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex"
AUDIT = R / "scripts" / "phase0mr3c" / "audit_manuscript.py"


def _audit() -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(AUDIT)], capture_output=True,
                          text=True, cwd=str(R))


def test_manuscript_audit_passes():
    p = _audit()
    assert p.returncode == 0, p.stdout[-3000:]


@pytest.mark.parametrize("injected", [
    # A superseded intermediate state written as a current result, in body prose.
    # This is the real sentence form, not a paraphrase: both values are genuine
    # historical states (Phase-0M-R3 / 0M-R3A) that the ablation table carries
    # legitimately and that body prose must never assert as the answer.
    "The peak temperature of the backside architecture is $126.91\\,^{\\circ}$C and the "
    "response ratio is $D = 1.1943$.\n",
    "The corner-joint response of the embedded architecture is $4.6401$\\,\\textmu m.\n",
])
def test_historical_value_as_current_is_rejected(injected):
    """The float-scoped frame must not excuse a historical value in body prose."""
    anchor = "The backside architecture dissipates $2.37$\\,W more, almost entirely because its"
    orig = MANUSCRIPT.read_text()
    assert orig.count(anchor) == 1, "anchor moved; update the negative test"
    try:
        MANUSCRIPT.write_text(orig.replace(anchor, injected + anchor, 1))
        p = _audit()
        assert p.returncode != 0, "the historical-value guard did not fire:\n" + p.stdout[-2000:]
        assert "without a historical frame" in p.stdout
    finally:
        MANUSCRIPT.write_text(orig)
    assert MANUSCRIPT.read_text() == orig
    assert _audit().returncode == 0, "the manuscript was not restored cleanly"


@pytest.mark.parametrize("old,new", [
    ("$1264.8$", "$1264.9$"),      # Reynolds number, cooling table
    ("$4.6252$", "$4.6253$"),      # Z1 corner-joint driver
    ("1.1947", "1.1946"),          # the deciding response ratio
    ("115.6", "115.7"),            # effective cooling coefficient
    ("$4.640$", "$4.641$"),        # a superseded ablation state
    ("1.1943", "1.1944"),          # a superseded ratio in the ladder
    ("0.833", "0.834"),            # worst repartitioned aspect ratio
    ("204.2", "204.3"),            # measured Z2 wall time
])
def test_corrupting_any_guarded_value_is_caught(old, new):
    """A wrong number must fail even when the right one survives elsewhere.

    Check A alone only proves the correct value is PRESENT; these probes corrupt real
    occurrences, including inside the ablation table, and the audit must reject each.
    """
    orig = MANUSCRIPT.read_text()
    assert old in orig, f"probe anchor {old!r} is gone; update the negative test"
    try:
        MANUSCRIPT.write_text(orig.replace(old, new))
        assert MANUSCRIPT.read_text() != orig, "probe was a no-op; it proves nothing"
        p = _audit()
        assert p.returncode != 0, (
            f"corrupting {old!r} -> {new!r} was not caught:\n" + p.stdout[-2500:])
    finally:
        MANUSCRIPT.write_text(orig)
    assert _audit().returncode == 0, "the manuscript was not restored cleanly"


def test_plotted_die_field_reproduces_the_frozen_warpage():
    """The field Fig. 6 plots must be the frozen result, not a re-solve that drifted."""
    import csv as _csv
    p = subprocess.run([sys.executable, str(R / "scripts/phase0mr3c/extract_die_field.py")],
                       capture_output=True, text=True, cwd=str(R))
    assert p.returncode == 0, p.stdout[-2000:] + p.stderr[-1000:]
    frozen = {r["case"]: float(r["die_warpage_pv_um"])
              for r in _csv.DictReader((OUT / "final_etm_replay.csv").open())}
    for case, want in frozen.items():
        f = OUT / f"die_surface_field_{case}.csv"
        uz = [float(r["uz_um"]) for r in _csv.DictReader(f.open())]
        assert abs((max(uz) - min(uz)) - want) < 1e-6, \
            f"{case}: plotted field p-v {max(uz) - min(uz)} against frozen {want}"


def test_frozen_global_pair_is_unchanged_by_the_local_response_work():
    """The local submodel must not have moved a single frozen global number."""
    import csv as _csv
    want = {
        "Z1": dict(P_total_electronics_w=137.29226286185747, T_max_C=118.32,
                   T_mean_C=93.40990690909089, die_warpage_pv_um=41.6156,
                   pkg_warpage_pv_um=77.02383, response_driver_um=4.625234102183368),
        "Z2": dict(P_total_electronics_w=139.65949335081902, T_max_C=126.463,
                   T_mean_C=95.41169712500002, die_warpage_pv_um=38.915500000000009,
                   pkg_warpage_pv_um=72.03949, response_driver_um=3.8713856447013915)}
    got = {r["case"]: r for r in _csv.DictReader((OUT / "final_etm_replay.csv").open())}
    for case, cols in want.items():
        for k, v in cols.items():
            assert float(got[case][k]) == pytest.approx(v, rel=0, abs=1e-9), \
                f"{case}.{k} changed: {got[case][k]} != {v}"


def test_local_response_traces_to_the_frozen_pair():
    """d_eps_in must come from the frozen du_c and T_joint, and the two must not be conflated."""
    import csv as _csv
    inp = {r["case"]: r for r in _csv.DictReader((OUT / "local_submodel_inputs.csv").open())}
    res = {r["case"]: r for r in _csv.DictReader((OUT / "final_local_response.csv").open())}
    frz = {r["case"]: r for r in _csv.DictReader((OUT / "final_etm_replay.csv").open())}
    for case in ("Z1", "Z2"):
        # the driver the submodel was given is the frozen driver, to the last digit
        assert float(res[case]["du_c_um"]) == pytest.approx(
            float(frz[case]["response_driver_um"]), rel=0, abs=1e-9)
        assert float(inp[case]["du_c_um"]) == pytest.approx(
            float(frz[case]["response_driver_um"]), rel=0, abs=1e-9)
        # the response is dimensionless and of a wholly different magnitude to the driver
        e = float(res[case]["d_eps_in_stab"])
        assert 0.0 < e < 1.0, f"{case}: d_eps_in {e} is not a strain increment"
        assert abs(e - float(res[case]["du_c_um"])) > 1.0, "driver and response conflated"
        # the stabilised cycle really is stabilised
        assert float(res[case]["stab_change_pct"]) < 5.0
        # the integration tolerance used reproduced the published control exactly
        assert float(res[case]["cetol_control_dev_pct"]) < 0.5
    e1, e2 = (float(res[c]["d_eps_in_stab"]) for c in ("Z1", "Z2"))
    d1, d2 = (float(res[c]["du_c_um"]) for c in ("Z1", "Z2"))
    assert e1 > e2 and d1 > d2, "the driver and response orderings must agree"
    assert e1 / e2 == pytest.approx(1.2260, abs=5e-4)
    assert d1 / d2 == pytest.approx(1.1947, abs=5e-4)
    # and they must NOT be the same number -- that was the defect being corrected
    assert abs(e1 / e2 - d1 / d2) > 1e-3


def test_manuscript_never_calls_the_driver_an_inelastic_response():
    """du_c is a displacement. The 16.3 % separation may not be labelled a strain response."""
    tex = MANUSCRIPT.read_text()
    # forms that EQUATE the driver with the response. Sentences that contrast the two are
    # correct and must not be caught, so the patterns are anchored on the 16.3 % figure and
    # on the table row label rather than on any co-occurrence of the two symbols.
    for bad in (
            # "16.3 % ... inelastic response" in any spelling. The 16.3 % figure belongs to
            # the displacement driver; attaching it to an inelastic response is the defect.
            # The window is short enough to exclude the caption sentence that legitimately
            # names both quantities 88 characters apart.
            r"16\.3\$?\\,\\%\s*(?:lower|less|lower,)[^.]{0,40}inelastic",
            # the table row label that called the driver a response
            r"Corner-joint response \$\\du\$"):
        assert not re.search(bad, tex), f"driver labelled as response: {bad}"
    # and the response figure must never be attached to the driver symbol
    assert not re.search(r"\\du[^$]{0,30}18\.4", tex), "18.4 % attached to the driver"
    # both quantities must appear in the final-comparison table
    i = tex.index("\\label{tab:final}")
    j = tex.index("\\end{table}", i)
    tab = tex[i:j]
    assert "\\du" in tab and "varepsilon_{\\mathrm{in}}" in tab, \
        "Table II must carry the driver and the response as separate rows"


@pytest.mark.parametrize("old,new", [
    # the exact Table II row label that called the displacement driver a response
    ("Displacement driver $\\du$ (\\textmu m)", "Corner-joint response $\\du$ (\\textmu m)"),
    # the exact abstract and results wordings that attached the driver's 16.3 % to a strain
    ("an $18.4$\\,\\% lower stabilised local\ninelastic response",
     "a $16.3$\\,\\% lower local inelastic response"),
    ("carrying $18.4$\\,\\% lower local\nfatigue-relevant inelastic response",
     "carrying $16.3$\\,\\% lower local\nfatigue-relevant inelastic response"),
])
def test_conflation_guard_fires_on_the_real_defect(old, new):
    """Each probe is the real text this pass removed, not a paraphrase."""
    orig = MANUSCRIPT.read_text()
    assert old in orig, f"anchor moved, probe is void: {old[:45]!r}"
    try:
        MANUSCRIPT.write_text(orig.replace(old, new, 1))
        assert MANUSCRIPT.read_text() != orig, "probe was a no-op; it proves nothing"
        with pytest.raises(AssertionError):
            test_manuscript_never_calls_the_driver_an_inelastic_response()
    finally:
        MANUSCRIPT.write_text(orig)
    test_manuscript_never_calls_the_driver_an_inelastic_response()


def test_mechanics_is_outside_the_et_loop():
    """The timing text may only claim what the code does."""
    import json as _json
    tb = _json.loads((OUT / "timing_breakdown.json").read_text())
    for case in ("Z1", "Z2"):
        assert tb[case]["mechanics_inside_et_loop"] is False
        assert tb[case]["n_et_iterations"] == 3
        assert tb[case]["thermal_subsolves_total"] == 11
    src = (R / "scripts/phase0mr/replay_production.py").read_text()
    body = src[src.index("def run_case("):]
    loop = body.index("for it in range(max_et_iter)")
    mech = body.index("run_ccx(si")
    brk = body.index("# ---- mechanics on the converged temperature field")
    assert loop < brk < mech, "the structural solve is no longer outside the E-T loop"


def test_every_manuscript_figure_is_built_from_the_generator():
    """No figure may be a stale file: each one the .tex includes must be regenerated."""
    import hashlib
    figs = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}", MANUSCRIPT.read_text())
    assert len(figs) == 8, figs
    d = R / "manuscript" / "figs"
    before = {f: hashlib.md5((d / f).read_bytes()).hexdigest() for f in figs}
    p = subprocess.run([sys.executable, str(R / "scripts/phase0mr3c/make_manuscript_figures.py")],
                       capture_output=True, text=True, cwd=str(R))
    assert p.returncode == 0, p.stderr[-2000:]
    missing = [f for f in figs if not (d / f).exists()]
    assert not missing, f"the generator does not produce {missing}"
    assert set(x.name for x in d.glob("*.pdf")) == set(figs), \
        "figs/ holds a PDF the manuscript does not include"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
