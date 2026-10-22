# VPD vs DVPD — terminology audit

Phase 0N Section G. Every definition below is quoted from a primary source held in full
in this repository or reachable in full. Where a source could not be read in full that is
stated and **no construction is inferred from its abstract**.

---

## 1. Source access status

| source | DOI | access |
|---|---|---|
| Krishnakumar *et al.*, "A Comprehensive Design Framework for Vertical Power Delivery in HPC" | `10.1109/TCPMT.2026.3724907` | **FULL TEXT HELD** — `research/phase0e/June2026_DVPD_arXiv2606.28837.pdf` (arXiv:2606.28837). This is the repository's "June-2026" reference. |
| Krishnakumar *et al.*, "Vertical Power Delivery for HPC Systems with Buck-Derived Regulators", ECTC 2024 | `10.1109/ECTC51529.2024.00364` | **FULL TEXT HELD** — repo root PDF |
| "Design Considerations for DC-DC Voltage Regulators in DVPD Systems", ISCAS 2024 | `10.1109/ISCAS58744.2024.10558456` | **FULL TEXT HELD** — repo root PDF |
| "Integrated Vertical Power Delivery – Review & Challenges" | `10.1109/TCPMT.2026.3716987` | metadata verified via Crossref; **full text NOT accessible** (no open copy; WebSearch blocked in this environment) |
| "Embedded Vertical PDN (EV-PDN) ... Over-1kW FC-BGA ... Over-1mm Thick-Core Organic Substrate", ECTC 2025 | `10.1109/ECTC51687.2025.00176` | metadata verified via Crossref; **full text NOT accessible** |
| "VPD for Emerging Packaging and Integration Platforms", SOCC 2023 | `10.1109/SOCC58585.2023.10256973` | metadata verified; **full text NOT accessible** |
| "A Vertical Power Delivery Architecture for HPC", TPEL 2025 | `10.1109/TPEL.2025.3531414` | metadata verified; **full text NOT accessible** |
| "Vertically Stacked Dual-Bus DC–DC Converter", TPEL 2025 | `10.1109/TPEL.2025.3532833` | metadata verified; **full text NOT accessible** |
| "Package Power Delivery ... 1 kW IVR in CCM-DCM Boundary Mode", ECTC 2024 | `10.1109/ECTC51529.2024.00054` | metadata verified; **full text NOT accessible** |

All nine DOIs resolve and the titles match those given in the brief.

---

## 2. The distinction, from primary sources

### Krishnakumar 2026 (TCPMT, held in full) — on **lumped VPD**

> "Electrically, although **lumped VPD architectures reduce routing loss, substantial
> voltage drop persists within the horizontal interconnects of the RDLs**, as current must
> travel long distances — **up to a quarter of the system perimeter** — between the VR
> output and distant POLs on the same or adjacent chiplets."

and on **DVPD**

> "To address these limitations, a **distributed vertical power delivery (DVPD)** is
> proposed. The architecture employs a **fine-pitch network of horizontally distributed
> VRs**, with VR components **vertically stacked across multiple power layers (PL)**,
> placing the VR outputs **just tens of microns from the on-chip POLs**."

> "in a DVPD system with M VRs, the per-VR output current is reduced to **Io/M** ... As M
> increases, the VR components move closer laterally, **shortening the intra-VR routing
> paths** and reducing conduction losses in the RDL network."

### ECTC 2024 (held in full) — independent confirmation

> "shortening the long PCB-to-POLs lateral distance (**aka vertical power delivery**)"

> "Albeit the significantly lower PCB-to-VR power dissipation with VPD, **the lateral high
> current path from the single VR output to the farthest POL on-chip remains long**,
> exhibiting prohibitively high conduction loss. Alternatively, **multiple VRs can be
> distributed below and/or along the periphery of the functional die, significantly
> shortening the individual VR-to-POL high-current paths.** With distributed VPD (DVPD),
> system-wide power efficiency becomes a strong complex function..."

---

## 3. Verdict on the proposed wording

The hypothesis put to this audit was that the distinguishing variable is **the spatial
distribution of conversion and the residual low-voltage/high-current lateral path**, not
mere proximity to the load. **Both held-in-full sources support that, in almost those
words, and both are explicit that VPD already converts near/below the die.**

Accordingly:

| wording | verdict |
|---|---|
| "VPD is far away; DVPD is near the POL" | **WRONG.** Both place conversion in/near the package below the load. ECTC 2024 defines VPD itself as *shortening the PCB-to-POL lateral distance*. |
| "DVPD is unrelated to VPD" | **WRONG.** DVPD is a *distributed form* of vertical power delivery; the sources treat it as addressing limitations *of* lumped VPD. |
| "The distinction is the spatial distribution of conversion and the residual lateral low-voltage path" | **CORRECT and source-supported** (both held sources). |
| "With lumped VPD the post-conversion 1 V current can still traverse a large lateral distance through package/interposer RDL" | **CORRECT** — Krishnakumar 2026 quantifies it as *up to a quarter of the system perimeter*. |
| "DVPD distributes conversion laterally so each VR output sits close to its POL; per-VR current is Io/M" | **CORRECT** — Krishnakumar 2026, verbatim mechanism and scaling. |

---

## 4. Allowed manuscript wording

**Permitted**

- "Vertical power delivery (VPD) converts in or near the package beneath the load,
  removing the long PCB-to-package lateral path."
- "In a lumped VPD implementation the post-conversion low-voltage, high-current rail can
  still traverse a substantial lateral distance through package or interposer RDL to reach
  spatially separated points of load [Krishnakumar2026DVPD; Sriharini_ECTC_24]."
- "Distributed VPD (DVPD) partitions conversion across many smaller VR cells placed
  laterally beneath or around their corresponding POL regions, so that high-voltage,
  low-current power is distributed laterally first and the resulting low-voltage,
  high-current path is short and predominantly local and vertical."
- "DVPD is best understood as a distributed form of vertical/integrated power delivery
  rather than a separate class."
- "With M distributed VRs the per-VR output current scales as I_o/M."

**Not permitted**

- Any phrasing implying VPD places conversion far from the load, or on the board.
- Any phrasing implying DVPD is the only architecture that converts near the POL.
- Any claim about the taxonomy in `10.1109/TCPMT.2026.3716987` ("Integrated Vertical Power
  Delivery – Review & Challenges"): **full text was not accessible to this audit.** Cite it
  for existence only, not for a definition.

---

## 5. Required manuscript change

The current introduction (lines 63–67) reads:

> "Distributed vertical power delivery (DVPD) answers this by partitioning conversion into
> many regulator cells placed immediately above, below or within the package, so that the
> high-current rail travels micrometres rather than millimetres."

This is **not wrong**, but it contrasts DVPD only against *direct lateral delivery* (LPD).
It never introduces **lumped VPD** as the intermediate, so a reader cannot see what
distribution adds over vertical conversion alone. The abstract has the same gap
("DVPD shortens the 1 V rail by converting close to the point of load").

**Action:** insert the lumped-VPD step so the taxonomy is explicit —
**LPD → lumped / integrated VPD → DVPD** — with the discriminating variable stated as the
residual lateral low-voltage path. Figure `fig_vpd_dvpd_taxonomy` is generated for this
purpose by `scripts/phase0n_make_taxonomy_figure.py`.
