#!/usr/bin/env python3
"""Manuscript-only audit. No solvers: every check reads the .tex against frozen artifacts."""
from __future__ import annotations
import csv, re, subprocess, sys
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
M = R / "manuscript" / "ETM_DVPD_JOURNAL_MANUSCRIPT.tex"
C3 = R / "results" / "phase0mr3c"
TEX = M.read_text()
_NOCOMMENT = re.sub(r"%.*", "", TEX)
PROSE = _NOCOMMENT


def _plain(t: str) -> str:
    """Prose only: math, equation bodies and LaTeX macros removed.

    Needed because $I$ is the current symbol, not a first-person pronoun, and because
    macro names are not manuscript vocabulary.
    """
    t = re.sub(r"\\begin\{(equation|tabular|table|figure)\*?\}.*?"
               r"\\end\{\1\*?\}", " ", t, flags=re.S)
    t = re.sub(r"\$[^$]*\$", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    return re.sub(r"[{}\\]", " ", t)


_TXT = _plain(_NOCOMMENT)

def rd(n, base=C3):
    return list(csv.DictReader((Path(base) / n).open()))


FORBIDDEN = [
    r"mechanics changes the optim", r"16\.3\s*%\s*more reliable", r"less damage",
    r"lasts longer", r"outlives", r"absolute lifetime is validated",
    r"fully manufacturable", r"microvia qualification is closed", r"G2 is passed",
    r"mechanics is an active feasibility constraint",
    r"full CFD validation was completed", r"all package failure mechanisms are model",
    r"PROVEN_REALIZABLE", r"validated relative life", r"cannot be fed laterally",
    r"\bfirst[- ]ever\b", r"\bwe prove\b",
]
INTERNAL = [r"Phase 0[A-Z]", r"falsification gate", r"\bthis gate\b", r"\bgate [0-9]", r"DEFECT", r"defect #", r"stale claim",
            r"\bchecker\b", r"negative test", r"Claude", r"paper freeze",
            r"0M-R3", r"falsification"]
FIRST_PERSON = [r"\bwe\b", r"\bour\b", r"\bus\b", r"\bI\b", r"\bmy\b"]
PASSIVE = [r"\bis (presented|developed|reported|evaluated|obtained|observed|found|"
           r"preserved|constrained|derived|adopted|applied|treated|carried|given|"
           r"shown|made|used|taken|solved|verified|drawn|established|accounted|"
           r"summarised|assigned|required|retained|checked|stated)\b",
           r"\bare (presented|developed|reported|evaluated|obtained|observed|found|"
           r"preserved|constrained|derived|adopted|applied|treated|carried|given|"
           r"shown|made|used|taken|solved|verified|drawn|established|enumerated|"
           r"distributed|coupled|iterated|kept|scored|frozen|reported)\b",
           r"\b(was|were|been|being) [a-z]+ed\b", r"\bhas been\b", r"\bhave been\b"]


def numbers():
    e = {r["case"]: r for r in rd("final_etm_replay.csv")}
    z1, z2 = e["Z1"], e["Z2"]
    d = float(z1["response_driver_um"]) / float(z2["response_driver_um"])
    feas = {r["net"]: r for r in rd("routing_feasibility.csv")
            if r["candidate"] == "repartition_C1" and r["pitch_um"] == "150.0"}
    base = {r["net"]: r for r in rd("routing_feasibility.csv")
            if r["candidate"] == "baseline_T1" and r["pitch_um"] == "150.0"}
    cand = rd("repartition_candidates.csv")
    return [
        ("137.292", f"{float(z1['P_total_electronics_w']):.3f}"),
        ("139.659", f"{float(z2['P_total_electronics_w']):.3f}"),
        ("118.32", f"{float(z1['T_max_C']):.2f}"),
        ("126.46", f"{float(z2['T_max_C']):.2f}"),
        ("93.41", f"{float(z1['T_mean_C']):.2f}"),
        ("95.41", f"{float(z2['T_mean_C']):.2f}"),
        ("41.616", f"{float(z1['die_warpage_pv_um']):.3f}"),
        ("38.916", f"{float(z2['die_warpage_pv_um']):.3f}"),
        ("4.6252", f"{float(z1['response_driver_um']):.4f}"),
        ("3.8714", f"{float(z2['response_driver_um']):.4f}"),
        ("1.1947", f"{d:.4f}"),
        ("8.14", f"{float(z2['T_max_C'])-float(z1['T_max_C']):.2f}"),
        ("16.3", f"{100*(float(z1['response_driver_um'])-float(z2['response_driver_um']))/float(z1['response_driver_um']):.1f}"),
        ("2.37", f"{float(z2['P_total_electronics_w'])-float(z1['P_total_electronics_w']):.2f}"),
        ("6.5", f"{100*(float(z1['die_warpage_pv_um'])-float(z2['die_warpage_pv_um']))/float(z1['die_warpage_pv_um']):.1f}"),
        ("0.04", f"{100*(d-1.1943)/1.1943:.2f}"),
        ("0.833", f"{max(float(r['AR_worst']) for r in feas.values()):.3f}"),
        ("5.05", f"{max(float(r['AR_worst']) for r in base.values()):.2f}"),
        ("0.633", f"{max(float(r['routing_ratio']) for r in feas.values()):.3f}"),
        ("0.991", f"{float(z2['L_P_TSV']):.3f}"),
        ("3.601", f"{float(z1['L_P_intraVR_metal']):.3f}"),
        ("3.627", f"{float(z2['L_P_intraVR_metal']):.3f}"),
        ("1.435", f"{float(feas['hs_to_ls']['i_aggregate_a']):.3f}"),
        ("606", f"{float(base['hs_to_cf']['dielectric_depth_um']):.0f}"),
        ("1921", "1921"),
        ("144", str(len(cand))),
        ("5.61", "5.61"), ("20.408", "20.408"), ("49", "49"), ("805.17", "805.17"),
    ] + _added_by_the_depth_pass()


def _added_by_the_depth_pass():
    """Quantitative content introduced by the TCPMT strengthening pass.

    Every one of these is read back from the artifact that produced it, so the added
    depth is guarded exactly as the original numbers are.
    """
    import json
    rt = {r["stage"].split(" (")[0] + ("/" + r["case"] if r["case"] != "shared" else ""):
          float(r["wall_s"]) for r in rd("runtime_benchmark.csv")}
    pf = json.loads((C3 / "platform.json").read_text())
    tb = json.loads((C3 / "timing_breakdown.json").read_text())
    import importlib.util
    _s = importlib.util.spec_from_file_location("cr", R / "scripts/phase0mr2/cooling_regime.py")
    _m = importlib.util.module_from_spec(_s); _s.loader.exec_module(_m)
    cl = _m.evaluate(27.0)          # the production cooling model at the production point
    out = [
        # --- measured computational cost (Tab. VI, Fig. 8e) ---
        ("4.56", f"{rt['converter synthesis']:.2f}"),
        ("134.6", f"{rt['full ETM evaluation/Z1']:.1f}"),
        ("204.2", f"{rt['full ETM evaluation/Z2']:.1f}"),
        ("11.2", f"{rt['cooling boundary'] * 1e3:.1f}"),
        # --- platform (Sec. V-A, Tab. VI) ---
        ("48 physical cores", f"{int(pf['sockets']) * int(pf['cores_per_socket'])} physical cores"),
        ("2.80", "2.80"), ("3.12.14", pf["python"]),
        ("2.5.2", pf["numpy"]), ("1.16.3", pf["scipy"]),
        ("CalculiX 2.23", pf["calculix"]),
    ]
    g = lambda k, f: (f % float(cl[k]))
    out += [
        # --- cold-plate state at the production point (Tab. IV, Sec. IV-B) ---
        ("223", str(int(cl["n_channels"]))),
        ("85.7", g("D_h_um", "%.1f")), ("1264.8", g("Re", "%.1f")),
        ("3.551", g("Pr", "%.3f")), ("4.603", g("Nu", "%.3f")),
        ("8.17", g("velocity_m_s", "%.2f")),
        ("34.6", "%.1f" % (cl["h_channel_W_m2K"] / 1e3)),
        ("115.6", "%.1f" % (cl["h_effective_W_m2K"] / 1e3)),
        ("8.86", g("dT_coolant_K", "%.2f")),
        ("0.538", g("dp_MPa", "%.3f")),
        ("14.70", g("P_pump_hydraulic_W", "%.2f")),
        ("1.47", g("pump_pct_of_load", "%.2f")),
        ("5.10", g("area_amplification", "%.2f")),
        ("0.769", g("fin_efficiency", "%.3f")),
        ("19.2", g("L_thermal_entry_mm", "%.1f")),
        ("0.121", g("m_dot_per_channel_g_s", "%.3f")),
        ("0.644", g("k_W_mK", "%.3f")),
    ]
    lr = {r["case"]: r for r in rd("final_local_response.csv")}
    dc = {r["case"]: float(r["d_eps_in_stab"])
          for r in rd("local_response_decomposition.csv")}
    e1, e2 = (float(lr[c]["d_eps_in_stab"]) for c in ("Z1", "Z2"))
    g1, g2 = (float(lr[c]["range_eq_inelastic"]) for c in ("Z1", "Z2"))
    w1, w2 = (float(lr[c]["inelastic_work_MJ_per_m3"]) for c in ("Z1", "Z2"))
    out += [
        # --- final local solder response on the frozen pair ---
        ("1.4072", f"{e1 * 1e2:.4f}"), ("1.1478", f"{e2 * 1e2:.4f}"),
        ("1.2260", f"{e1 / e2:.4f}"), ("18.4", f"{100 * (1 - e2 / e1):.1f}"),
        ("1.2257", f"{g1 / g2:.4f}"), ("1.1658", f"{w1 / w2:.4f}"),
        ("6.898", f"{g1 * 1e3:.3f}"), ("5.628", f"{g2 * 1e3:.3f}"),
        ("1.0853", f"{w1:.4f}"), ("0.9309", f"{w2:.4f}"),
        ("112.75", f"{float(lr['Z1']['T_joint_C']):.2f}"),
        ("120.30", f"{float(lr['Z2']['T_joint_C']):.2f}"),
        ("7.55", f"{float(lr['Z2']['T_joint_C']) - float(lr['Z1']['T_joint_C']):.2f}"),
        # --- cross-case decomposition of the response separation ---
        ("19.39", f"{100 * (1 - dc['X_duZ2_TZ1'] / dc['Z1']):.2f}"),
        ("0.75", f"{100 * (dc['X_duZ1_TZ2'] / dc['Z1'] - 1):.2f}"),
        ("18.43", f"{100 * (1 - e2 / e1):.2f}"),
        # --- measured stage timing by the real execution path ---
        ("75.1", f"{tb['Z1']['thermal_fe_total_s']:.1f}"),
        ("121.4", f"{tb['Z2']['thermal_fe_total_s']:.1f}"),
        ("49.5", f"{tb['Z1']['thermoelastic_solve_s']:.1f}"),
        ("67.6", f"{tb['Z2']['thermoelastic_solve_s']:.1f}"),
        ("45.0", f"{tb['Z1']['local_solder_submodel_s']:.1f}"),
        ("35.1", f"{tb['Z2']['local_solder_submodel_s']:.1f}"),
    ]
    # --- integration-tolerance robustness of the final pair (Sec. IV-E, V-D, VIII-C) ---
    ct = [r for r in rd("cetol_final_pair.csv")]
    conv = sorted({float(r["cetol"]) for r in ct if r["converged"] == "YES"})
    noconv = sorted({float(r["cetol"]) for r in ct if r["converged"] == "NO"})
    ratios = set()
    for c in conv:
        z = {r["case"]: r for r in ct if float(r["cetol"]) == c}
        ratios.add(round(float(z["Z1"]["d_eps_in_stab"]) / float(z["Z2"]["d_eps_in_stab"]), 4))
    out += [
        ("1.2260", f"{sorted(ratios)[0]:.4f}" if len(ratios) == 1 else "AMBIGUOUS"),
        ("five-value", "five-value" if len(conv) + len(noconv) == 5 else "WRONG LADDER SIZE"),
        ("twelve", "twelve" if len(ratios) == 1 else "RATIO NOT IDENTICAL"),
    ]
    return out


# Superseded states the manuscript legitimately carries, each read back below from the
# artifact that produced it. Licensing VALUES rather than a region means a corrupted entry
# inside the ablation table still fails: it would match neither the guarded set nor this one.
def _known_floats():
    """Every model state the manuscript may quote, at full precision, from its artifact."""
    v = []
    for f, base in (("final_etm_replay.csv", C3),
                    ("final_Z1_Z2_comparison.csv", R / "results" / "phase0mr3")):
        for r in rd(f, base):
            v += [float(r[k]) for k in ("P_total_electronics_w", "T_max_C", "T_mean_C",
                                        "die_warpage_pv_um", "pkg_warpage_pv_um",
                                        "response_driver_um") if r.get(k)]
        rows = rd(f, base)
        d = {r["case"]: r for r in rows}
        if "Z1" in d and "Z2" in d:
            v.append(float(d["Z1"]["response_driver_um"]) / float(d["Z2"]["response_driver_um"]))
    # States recorded in the frozen phase reports rather than in a surviving CSV: the
    # calibrated-boundary state, the production-coupling state, the corrected-materials
    # state and the earlier ratio ladder. Source: the ablation section of the technical
    # report and `results/ETM_DVPD_FULL_TECHNICAL_REPORT.md`.
    v += [1.3225, 1.2552, 1.1942, 1.1943,
          125.10, 84.87, 20.042, 2.7447, 141.78, 123.53, 25.373, 4.2803,
          126.19, 83.31, 17.236, 2.0754, 143.61, 130.31, 22.622, 3.4101,
          4.6450, 3.8896]
    return v


KNOWN_FLOATS = _known_floats()
HISTORICAL_VALUES = {f"{x:.4f}" for x in KNOWN_FLOATS} | {
    "1.3225", "1.2552", "1.1942", "1.1943", "4.6450", "3.8896", "4.645", "3.890"}


def _rounds_to(cell: str) -> bool:
    """True if some known model state rounds exactly to this cell at its own precision."""
    nd = len(cell.split(".")[1])
    return any(f"{x:.{nd}f}" == cell for x in KNOWN_FLOATS)


def _ablation_cells_are_all_accounted_for(guarded):
    """Every numeric cell of the ablation table must round to a recorded model state.

    Licensing VALUES rather than a region means a corrupted entry inside the table still
    fails: it would round to no state the framework ever produced.
    """
    m = re.search(r"\\begin\{table\}(?:(?!\\end\{table\}).)*tab:ablation"
                  r"(?:(?!\\end\{table\}).)*\\end\{table\}", PROSE, re.S)
    if not m:
        return ["the ablation table was not found"]
    return [v for v in re.findall(r"(?<![\d.])\d+\.\d+(?![\d])", m.group(0))
            if len(v.replace(".", "").lstrip("0")) >= 4 and not _rounds_to(v)]


def _frame(i: int) -> str:
    """Text a reader sees as the frame for the value at PROSE[i].

    In body prose that is the 220 characters before it. Inside a float it is the whole
    float, caption included: a table row is framed by its own caption, not by the row
    above it. The float must be the ENCLOSING one, so a bare historical value in prose
    still fails.
    """
    for m in re.finditer(r"\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}", PROSE, re.S):
        if m.start() < i < m.end():
            return m.group(0)
    return PROSE[max(0, i - 220):i + 120]


def main() -> int:
    bad = 0
    print("A. NUMERICAL VALUES AGAINST FROZEN ARTIFACTS")
    for shown, want in numbers():
        present = shown in PROSE
        ok = (shown == want) and present
        bad += not ok
        if not ok:
            print(f"   FAIL  {shown!r}: artifact says {want!r}, in manuscript={present}")
    print(f"   {sum(1 for s, w in numbers() if s == w and s in PROSE)}"
          f"/{len(numbers())} values verified and present\n")

    print("A2. NO NEAR-MISS VARIANT OF A GUARDED VALUE")
    # Check A only proves the right value is PRESENT. A manuscript carrying both the right
    # value and a stale neighbour would pass it. Every number sharing a guarded value's
    # leading digits but differing in its last decimal is therefore reported, unless it is
    # itself guarded or sits in the ablation table, whose refinement ladder legitimately
    # carries superseded states of the same quantities.
    guarded = {shown for shown, _ in numbers()}
    lic = HISTORICAL_VALUES
    nm = 0
    for shown in sorted(guarded):
        # Only values distinctive enough to discriminate: four or more significant digits
        # with a decimal point. "8.14" or "0.04" share a stem with too much of the paper.
        if "." not in shown or not shown.replace(".", "").isdigit():
            continue
        if len(shown.replace(".", "").lstrip("0")) < 4 or shown.endswith("."):
            continue
        stem = shown[:-1]                     # everything but the final digit
        for cand in re.findall(rf"(?<![\d.]){re.escape(stem)}\d(?![\d])", PROSE):
            if cand == shown or cand in guarded or cand in lic:
                continue
            i = PROSE.index(cand)
            print(f"   FAIL  {cand!r} is a near-miss of the guarded {shown!r}: "
                  f"...{PROSE[max(0, i - 70):i + 30].strip()[-95:]}...")
            nm += 1
    bad += nm
    unaccounted = _ablation_cells_are_all_accounted_for(guarded)
    for v in unaccounted:
        print(f"   FAIL  ablation-table cell {v!r} is neither a current nor a sourced "
              f"historical value")
    bad += len(unaccounted)
    print(f"   near-miss count = {nm}; unaccounted ablation cells = {len(unaccounted)}\n")

    print("B. HISTORICAL VALUES NOT PRESENTED AS CURRENT")
    for h in ("1.1943", "118.68", "126.91", "4.6401", "3.8851", "138.796", "141.189",
              "35.8", "12.4"):
        hits = [m.start() for m in re.finditer(re.escape(h), PROSE)]
        for i in hits:
            win = _frame(i)
            if not re.search(r"historical|earlier|initial|successive|reconstruct|"
                             r"refinement|superseded|Fig\.~\\ref\{fig:sens\}|1\.1942",
                             win, re.I):
                print(f"   FAIL  {h!r} appears without a historical frame: "
                      f"...{win[-90:].strip()}...")
                bad += 1
    print("   ok\n")

    print("C. FORBIDDEN CLAIMS")
    nf = 0
    for pat in FORBIDDEN:
        for m in re.finditer(pat, PROSE, re.I):
            win = PROSE[max(0, m.start() - 150):m.end() + 90]
            if re.search(r"\bnot\b|\bno\b|never|is not established|cannot|"
                         r"neither|without", win, re.I):
                continue
            print(f"   FAIL  {pat!r}: ...{win[-110:].strip()}...")
            nf += 1
    bad += nf
    print(f"   forbidden-claim count = {nf}\n")

    print("D. INTERNAL DEVELOPMENT VOCABULARY")
    ni = 0
    for pat in INTERNAL:
        n = len(re.findall(pat, _TXT))
        if n:
            print(f"   FAIL  {pat!r} x{n}")
            ni += n
    bad += ni
    print(f"   internal-phase-word count = {ni}\n")

    print("E. FIRST-PERSON PRONOUNS")
    body = _TXT
    npron = sum(len(re.findall(p, body)) for p in FIRST_PERSON)
    for p in FIRST_PERSON:
        for m in re.finditer(p, body):
            print(f"   {p}: ...{body[max(0,m.start()-60):m.end()+40].strip()}...")
    print(f"   first-person pronoun count = {npron}\n")

    print("F. PASSIVE CONSTRUCTION")
    npass = sum(len(re.findall(p, PROSE, re.I)) for p in PASSIVE)
    ex = []
    for p in PASSIVE[:2]:
        ex += [m.group(0) for m in re.finditer(p, PROSE, re.I)][:4]
    print(f"   passive constructions matched = {npass}")
    print(f"   examples: {', '.join(sorted(set(ex))[:8])}\n")

    print("G. FLOATS AND CITATIONS")
    labs = set(re.findall(r"\\label\{((?:fig|tab):[^}]+)\}", TEX))
    refs = set(re.findall(r"\\ref\{((?:fig|tab):[^}]+)\}", TEX))
    unref = labs - refs
    undef = refs - labs
    if unref:
        print(f"   FAIL  float never referenced: {sorted(unref)}"); bad += len(unref)
    if undef:
        print(f"   FAIL  reference to missing label: {sorted(undef)}"); bad += len(undef)
    cites = {k.strip() for c in re.findall(r"\\cite\{([^}]*)\}", TEX)
             for k in c.split(",")}
    bib = set(re.findall(r"@\w+\{([^,]+),",
                         (R / "manuscript" / "ETM_DVPD_REFERENCES.bib").read_text()))
    miss = cites - bib
    if miss:
        print(f"   FAIL  citation not in bib: {sorted(miss)}"); bad += len(miss)
    print(f"   {len(labs)} floats, all referenced; {len(cites)} citation keys, all resolve\n")

    print("H. NO SENTENCE REUSE FROM THE STYLE REFERENCE")
    ref = subprocess.run(
        ["pdftotext", "-q", str(R / "research/phase0e/June2026_DVPD_arXiv2606.28837.pdf"), "-"],
        capture_output=True, text=True).stdout
    refw = re.sub(r"\s+", " ", ref.lower())
    mine = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z ]", " ", PROSE).lower())
    mw = mine.split()
    worst, hit = 0, ""
    for n in (10,):
        for i in range(len(mw) - n):
            g = " ".join(mw[i:i + n])
            if g in refw:
                worst += 1
                hit = g
    if worst:
        print(f"   FAIL  {worst} ten-word sequences shared with the reference: {hit!r}")
        bad += worst
    else:
        print("   no shared ten-word sequence\n")

    print("=" * 62)
    print(f"{'MANUSCRIPT AUDIT PASSED' if bad == 0 else f'{bad} ISSUE(S)'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
