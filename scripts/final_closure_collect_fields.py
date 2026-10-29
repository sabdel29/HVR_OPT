"""Copy the CONVERGED production fields out of the E-T work tree (scratch).

The mechanics-only class-B variants re-solve the structure on the production temperature
field, and the die-warpage maps read the production structural solution. Both are taken
from $HVR_FIELDS/etm_{arch}_{scen}_r21/{thermal_converged,structural}.frd, which this
script fills from the final E-T iteration of each production case. It verifies that the
copied thermal field's peak equals the case file's to 1e-6 K, so a field from another run
can never pass as the production one.

    python final_closure_collect_fields.py [ARCH:SCEN ...]    (default: Z1/Z2 at HV-S0)
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402

FIELDS = Path(os.environ.get("HVR_FIELDS", Path.home() / "claude_scratch" / "hvr_work"
                             / "fields"))


def collect(arch, scen):
    import production_et as PE
    case = json.loads(E.case_path(arch, scen).read_text())
    wd = E.WD / f"{arch}_{scen}_h{E.PRODUCTION_H_XY}{E.refine_tag(E.PRODUCTION_REFINE)}"
    it = len(case["et_history"]) - 1
    th = sorted((wd / f"et{it}").glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))
    if not th:
        raise SystemExit(f"no thermal result in {wd / f'et{it}'}")
    tn = PE.ccxio.read_frd(th[-1])["NDTEMP"][1:, 0]
    if abs(float(np.nanmax(tn)) - case["thermal"]["T_max_C"]) > 1e-6:
        raise SystemExit(f"{th[-1]} is not the converged field of {arch} {scen}")
    st = wd / "structural.frd"
    dst = FIELDS / f"etm_{arch}_{scen}_r21"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(th[-1], dst / "thermal_converged.frd")
    if st.exists():
        shutil.copyfile(st, dst / "structural.frd")
    (dst / "SOURCE.json").write_text(json.dumps(
        {"case_file": E.case_path(arch, scen).name, "thermal": str(th[-1]),
         "structural": str(st) if st.exists() else None,
         "architecture_variant": case.get("architecture_variant"),
         "T_max_C": case["thermal"]["T_max_C"]}, indent=1))
    print(f"{arch} {scen}: {th[-1].name} (T_max {case['thermal']['T_max_C']:.4f} C)"
          + (" + structural" if st.exists() else " (no structural yet)"))


def main():
    cases = [tuple(c.split(":")) for c in sys.argv[1:]] or [("Z1", "HV_S0"), ("Z2", "HV_S0")]
    for a, s in cases:
        collect(a, s)


if __name__ == "__main__":
    main()
