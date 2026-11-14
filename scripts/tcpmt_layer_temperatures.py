"""TCPMT revision. Mean temperature of each layer (board, BGA, substrate, converter, die) for every cooling-tier
case, from the collected converged fields on the production mesh, plus the board and silicon
in-plane CTE cards and the mismatch strain they imply."""
import sys, json
from pathlib import Path
import numpy as np
R = Path("/home/beams0/SABDELZAHER/ETM_project/HVR_OPT_work")
sys.path.insert(0, str(R / "scripts"))
import final_closure_physical_etm as E
import production_et as PE
F = Path("/home/beams0/SABDELZAHER/ETM_project/scratch/fields")
CASES = {"Z1": [("A", "etm_Z1_HV_S0_r21"), ("B", "etm_Z1_HV_S0__z1_bottom_plate_tim")],
         "Z2": [("A", "etm_Z2_HV_S0_r21"), ("B", "etm_Z2_HV_S0__z2_cooled_tim")],
         "Z3": [("A", "etm_Z3_HV_S0__z3_top_only"), ("B", "etm_Z3_HV_S0__z3_plate_tim")]}
RES = {}
for arch, cases in CASES.items():
    m, mats, st, tiles, minfo = E.build(arch, 1.1, (2, 1))
    lay = np.array(m.elem_layer, dtype=object)
    def nodes(pred):
        ids = np.where([pred(str(x)) for x in lay])[0]
        return np.unique(m.elems[ids].ravel()) - 1
    groups = {"board": nodes(lambda n: n == "board"), "bga": nodes(lambda n: n == "bga"),
              "substrate": nodes(lambda n: n in ("sub_lower", "tile_band")),
              "converter": nodes(lambda n: "conv_" in n or n.startswith("z3conv") or n.startswith("z1conv")),
              "die": nodes(lambda n: n == "die")}
    mt = st["materials"]
    def cte(name):
        c = mt[name].get("cte"); c = c["value"] if isinstance(c, dict) else c
        return c[0] if isinstance(c, (list, tuple)) else c
    board_mat = [k for k in mt if k.startswith("board") or "it968" in k.lower()]
    print(f"== {arch}: board cards {board_mat[:3]}; CTE silicon {cte('silicon'):.2e}",
          {k: f"{cte(k):.2e}" for k in board_mat[:2]})
    for tier, d in cases:
        T = PE.ccxio.read_frd(F / d / "thermal_converged.frd")["NDTEMP"][1:m.n_nodes + 1, 0]
        out = {g: float(np.nanmean(T[ix])) for g, ix in groups.items() if len(ix)}
        bz = m.nodes[groups["board"], 2]
        top = groups["board"][np.abs(bz - bz.max()) < 1e-9]; bot = groups["board"][np.abs(bz - bz.min()) < 1e-9]
        out["board_top"], out["board_bottom"] = float(np.nanmean(T[top])), float(np.nanmean(T[bot]))
        print(f"   {tier}: " + "  ".join(f"{k} {v:6.1f}" for k, v in out.items()))
        RES.setdefault(arch, {})[tier] = dict(out, field=d, cte_board=cte(board_mat[0]),
                                              cte_silicon=cte("silicon"))
OUT = R / "research" / "tcpmt_revision" / "layer_temperatures.json"
OUT.write_text(json.dumps({"rule": "layer means of the converged nodal temperature on the "
                                   "production mesh (r21), cooling tiers A and B, S0", "cases": RES},
                          indent=1))
print("wrote", OUT)
