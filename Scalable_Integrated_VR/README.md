# Scalable Integrated Voltage Regulators for Data-Center Power Delivery

Design-space exploration and co-optimization framework for **vertical power delivery (VPD)**
in AI-accelerator packages — 48 V backplane down to sub-1 V at the point of load.

> **Salma Abdelzaher & Mohamed Gharib** — HiPerCAS Lab (Dr. Inna Partin-Vaisband),
> University of Illinois Chicago. Prepared for the **Qualcomm Innovation Fellowship (QIF)
> finals, March 2026**. See [`docs/`](docs/) for the full presentation script.

---

## 1. The problem

AI accelerators now draw kilowatts per package from a 48 V backplane, delivered to loads
at sub-1 V and extreme current density. In **conventional lateral delivery** the regulators
sit at the board or package edge, so current travels a long way to the die. That costs twice:

* resistive **IR drop** along the path, and
* path **inductance**, which adds a transient droop proportional to `L·di/dt`.

**Vertical power delivery** puts compact regulators directly beneath (or inside) the package,
shortening the path and cutting both penalties — and it enables per-region power management.

A plain buck converter cannot do 48 V → 1 V: the duty cycle is ~2 %, which is not practical.
The answer used here is a **hybrid VR (HVR)**: a **switched-capacitor (SC) stage** that steps
48 V to an intermediate rail, followed by a **multiphase buck** to 1 V. This repository
searches that design space exhaustively.

## 2. What the code actually computes

Three modelling layers, each optimized jointly rather than in isolation:

| Layer | What it models | Where |
|---|---|---|
| **HVR loss model** | Per-converter conduction, switching (HS/gate-drive/C_OSS), inductor DCR + core loss, under area and ripple constraints | `src/HVR_FULL_OPT_EPC_V2.py` |
| **PDN routing model** | Loss delivering current from each VR to each load segment — parallel-resistance network over Manhattan distances (GLSVLSI'24 model) | `src/Framework*.py` |
| **System co-optimization** | Sweeps VR **count**, **placement**, **topology**, **components** and **f_sw** together to find the optimum | `src/Framework_w_HVR_OPT_sizing_v2.py` |

The central trade-off the framework resolves: **more VRs → less routing loss, but less area
per VR → worse VR efficiency.** That produces a well-defined optimal VR count, and it differs
per architecture.

### Architecture parameterization

A candidate VR is described by `VRArchitecture(N, K, K_A, B_array, D, component_count)`:

* `N` — number of SC branches
* `K` — number of inductors (buck phases)
* `K_A` — how many of those inductors sit in phase A
* `B_array` — how many branches feed each inductor
* component count = `N` HS switches + `K` LS switches + `K` inductors + `(N-1)` flying caps

### Default operating point

| Parameter | Value |
|---|---|
| `V_in` → `V_out` | 48 V → 1 V |
| `I_out` | 30 A (20 A in the DSE studies) |
| Gate drive `V_gs` | 5 V |
| Current-ripple limit | `ΔI_out < 50 % · I_out` (40 % in DSE) |
| Voltage-ripple limit | `ΔV_out < 25 % · V_out` (5 % in DSE) |
| Area budget | `I_out / J_target`, with `J_target = 1 A/mm²` |
| `f_sw` sweep | 43 kHz → 200 MHz, 50 log-spaced points |

Devices come from **`EPC-Product-Table.csv`** (97 EPC GaN parts, 90 usable after filtering).
Passive libraries (integrated/embedded inductors and capacitors, with real citations) live in
`src/Ind_and_Cap_data.py` and inside the V2 engine.

## 3. Repository layout

```
Scalable_Integrated_VR/
├── README.md                    ← you are here
├── EPC-Product-Table.csv        ← GaN device library (INPUT — must stay at repo root)
├── src/          19 Python modules, kept flat   → see src/README.md
├── results/
│   ├── figures/  19 PNG plots                   → see results/README.md
│   ├── matlab/   .fig / .mat / .m artifacts
│   ├── slides/   generated .pptx decks
│   └── data/     exported result tables (.csv)
├── docs/         QIF presentation script (.docx/.pdf)
├── .venv/        Windows virtualenv, 384 MB — NOT usable on Linux (see §5)
├── .idea/        PyCharm project files
└── .git/         single "Starting_point" commit; most work is untracked
```

## 4. Running it

Every script is launched **from this directory** so that `EPC-Product-Table.csv`
resolves (all scripts open it by bare relative path):

```bash
cd Scalable_Integrated_VR
python3 src/HVR_FULL_OPT_EPC_V2.py            # single-VR HVR optimization
python3 src/dse_study_cases.py                # planar vs 3D-stacked design-space study
python3 src/Framework_w_HVR_OPT_sizing_v2.py  # system sweep: efficiency vs VR count
```

Modules import each other flat (`from HVR_FULL_OPT_EPC_V2 import ...`); because Python puts
the script's own directory first on `sys.path`, running `python3 src/<script>.py` keeps every
import working. Outputs are written to the **current directory**, so move new plots into
`results/` afterwards.

### ⚠ Python version — read this first

**The code needs Python ≥ 3.10.** `HVR_FULL_OPT_EPC.py` uses PEP-604 annotations
(`EPCDevice | None`), which are a syntax error at runtime on older interpreters.

On this machine the bare `python3` on `PATH` is **Python 3.8.16** (from the Mentor Calibre
install), and it fails with:

```
TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

An interactive shell alias masks this by pointing at a 3.12 conda build in *another user's*
home directory, so the same command can succeed interactively and fail in a script. Pin the
interpreter explicitly:

```bash
/home/beams/AMICELI/miniconda3/bin/python3 src/dse_study_cases.py   # 3.12, works today
```

Creating your own environment is the durable fix:

```bash
conda create -n hvr python=3.12 numpy pandas matplotlib scipy python-pptx lxml
```

Dependencies: `numpy`, `pandas`, `matplotlib`, `scipy`, plus `python-pptx` + `lxml` for the
PowerPoint exporters.

## 5. Known gotchas

| Issue | Detail |
|---|---|
| **`.venv/` is Windows-only** | Contains `Scripts/python.exe` and `*.pyd` (CPython 3.14, `win_amd64`). It is 384 MB of the repo's 389 MB and cannot run on Linux. Rebuild natively rather than trying to use it. |
| **`__pycache__/` at root is stale** | CPython 3.14 Windows bytecode for modules that now live in `src/`. Orphaned and safe to delete. |
| **Input CSV location is load-bearing** | 17 code sites hard-code `"EPC-Product-Table.csv"` as a bare relative path, so it resolves against the *working directory*, not the script. Keep it at the repo root and launch from there. |
| **`Framework_cowork_physical (1).py` is the newer file** | Despite the browser-style "(1)" name it is *ahead* of `Framework_cowork_physical.py`: it replaces the unbounded `k · L · f^α` core-loss term with a bounded ripple-based surrogate. Do not assume the un-suffixed file is current. |
| **Git history is nearly empty** | One commit (`Starting_point`) holding only `Framework.py` and `.idea/`. Everything else — both engines, all drivers, all results — is untracked. |

## 6. Where to look first

* **Understand the physics** → `docs/QIF Finals Presentation Script.pdf`, slides 5–8.
* **Understand the code** → [`src/README.md`](src/README.md) — engine families, version lineage, what supersedes what.
* **Understand the results** → [`results/README.md`](results/README.md) — every figure mapped to the script that produced it.
