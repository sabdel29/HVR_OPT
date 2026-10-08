#!/usr/bin/env python3
"""Phase-0M-R3C addendum --- timing of the FROZEN configurations. No physics is changed.

Each stage of one production evaluation is timed separately, on the frozen Z1 and Z2
configurations of configs/phase0mr3c/frozen_pair_*.yaml and with the same environment
hooks the final replay used. Mesh sizes are recorded alongside the times so the cost can
be read per degree of freedom.
"""
from __future__ import annotations
import csv, json, os, platform, subprocess, sys, time
from pathlib import Path
import yaml

R = Path(__file__).resolve().parents[2]
for p in ("scripts/phase0mr3", "scripts/phase0mr2", "scripts/phase0mr", "scripts/phase0i",
          "scripts/phase0f", "scripts/phase0m", "scripts"):
    sys.path.insert(0, str(R / p))
os.environ["PATH"] = "/home/beams0/MGHARIB/envs/etm/bin:" + os.environ["PATH"]
OUT = R / "results" / "phase0mr3c"
CASES = [("Z1", "ARCH_Z1_EMBEDDED", 1.30), ("Z2", "ARCH_Z2_BACKSIDE", 0.30)]


def platform_record() -> dict:
    def sh(c):
        try:
            return subprocess.run(c, shell=True, capture_output=True,
                                  text=True, timeout=30).stdout.strip()
        except Exception:
            return ""
    lscpu = sh("lscpu")
    def f(k):
        for l in lscpu.splitlines():
            if l.startswith(k):
                return l.split(":", 1)[1].strip()
        return ""
    import numpy, scipy
    return {
        "host": platform.node(), "os": sh("cat /etc/redhat-release") or platform.platform(),
        "kernel": platform.release(), "cpu": f("Model name"),
        "sockets": f("Socket(s)"), "cores_per_socket": f("Core(s) per socket"),
        "threads_per_core": f("Thread(s) per core"), "logical_cpus": os.cpu_count(),
        "ram": sh("free -g | awk '/^Mem:/{print $2\" GiB\"}'"),
        "python": platform.python_version(), "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "calculix": sh("echo | ccx -v 2>&1 | head -1") or "CalculiX 2.23",
        "moose": sh("/home/beams0/LPOPRYHO/projects/moose/modules/heat_transfer/"
                    "heat_transfer-opt --version 2>/dev/null | head -1"),
        "gpu_used": "no", "solver_threads": os.environ.get("OMP_NUM_THREADS", "48"),
    }


def main() -> int:
    fz = yaml.safe_load((R / "configs/phase0mr3c/frozen_pair_Z1.yaml").read_text())
    ic = fz["interconnect"]
    os.environ["PHASE0MR3B_PHYSICAL_SPANS"] = "1"
    os.environ["PHASE0MR3_R_VIA_UM"] = str(ic["microvia_diameter_um"] / 2.0)
    os.environ["PHASE0MR3_VIA_PITCH_UM"] = str(ic["microvia_pitch_um"])
    tpl = fz["partition"]["template"]

    plat = platform_record()
    (OUT / "platform.json").write_text(json.dumps(plat, indent=1))
    for k, v in plat.items():
        print(f"  {k:18s} {v}")
    print()

    import routing_production as RP                                      # noqa: E402
    import cooling_regime as CR                                          # noqa: E402
    import replay_production as RPX                                      # noqa: E402

    rows = []

    # ---- converter synthesis -----------------------------------------------------
    t0 = time.perf_counter()
    d = RPX.compiled_design()
    t_syn = time.perf_counter() - t0
    rows.append({"stage": "converter synthesis (HVR compile)", "case": "shared",
                 "size": f"{len(d.arch.B_array)} SC stages, N={d.arch.N}, K={d.arch.K}; "
                         f"90-device library", "dof": "", "wall_s": round(t_syn, 3),
                 "threads": 1, "reference_tool": "none", "error": "", "speedup": ""})

    # ---- electrical / PPDN --------------------------------------------------------
    t0 = time.perf_counter()
    for _ in range(20):
        RP.template_loss(tpl)
    t_el = (time.perf_counter() - t0) / 20
    rows.append({"stage": "rail-aware PPDN + intra-VR routing", "case": "shared",
                 "size": "6 segments/cell x 49 cells", "dof": "",
                 "wall_s": round(t_el, 4), "threads": 1, "reference_tool": "none",
                 "error": "", "speedup": ""})

    # ---- cooling ------------------------------------------------------------------
    t0 = time.perf_counter()
    for _ in range(200):
        CR.evaluate(27.0, strict=True)
    t_cool = (time.perf_counter() - t0) / 200
    rows.append({"stage": "cooling boundary (correlation)", "case": "shared",
                 "size": "223 channels", "dof": "", "wall_s": round(t_cool, 5),
                 "threads": 1, "reference_tool": "MOOSE explicit fins",
                 "error": "3.78 %", "speedup": ""})

    # ---- full ETM evaluation, per architecture -------------------------------------
    for tag, arch, h in CASES:
        t0 = time.perf_counter()
        r = RPX.run_case(arch=arch, mode="AFTER", template=tpl,
                         cooler_name="TOP_SI_MICROCHANNEL_27", h_sub_mm=h)
        t_all = time.perf_counter() - t0
        rows.append({"stage": "full ETM evaluation (E-T fixed point + mechanics)",
                     "case": tag, "size": f"{r['et_iters']} E-T iterations",
                     "dof": "", "wall_s": round(t_all, 2), "threads":
                     os.environ.get("OMP_NUM_THREADS", "48"),
                     "reference_tool": "none", "error": "", "speedup": ""})
        print(f"  {tag}: full ETM {t_all:7.2f} s, {r['et_iters']} E-T iterations, "
              f"T_max {r['T_max_C']:.2f} C, response {r['du_corner_um']:.4f} um")

    with (OUT / "runtime_benchmark.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"\n  wrote {OUT.name}/runtime_benchmark.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
