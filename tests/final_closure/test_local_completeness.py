"""DEFECT #69: a local solder solve is accepted only if its .dat reaches the schedule end.

On 2026-10-28 at 22:20:08 the per-user thread limit of the shared host was reached and
CalculiX died mid-run. The control solve's .dat stopped at t = 1800.517 s of 2400 s; the
historical runner evaluated its time-keyed last-cycle window on what was there and returned
d_eps = 2.695e-3 against the published 6.513e-3. The guards below run on the REAL header
lines that truncated file ended with, never a paraphrase."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))
import final_closure_local_extract as X                             # noqa: E402

#: the first block every harness .dat starts with (S0 control, 2026-10-28)
HEAD = (" equivalent plastic strain (elem, integ.pnt.,pe)for set ESOLCORE and time  "
        "0.2000000E-02\n\n       124   1  4.553398E-04\n       124   2  8.090446E-04\n")
#: the last blocks of the truncated control .dat (fc_local_HV_S2/CONTROL.dat, 22:20:08)
TRUNCATED_TAIL = (
    " strains (elem, integ.pnt.,exx,eyy,ezz,exy,exz,eyz) for set ESOLCORE and time  "
    "0.1800517E+04\n\n"
    " stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set ESOL and time  "
    "0.1800517E+04\n\n"
    " strains (elem, integ.pnt.,exx,eyy,ezz,exy,exz,eyz) for set ESOL and time  "
    "0.1800517E+04\n\n"
    " temperatures for set NBOT and time  0.1800517E+04\n\n"
    "       804  8.286000E+01\n       808  8.286000E+01\n       812  8.286000E+01\n")
COMPLETE_TAIL = TRUNCATED_TAIL.replace("0.1800517E+04", "0.2400000E+04")
T_END = 2 * 4 * 300.0                       # the harness schedule: 4 cycles x 2 x 300 s


def _dat(tmp_path, name, tail):
    p = tmp_path / f"{name}.dat"
    p.write_text(HEAD + tail)
    return p


def test_end_time_reads_the_last_block(tmp_path):
    assert X.end_time(_dat(tmp_path, "cut", TRUNCATED_TAIL)) == pytest.approx(1800.517)
    assert X.end_time(_dat(tmp_path, "full", COMPLETE_TAIL)) == pytest.approx(2400.0)


def test_the_real_truncated_file_is_refused_and_a_complete_one_accepted(tmp_path):
    assert not X.complete(_dat(tmp_path, "cut", TRUNCATED_TAIL), T_END)
    assert X.complete(_dat(tmp_path, "full", COMPLETE_TAIL), T_END)
    assert not X.complete(tmp_path / "missing.dat", T_END)
    assert not X.complete(_dat(tmp_path, "empty", ""), T_END)


@pytest.fixture
def LS(tmp_path, monkeypatch):
    import final_closure_local_solder as LS
    monkeypatch.setattr(LS.LR, "WD", tmp_path)
    monkeypatch.setattr(LS.LR, "N_CYC", 4)
    monkeypatch.setattr(LS.LR, "DWELL", 300.0)
    LS.INCOMPLETE.clear()
    return LS


def test_the_runner_reports_no_response_for_the_truncated_solve(LS, tmp_path):
    """The historical runner returned a number from the truncated file; the checked runner
    must not, and must say where the solve stopped."""
    def fake(case, du, t, tail=TRUNCATED_TAIL):
        _dat(tmp_path, case, tail)
        return {"d_peeq_per_cycle": 2.695221328e-03}       # what the old runner returned
    assert LS._complete_case("CONTROL", 2.749, 82.86, _run=fake) is None
    assert LS.INCOMPLETE["CONTROL"]["t_last_s"] == pytest.approx(1800.517)
    ok = LS._complete_case("CONTROL", 2.749, 82.86,
                           _run=lambda c, d, t: fake(c, d, t, COMPLETE_TAIL))
    assert ok == {"d_peeq_per_cycle": 2.695221328e-03}


def test_an_old_dat_never_stands_in_for_a_solve_that_did_not_run(LS, tmp_path):
    _dat(tmp_path, "Z1_HV_S0", COMPLETE_TAIL)                # a previous, complete solve
    assert LS._complete_case("Z1_HV_S0", 2.39, 121.5, _run=lambda c, d, t: None) is None
    assert not (tmp_path / "Z1_HV_S0.dat").exists()


def test_install_routes_the_control_through_the_check(LS):
    orig = LS.LR.run_case
    try:
        LS.install()
        assert LS.LR.run_case is LS._complete_case
        LS.install()                                          # idempotent
        assert LS.LR.run_case is LS._complete_case
    finally:
        LS.LR.run_case = orig


def test_a_solid_joint_without_a_response_stops_the_run(LS):
    resp = {"d_peeq_per_cycle": 8.0e-3}
    cases = {"Z1": {"T_joint_C": 121.51, "response": None,
                    "fine_mesh": {"response": resp}},          # the 22:20:08 Z1 HV-S0 loss
             "Z2": {"T_joint_C": 97.25, "response": resp, "fine_mesh": {"response": resp}}}
    assert LS.lost_responses(cases) == ["Z1"]
    cases["Z1"]["response"] = resp
    assert LS.lost_responses(cases) == []
    # above the solder melting onset a missing response is an outcome, not a failure
    molten = {"Z1": {"T_joint_C": 240.0, "response": None, "fine_mesh": {"response": None}}}
    assert LS.lost_responses(molten) == []
