"""READY_NOT_EXECUTED: Q3D Extractor DC-resistance references (TSV bar, package RDL sheet).

Status on this host: the AEDT 2026 R1 desktop launches and builds these models, but
the Q3D solver feature is NOT licensed (FlexNet 'No such feature exists' on solve,
see scripts/reference_tools/q3d_smoke.py). These scripts are kept ready so the
comparison can be run unchanged on a licensed host; NO Q3D result appears anywhere
in this repository as evidence.

Usage on a licensed host:
    python q3d_dc_reference.py tsv   # single 30 um x 300 um TSV, DCR vs rho L/A
    python q3d_dc_reference.py rdl   # package HV RDL sheet at the matched count
Q3D's DC solution is a finite-element DC conduction solve for potential and current
(fields Phidc, VolumeJdc, Mag_VolumeJdc, Volume_Loss_DensityDc).
"""
import json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts" / "phase0nw"))
sys.path.insert(0, str(R / "scripts" / "phase0m"))
sys.path.insert(0, str(R / "scripts"))


def tsv(out):
    from ansys.aedt.core import Q3d
    q = Q3d(project=str(out / "q3d_tsv.aedt"), design="tsv", non_graphical=True,
            new_desktop=True, version="2026.1")
    q.modeler.model_units = "um"
    q.modeler.create_cylinder("Z", [0, 0, 0], 15.0, 300.0, name="tsv", material="copper")
    q.auto_identify_nets()
    q.source(q.modeler.get_faceid_from_position([0, 0, 0], assignment="tsv"), name="s")
    q.sink(q.modeler.get_faceid_from_position([0, 0, 300], assignment="tsv"), name="k")
    st = q.create_setup("DC"); st.props["AC"]["Enabled"] = False
    st.props["Cap"]["Enabled"] = False; st.props["DC"]["Enabled"] = True; st.update()
    t0 = time.time(); q.analyze_setup("DC"); dt = time.time() - t0
    expr = q.post.available_report_quantities(quantities_category="DCR Matrix")[0]
    d = q.post.get_solution_data(expressions=expr)
    return {"case": "tsv", "R_ohm": d.data_real()[0], "solve_s": dt}


def rdl(out):
    raise SystemExit("RDL sheet case: build from research/final_closure/package_network.json "
                     "ball_xy and pkg_rdl_refined.cell_terminals(); identical geometry to "
                     "the production solve. Requires a licensed Q3D solver.")


if __name__ == "__main__":
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/q3d_ref")
    out.mkdir(parents=True, exist_ok=True)
    res = {"tsv": tsv, "rdl": rdl}[sys.argv[1]](out)
    print(json.dumps(res))
