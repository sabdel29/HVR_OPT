"""Copy the converged fields of SENSITIVITY cases out of their work trees (scratch).

The counterpart of final_closure_collect_fields.py for the cooling-tier cases of the TCPMT
revision (z3_top_only, z1_bottom_plate_tim, z2_cooled_tim, z3_plate_tim, ...): the thermal
field of the last E-T iteration and the structural solution go to
$HVR_FIELDS/etm_{arch}_HV_S0__{variant}/, after checking that the thermal field's peak equals
the case file's to 1e-6 K.

    python tcpmt_collect_variant_fields.py ARCH:VARIANT [...]
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
from hvr_scratch import path as scratch                             # noqa: E402

FIELDS = Path(os.environ.get("HVR_FIELDS", Path.home() / "claude_scratch" / "hvr_work"
                             / "fields"))


def collect(arch, variant):
    import production_et as PE
    f = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "final_closure" / "sensitivity" / f"etm_{arch}_HV_S0__{variant}.json"
    case = json.loads(f.read_text())
    wd = scratch("fc_sens", variant) / f"{arch}_HV_S0_h{E.PRODUCTION_H_XY}{E.refine_tag(E.PRODUCTION_REFINE)}"
    it = len(case["et_history"]) - 1
    th = sorted((wd / f"et{it}").glob("th_*.frd"), key=lambda p: int(p.stem.split("_")[1]))
    if not th:
        raise SystemExit(f"no thermal result in {wd / f'et{it}'}")
    tn = PE.ccxio.read_frd(th[-1])["NDTEMP"][1:, 0]
    if abs(float(np.nanmax(tn)) - case["thermal"]["T_max_C"]) > 1e-6:
        raise SystemExit(f"{th[-1]} is not the converged field of {arch} {variant}")
    st = wd / "structural.frd"
    dst = FIELDS / f"etm_{arch}_HV_S0__{variant}"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(th[-1], dst / "thermal_converged.frd")
    if st.exists():
        shutil.copyfile(st, dst / "structural.frd")
    (dst / "SOURCE.json").write_text(json.dumps(
        {"case_file": f.name, "thermal": str(th[-1]),
         "structural": str(st) if st.exists() else None,
         "T_max_C": case["thermal"]["T_max_C"]}, indent=1))
    print(f"{arch} {variant}: {th[-1].name} (T_max {case['thermal']['T_max_C']:.4f} C)"
          + (" + structural" if st.exists() else " (no structural yet)"))


def main():
    for c in sys.argv[1:]:
        a, v = c.split(":")
        collect(a, v)


if __name__ == "__main__":
    main()
