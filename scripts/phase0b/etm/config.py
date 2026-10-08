"""Phase-0B configuration loading, validation and material derivation.

Every numeric value carried into a simulation must have a provenance status.
This module refuses to silently promote an unknown into a fact: `Value.get()`
returns the number, but the status travels with it into the run manifest.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

MM_PER_M_INV = 1.0e-3      # W/(m.K) -> W/(mm.K)
W_M2K_TO_W_MM2K = 1.0e-6   # W/(m^2.K) -> W/(mm^2.K)

VALID_STATUS = {"SOURCE_BACKED", "DERIVED", "ASSUMPTION", "PROVISIONAL", "OPEN_DECISION"}
REPO = Path(__file__).resolve().parents[3]
CFG = REPO / "configs" / "phase0b"


def _v(node: Any, default_status: str = "ASSUMPTION") -> tuple[Any, str]:
    """Unpack a {value:, status:} node, or a bare scalar."""
    if isinstance(node, dict) and "value" in node:
        st = node.get("status", default_status)
        if st not in VALID_STATUS:
            raise ValueError(f"invalid status {st!r}; expected one of {sorted(VALID_STATUS)}")
        return node["value"], st
    return node, default_status


def load_stack(path: Path | None = None) -> dict:
    return yaml.safe_load((path or CFG / "package_stack.yaml").read_text())


def load_doe(path: Path | None = None) -> dict:
    return yaml.safe_load((path or CFG / "doe_cases.yaml").read_text())


# ---------------------------------------------------------------------------
# Material derivation
# ---------------------------------------------------------------------------

def derive_tsv_homog(stack: dict) -> dict:
    """Effective properties of a square-pitch Cu-via array in a Si matrix.

    Cu area fraction        f = pi*d^2 / (4*p^2)
    Stiffness (Voigt, aligned continuous phase along z):
        E_eff = f*E_Cu + (1-f)*E_Si_iso
    CTE (stiffness-weighted rule of mixtures):
        a_eff = (f*E_Cu*a_Cu + (1-f)*E_Si*a_Si) / (f*E_Cu + (1-f)*E_Si)
    Thermal:
        k_z  = f*k_Cu + (1-f)*k_Si                       (Voigt; exact for parallel conduction)
        k_xy = k_Si * (k_Cu + k_Si + f*(k_Cu - k_Si))
                    / (k_Cu + k_Si - f*(k_Cu - k_Si))    (Maxwell-Garnett, cylinders)

    The formula is the record; the number is a consequence. Status DERIVED.
    """
    tsv = stack["geometry"]["tsv_field"]
    d, _ = _v(tsv["diameter"])
    p, _ = _v(tsv["pitch"])
    f = math.pi * d * d / (4.0 * p * p)

    si, cu = stack["materials"]["silicon"], stack["materials"]["copper"]
    E_si, _ = _v(si["isotropic_check"]);  E_si = si["isotropic_check"]["E"]
    nu_si = si["isotropic_check"]["nu"]
    a_si, _ = _v(si["cte"]);   k_si, _ = _v(si["k"])
    E_cu, _ = _v(cu["E"]);     nu_cu, _ = _v(cu["nu"])
    a_cu, _ = _v(cu["cte"]);   k_cu, _ = _v(cu["k"])

    E_eff = f * E_cu + (1 - f) * E_si
    nu_eff = f * nu_cu + (1 - f) * nu_si
    a_eff = (f * E_cu * a_cu + (1 - f) * E_si * a_si) / E_eff
    k_z = f * k_cu + (1 - f) * k_si
    k_xy = k_si * (k_cu + k_si + f * (k_cu - k_si)) / (k_cu + k_si - f * (k_cu - k_si))

    return {
        "status": "DERIVED", "elastic_type": "iso",
        "cu_area_fraction": f,
        "E": {"value": E_eff, "status": "DERIVED"},
        "nu": {"value": nu_eff, "status": "DERIVED"},
        "cte": {"value": a_eff, "status": "DERIVED"},
        # CalculiX *CONDUCTIVITY,TYPE=ORTHO takes (k11,k22,k33)
        "k": {"value": k_xy, "status": "DERIVED"},
        "k_ortho": {"value": [k_xy, k_xy, k_z], "status": "DERIVED"},
        "note": "Voigt (z) + Maxwell-Garnett (in-plane); see derive_tsv_homog docstring.",
    }


@dataclass
class Material:
    name: str
    status: str
    elastic_type: str               # 'iso' | 'ortho'
    cte: float
    k: float                        # isotropic conductivity (W/mK)
    E: float | None = None
    nu: float | None = None
    C11: float | None = None
    C12: float | None = None
    C44: float | None = None
    k_ortho: list[float] | None = None

    def ccx_elastic(self) -> list[str]:
        """CalculiX *ELASTIC card lines. Units: MPa."""
        if self.elastic_type == "ortho":
            # CalculiX ORTHO order: D1111,D1122,D2222,D1133,D2233,D3333,D1212,D1313,D2323
            c11, c12, c44 = self.C11, self.C12, self.C44
            return ["*ELASTIC, TYPE=ORTHO",
                    f"{c11:.6g},{c12:.6g},{c11:.6g},{c12:.6g},{c12:.6g},{c11:.6g},{c44:.6g},{c44:.6g},",
                    f"{c44:.6g}"]
        return ["*ELASTIC", f"{self.E:.6g},{self.nu:.6g}"]

    def ccx_conductivity(self) -> list[str]:
        """CalculiX *CONDUCTIVITY in the mm/N/MPa consistent unit system.

        Config stores k in W/(m.K); the deck needs W/(mm.K) = W/(m.K) / 1000.
        Getting this wrong scales every temperature rise by 1000x, so the
        conversion lives here, once, and is unit-tested.
        """
        if self.k_ortho:
            kx, ky, kz = (v * MM_PER_M_INV for v in self.k_ortho)
            return ["*CONDUCTIVITY, TYPE=ORTHO", f"{kx:.6g},{ky:.6g},{kz:.6g}"]
        return ["*CONDUCTIVITY", f"{self.k * MM_PER_M_INV:.6g}"]


def build_materials(stack: dict, overrides: dict | None = None) -> dict[str, Material]:
    """Instantiate all material cards. `overrides` scales named properties for sensitivity runs,
    e.g. {'underfill_homog': {'cte': 1.3}} multiplies underfill CTE by 1.3."""
    raw = dict(stack["materials"])
    raw["tsv_homog"] = derive_tsv_homog(stack)
    bcb = stack["structural_bc"]["variants"]["BC_B"]
    raw["support_foundation"] = {"status": "PROVISIONAL", "elastic_type": "iso",
                                 "E": bcb["E"], "nu": bcb["nu"],
                                 "cte": bcb["cte"], "k": bcb["k"]}
    overrides = overrides or {}
    out: dict[str, Material] = {}
    for name, m in raw.items():
        et = m.get("elastic_type", "iso")
        scale = overrides.get(name, {})

        def g(key, default=None):
            if key not in m:
                return default
            val, _st = _v(m[key])
            return val * scale.get(key, 1.0) if isinstance(val, (int, float)) else val

        out[name] = Material(
            name=name, status=m.get("status", "ASSUMPTION"), elastic_type=et,
            cte=g("cte"), k=g("k"),
            E=g("E"), nu=g("nu"),
            C11=(m.get("C11", 0) * scale.get("E", 1.0)) if et == "ortho" else None,
            C12=(m.get("C12", 0) * scale.get("E", 1.0)) if et == "ortho" else None,
            C44=(m.get("C44", 0) * scale.get("E", 1.0)) if et == "ortho" else None,
            k_ortho=(m.get("k_ortho", {}) or {}).get("value") if isinstance(m.get("k_ortho"), dict) else None,
        )
    return out


def open_decisions(stack: dict) -> list[str]:
    """Every OPEN_DECISION / PROVISIONAL in the stack, for the run manifest banner."""
    found: list[str] = []

    def walk(node, path=""):
        if isinstance(node, dict):
            if "status" in node and node["status"] in {"OPEN_DECISION", "PROVISIONAL"}:
                found.append(f"{node['status']:13s} {path}  = {node.get('value')!r}")
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(stack)
    return sorted(found)
