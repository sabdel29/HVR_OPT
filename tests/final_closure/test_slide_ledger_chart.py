"""The heat-map slide's stacked ledger bar must equal the ledger total. It used to group
terms by a fixed list that predated the direct-fed Z2, so the Cu-pillar attach rows were not
drawn and the Z2 bar read 147.80 W against the ledger's 148.04 W."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))
D = R / "research" / "final_closure"


def _real(a):
    f = D / f"etm_{a}_HV_S0_h1.1_r21.json"
    if not f.exists():
        pytest.skip("no production case")
    return json.loads(f.read_text())


def test_the_bar_draws_every_real_ledger_term(monkeypatch, tmp_path):
    import prelim_make_figs_final as M
    monkeypatch.setattr(M, "FIG", tmp_path, raising=False)
    monkeypatch.setattr(M, "etm", lambda a, s: _real(a))
    M.fig_ledger()                                  # real Z1 and Z2 rows: every term drawn


def test_an_undrawn_term_stops_the_chart(monkeypatch, tmp_path):
    """NEGATIVE: the real Z2 case plus a term no group knows (as the attach rows once were)."""
    import prelim_make_figs_final as M
    monkeypatch.setattr(M, "FIG", tmp_path, raising=False)

    def fake(a, s):
        r = _real(a)
        if a == "Z2":
            r = dict(r, ledger_rows=r["ledger_rows"] + [{"term": "P_new_conductor",
                                                          "P_w": 0.234}],
                     P_loss_w=r["P_loss_w"] + 0.234)
        return r
    monkeypatch.setattr(M, "etm", fake)
    with pytest.raises(RuntimeError, match="not drawn"):
        M.fig_ledger()
