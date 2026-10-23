# Architecture source papers — manifest

The PDFs supplied for Phase 0N-R/0N-S live in `Architecture_Papers/`, which is
**gitignored**. Two of the seven carry IEEE Xplore *"Authorized licensed use limited to:
Argonne National Laboratory … Restrictions apply"* watermarks, so the folder is kept
locally rather than redistributed — the same policy already applied to `results/Papers/`
and to the EPC datasheets read in Phase 0N-R.

This manifest records what was read, so every claim remains traceable without the files.

| file | work | DOI / identifier | access class | publisher watermark | read in full? | used for |
|---|---|---|---|---|---|---|
| `Power_Noise_and_Near-Field_EMI_...pdf` | Xu, Vaisband, Sizikov, Li, Friedman, IEEE TCPMT 9(4):712–718, 2019 | `10.1109/TCPMT.2019.2903285` | **peer-reviewed** | **YES (7 hits)** | yes | the peer-reviewed bottom-side package VR precedent: BGA power pins feed the VR, LV current travels vertically bottom→top, 16 vs 28 metal layers, bottom-side area congestion, pinout change |
| `A_Comprehensive_Design_Framework_...pdf` | Krishnakumar *et al.*, IEEE TCPMT 2026 | `10.1109/TCPMT.2026.3724907` (arXiv 2606.28837) | **peer-reviewed** | no | yes | DVPD definition, lumped-VPD lateral-path limitation, `I_o/M`, the backside-stacked-chiplet sentence, Table III geometry; also held at `research/phase0e/` |
| `2309.10141v1.pdf` | Krishnakumar & Partin-Vaisband, SOCC 2023 | `10.1109/SOCC58585.2023.10256973` | **peer-reviewed** (arXiv OA) | no | yes | the four VPD architectures A0–A3; **Z1 maps onto A2**; none of A0–A3 is a land-side construction |
| `Design_Space_Exploration_...pdf` | Hossen *et al.*, 2020 | arXiv:2008.03124 | **preprint** | no | partial | backside-of-package VRM as an analysed configuration |
| `Integrated_Vertical_Power_Delivery__Review_amp_Challenges.pdf` | Swaminathan *et al.*, IEEE TCPMT 2026 | `10.1109/TCPMT.2026.3716987` | **peer-reviewed review** | **YES (18 hits)** | no | not used — no claim drawn from it |
| `56585-package-voltage-regulators-...pdf` | Meyer, Moghimi, Sturcken, IMAPS 2019 | `10.4071/2380-4505-2019.1.000438` | peer-reviewed (industry), open | no | no | context only: thin-film-inductor PVRs below 0.2 mm |
| `micromachines-14-01149.pdf` | Wang *et al.*, Micromachines 14(6):1149, 2023 | `10.3390/mi14061149` | peer-reviewed review, open | no | partial | secondary discussion of top/bottom VR placement; Xu 2019 cited for the primary result |

## Patents (fetched from Google Patents, not stored)

| patent | assignee | used for | class |
|---|---|---|---|
| `US20260059645A1` | ARM | die on one substrate face, VIVR on the opposite face disposed at least partially in a PCB hole; BGA / pillars / socket attach; multiple assemblies; ≥ 1 kW; heat sink dissipating through the cutout | **patent — industry construction precedent, not demonstrated hardware** |
| `US20250233088A1` | Intel | VR chiplet on the interposer land side; motherboard "cutoff region 221"; no-cutout embodiment also contemplated; ganged chiplets; package-embedded inductors | **patent — same caveat** |

**Neither patent gives a single dimension.** Every dimension in the Phase 0N-S documents is
derived from our own sourced component heights and the framework's BGA/PCB values.

## PCB fabrication sources (web, not stored)

IPC-2221A; UGPCB 18-layer server PCB (2.4 mm ±10 %); Schweizer Electronic standard
multilayer 0.6–3.2 mm and higher-standard 0.2–4.2 mm; PCBWay capabilities; JLCPCB
capabilities; Isola 370HR/IS410 to 3.2 mm; Würth Elektronik DEVICE.embedding (3.2 mm max
final thickness, 2663 µm max embedded component height). **All vendor/standards evidence,
none peer-reviewed** — classified as such in `research/PCB_THICKNESS_Z2_AUDIT.md`.
