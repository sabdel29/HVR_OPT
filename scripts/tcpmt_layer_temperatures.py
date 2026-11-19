"""TCPMT revision. Mean temperature of each layer (board, BGA, substrate, converter, die) for every
cooling-tier case, from the converged fields on the production mesh, plus the board and silicon
in-plane CTE cards and the mismatch strain they imply.

Review round 2: the cases come from tcpmt_cases (the production state -- implemented decoupling --
under "cases", the S0 reference under "states"), Z3 is the coupled land-side case, and the
converged field is located by tcpmt_cases.converged_field (collected fields or the work trees),
checked against the case's T_max.

    python tcpmt_layer_temperatures.py   -> research/tcpmt_revision/layer_temperatures.json
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E                              # noqa: E402
import tcpmt_cases as TC                                            # noqa: E402
import tcpmt_region_temps as RT                                     # noqa: E402

OUT = Path(os.environ.get("ETM_RESULTS_ROOT") or R / "research") / "tcpmt_revision" / "layer_temperatures.json"


def layer_groups(m):
    lay = np.array(m.elem_layer, dtype=object)

    def nodes(pred):
        ids = np.where([pred(str(x)) for x in lay])[0]
        return np.unique(m.elems[ids].ravel()) - 1
    return {"board": nodes(lambda n: n == "board"), "bga": nodes(lambda n: n == "bga"),
            "substrate": nodes(lambda n: n in ("sub_lower", "tile_band")),
            "converter": nodes(lambda n: "conv_" in n or n.startswith(("z3conv", "z1conv"))),
            "die": nodes(lambda n: n == "die")}


def main():
    res = {"rule": "layer means of the converged nodal temperature on the production mesh (r21)",
           "production_state": TC.PRODUCTION_STATE, "cases": {}, "states": {}, "missing": []}
    meshes = {}
    for st in (TC.PRODUCTION_STATE, "S0"):
        for t in TC.TIERS:
            for arch in TC.ARCHS:
                p = TC.case_path(st, t, arch)
                if p is None:
                    res["missing"].append(f"{st} {t} {arch}")
                    continue
                c = json.loads(p.read_text())
                f = TC.converged_field(p, c)
                if f is None:
                    res["missing"].append(f"{st} {t} {arch}: no converged field ({p.name})")
                    continue
                if arch not in meshes:
                    m, mats, st_, tiles, minfo = E.build(arch, E.PRODUCTION_H_XY,
                                                         E.PRODUCTION_REFINE)
                    mt = st_["materials"]

                    def cte(name, mt=mt):
                        v = mt[name].get("cte")
                        v = v["value"] if isinstance(v, dict) else v
                        return v[0] if isinstance(v, (list, tuple)) else v
                    board_mat = [k for k in mt if k.startswith("board") or "it968" in k.lower()]
                    meshes[arch] = (m, layer_groups(m), cte(board_mat[0]), cte("silicon"))
                m, groups, cte_b, cte_si = meshes[arch]
                T = RT.read_temperatures(f["thermal"])[1:m.n_nodes + 1]
                if len(T) != m.n_nodes:
                    res["missing"].append(f"{st} {t} {arch}: field has another mesh")
                    continue
                out = {g: float(np.nanmean(T[ix])) for g, ix in groups.items() if len(ix)}
                bz = m.nodes[groups["board"], 2]
                top = groups["board"][np.abs(bz - bz.max()) < 1e-9]
                bot = groups["board"][np.abs(bz - bz.min()) < 1e-9]
                out["board_top"], out["board_bottom"] = (float(np.nanmean(T[top])),
                                                         float(np.nanmean(T[bot])))
                rec = dict(out, case=p.name, field=str(f["thermal"]), cte_board=cte_b,
                           cte_silicon=cte_si)
                res["states"].setdefault(st, {}).setdefault(arch, {})[t] = rec
                if st == TC.PRODUCTION_STATE:
                    res["cases"].setdefault(arch, {})[t] = rec
                print(f"{st} {t} {arch}: " + "  ".join(f"{k} {v:6.1f}" for k, v in out.items()),
                      flush=True)
    OUT.write_text(json.dumps(res, indent=1))
    print("wrote", OUT, "missing:", res["missing"])


if __name__ == "__main__":
    main()
