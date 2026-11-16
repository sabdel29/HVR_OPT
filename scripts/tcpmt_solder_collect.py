"""Assemble research/tcpmt_revision/solder_studies.json from the study summaries.

Each driver (tcpmt_solder_{critical,cycles,band,constitutive}.py --summarize) merges its own
section; this module only does the locked read-modify-write and the header.

    python tcpmt_solder_collect.py      re-run every driver's summary and write the file
"""
from __future__ import annotations

import datetime as _dt
import fcntl
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tcpmt_solder_common as C                                     # noqa: E402

STUDIES = C.OUT / "solder_studies.json"


def merge(key, section, path=STUDIES):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = C.scratch(C.ROOT) / "studies.lock"
    with open(lock, "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        d = json.loads(path.read_text()) if path.exists() else {}
        d.setdefault("what", "TCPMT revision: local solder-joint studies answering the "
                             "reviewer (critical joint, cycle stabilisation, averaging band, "
                             "constitutive law)")
        d.setdefault("generator", ["scripts/tcpmt_solder_common.py",
                                   "scripts/tcpmt_solder_critical.py",
                                   "scripts/tcpmt_solder_cycles.py",
                                   "scripts/tcpmt_solder_band.py",
                                   "scripts/tcpmt_solder_constitutive.py",
                                   "scripts/tcpmt_solder_collect.py"])
        d["harness"] = {"entry_point": "scripts/final_closure_local_mesh.py::_solve",
                        "first_increment_s": C.INC0,
                        "first_increment_source": "research/final_closure/local_time_study.json"
                                                  " production_dt0_s",
                        "band_frac_production": C.BAND_PROD,
                        "band_um_production": C.BAND_PROD * C.JOINT.SOLDER_SIDE_UM,
                        "scratch": str(C.scratch(C.ROOT)),
                        "concurrency": f"{C.SLOTS} global solver slots x LOCAL_THREADS"}
        d[key] = section
        d["updated"] = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
        path.write_text(json.dumps(d, indent=1, default=float) + "\n")


def main():
    import tcpmt_solder_band as B
    import tcpmt_solder_constitutive as K
    import tcpmt_solder_critical as CR
    import tcpmt_solder_cycles as CY
    import tcpmt_solder_units_check as U
    merge("critical_joint", CR.summarize())
    merge("stabilization", CY.summarize())
    merge("averaging_band", B.summarize())
    merge("constitutive", K.summarize())
    merge("numerical_tolerance", U.summarize())
    print("wrote", STUDIES)


if __name__ == "__main__":
    main()
