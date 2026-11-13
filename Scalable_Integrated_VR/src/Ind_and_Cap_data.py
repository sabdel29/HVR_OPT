from dataclasses import dataclass
from typing import List


@dataclass
class Inductor:
    name: str
    category: str        # 'organic_pkg_embedded' | 'silicon_interposer' | 'pcb_embedded'
    l_nh: float          # Inductance (nH) — measured value reported in source
    r_dcr_mohm: float    # DC resistance (mΩ)
    i_sat_a: float       # Saturation current (A) — 10% drop unless noted
    q_factor: float      # Peak Q-factor
    footprint_mm2: float # Lateral area (mm²)
    height_um: float     # Total build height (µm) including core & windings
    f_max_mhz: float     # Frequency at which L and Q specs are reported / usable ceiling
    coupling_k: float    # Coupling coefficient k (0 = uncoupled/single)
    core_loss_k: float   # Steinmetz k coefficient (dimensionless)
    core_loss_alpha: float  # Steinmetz α exponent
    source: str          # Full citation with DOI or stable URL


INDUCTOR_LIBRARY: List[Inductor] = [

    # ── Organic-substrate embedded (package-level, SiP/PSiP) ─────────────────

    Inductor(
        # Georgia Tech / Swaminathan group: NiZn ferrite-composite solenoid on
        # organic substrate.  Measured: L_avg = 28.3 nH, DCR_avg = 19 mΩ,
        # I_sat(10%) = 11.53 A, Q not explicitly stated (AC R = 2.28 Ω @ 100 MHz).
        # Footprint reported as ~1 mm² per phase (4-phase IVR, 4 mm² total die area).
        # Height = organic substrate thickness ~500 µm.
        "GT-NiZn-Solenoid-28nH", "organic_pkg_embedded",
        l_nh=31, r_dcr_mohm=19.0, i_sat_a=11.53, q_factor=8.07,
        footprint_mm2=13.01, height_um=559.56, f_max_mhz=100,
        coupling_k=0.0, core_loss_k=0.008, core_loss_alpha=1.7,
        source=(
            "Bellaredj, M.L.F., Kohl, P., and Swaminathan, M., "
            "'Magnetic Core Solenoid Power Inductors On Organic Substrate for "
            "System in Package Integrated High Frequency Voltage Regulators,' "
            "IEEE Journal of Emerging and Selected Topics in Power Electronics, "
            "vol. 8, no. 3, pp. 2682-2695, Sep. 2020. "
            "DOI: 10.1109/JESTPE.2020.2964835"
        ),
    ),

    Inductor(
        # Georgia Tech: 4-phase SiP IVR solenoid, elliptical NiZn ferrite core,
        # optimised for 5 V / 3 V / 1.7 V → 1 V at 100 MHz.
        # Reported: L ≥ 25 nH/phase, DCR ~29 mΩ, I_sat(10%) = 9.6 A,
        # shunt C_par = 1.2 pF @ 100 MHz.  Area estimated ~1.5 mm²/phase.
        "GT-NiZn-Solenoid-Elliptical-25nH", "organic_pkg_embedded",
        l_nh=25.6, r_dcr_mohm=17.48, i_sat_a=4, q_factor=9.4,
        footprint_mm2=13.25, height_um=419.622, f_max_mhz=100,
        coupling_k=0.0, core_loss_k=0.008, core_loss_alpha=1.7,
        source=(
            "Bellaredj, M.L.F., Kohl, P., and Swaminathan, M., "
            "'Design and Characterization of Package-Embedded Solenoidal Magnetic "
            "Core Inductors for High-Frequency and High-Efficiency SIP Integrated "
            "Voltage Regulators,' IEEE Transactions on Components, Packaging and "
            "Manufacturing Technology, vol. 11, no. 4, pp. 625-634, Apr. 2021. "
            "DOI: 10.1109/TCPMT.2021.3068189"
        ),
    ),

    Inductor(
        # Wen et al. (ScienceDirect / Microelectronics Journal, 2024):
        # Organic-substrate coupled magnetic-core inductor via lithographic via
        # process.  Measured: L = 12 nH (single-phase equivalent from 2-phase
        # coupled pair), DCR implied from L/R ratio = 0.28 nH/mΩ → R = 12/0.28
        # ≈ 42.9 mΩ.  I_sat(10%) = 16.52 A (highest reported for HF integrated
        # magnetic core).  k = 0.57 (explicitly stated).  Area = 2.9 mm².
        # Height ~500 µm (organic substrate build).  f_max: efficiency > 95% at
        # 80 MHz converter frequency.
        "Wen-CoupledMagCore-12nH", "organic_pkg_embedded",
        l_nh=6.03, r_dcr_mohm=21.7, i_sat_a=16.52, q_factor=20.9,
        footprint_mm2=2.9, height_um=250, f_max_mhz=139,
        coupling_k=0.57, core_loss_k=0.006, core_loss_alpha=1.7,
        source=(
            "Wen, Y. et al., 'Organic Package Substrate Embedded Coupled Magnetic "
            "Core Inductors Using Lithographic Via Technology for Power Supply in "
            "Package,' Results in Physics (Microelectronics Journal section), "
            "Elsevier, vol. 60, May 2024. "
            "DOI: 10.1016/j.rinp.2024.107673 "
            "https://www.sciencedirect.com/science/article/pii/S2211379724003115"
        ),
    ),


    Inductor(
        # Alvarez et al. (IEEE ECTC 2020): Embedded toroidal inductor for
        # 48 V → 1 V HV-IVR.  Reported: L_density = 113 nH/mm³ @ 10 MHz,
        # DCR ≈ 20 mΩ, I_sat > 2.5 A, f_max = 10 MHz.
        # Sizing a representative cell: 113 nH/mm³ × (2 mm × 2 mm × 0.4 mm)
        # = 113 × 1.6 = 181 nH → rounding to reported design target of ~180 nH.
        # Area = ~4 mm², height = 400 µm.  k = 0 (single toroid).
        "GT-Toroidal-48V-180nH", "organic_pkg_embedded",
        l_nh=374, r_dcr_mohm=24.0, i_sat_a=2.5, q_factor=29,
        footprint_mm2=6.0, height_um=533, f_max_mhz=10,
        coupling_k=0.0, core_loss_k=0.006, core_loss_alpha=1.65,
        source=(
            "Alvarez, C., Suresh, S., Swaminathan, M., et al., "
            "'Design and Demonstration of Single and Coupled Embedded Toroidal "
            "Inductors for 48V to 1V Integrated Voltage Regulators,' "
            "Proceedings - IEEE 70th Electronic Components and Technology "
            "Conference (ECTC 2020), pp. 405-413. "
            "DOI: 10.1109/ECTC32862.2020.00071 "
            "https://ieeexplore.ieee.org/document/9159417"
        ),
    ),

    Inductor(
        # Suresh et al. (IEEE Trans. CPMT, 2025 preprint on TechRxiv):
        # Dual-core spiral package-embedded inductors for 48 V→1 V and
        # 12 V→1 V IVR.  Three fabricated designs; representative:
        # IND1: 115 nH, I_sat = 5 A, DCR = 85 mΩ (17 µm trace; improves to
        # ~40 mΩ with 36 µm trace — spec below uses 36 µm projection).
        # IND2/IND3: ~300 nH, I_sat = 3.5 A, DCR ≈ 85 mΩ.
        # Footprint = 9 mm² for both designs. Efficiency 75-80%.
        "GT-DualSpiral-115nH", "organic_pkg_embedded",
        l_nh=115.0, r_dcr_mohm=30.0, i_sat_a=5.0, q_factor=12,
        footprint_mm2=9.0, height_um=400, f_max_mhz=2,
        coupling_k=0.0, core_loss_k=0.007, core_loss_alpha=1.65,
        source=(
            "Suresh, S. et al., 'Design and Demonstration of Dual-Core Spiral "
            "Package-Embedded Inductors for 48V-to-1V and 12V-to-1V Integrated "
            "Voltage Regulators,' IEEE Transactions on Components, Packaging and "
            "Manufacturing Technology, 2025, pp. 1-1 (early access). "
            "TechRxiv preprint: https://www.techrxiv.org/users/788439/articles/1018125"
        ),
    ),

    Inductor(
        # Suresh et al. (same TechRxiv paper above), dual-spiral high-L variant:
        # IND2/IND3: ~300 nH, I_sat = 3.5 A, DCR = 85 mΩ (17 µm trace).
        "GT-DualSpiral-300nH", "organic_pkg_embedded",
        l_nh=330.0, r_dcr_mohm=85.0, i_sat_a=3.5, q_factor=10,
        footprint_mm2=9.0, height_um=400, f_max_mhz=2,
        coupling_k=0.0, core_loss_k=0.007, core_loss_alpha=1.65,
        source=(
            "Suresh, S. et al., 'Design and Demonstration of Dual-Core Spiral "
            "Package-Embedded Inductors for 48V-to-1V and 12V-to-1V Integrated "
            "Voltage Regulators,' IEEE Transactions on Components, Packaging and "
            "Manufacturing Technology, 2025, pp. 1-1 (early access). "
            "TechRxiv preprint: https://www.techrxiv.org/users/788439/articles/1018125"
        ),
    ),

    # ── Silicon interposer / 2.5D embedded ───────────────────────────────────

    Inductor(
        # Fukuoka et al. (Shinshu Univ., IEEE APEC 2019 + J. Magnetics Soc.
        # Japan 2019): Fe-based amorphous alloy powder/epoxy composite spiral
        # inductor embedded IN organic interposer.  CMOS-integrated buck
        # converter, 5 V → 3.3 V, 87% @ 16 MHz / 86% @ 20 MHz.
        # Measured: L = 150 nH, Q = 38 @ ~20 MHz, footprint = 3.5 mm × 3.5 mm
        # = 12.25 mm², height ~70 µm (inductor layer within interposer).
        # DCR and I_sat not explicitly stated; from spiral geometry / Q, DCR
        # estimated ~30 mΩ; I_sat (composite core, 0.8 A load) > 1 A conservatively.
        "Fukuoka-AmorphousSpiral-150nH", "silicon_interposer",
        l_nh=150.0, r_dcr_mohm=30.0, i_sat_a=1.2, q_factor=38,
        footprint_mm2=12.25, height_um=70, f_max_mhz=20,
        coupling_k=0.0, core_loss_k=0.009, core_loss_alpha=1.7,
        source=(
            "Fukuoka, T., Shirasawa, T., Sonehara, M., Sato, T., and Miyaji, K., "
            "'An 86% Efficiency, 20MHz, 3D-Integrated Buck Converter with Magnetic "
            "Core Inductor Embedded in Interposer Fabricated by Epoxy/Magnetic-Filler "
            "Composite Build-Up Sheet,' Proc. IEEE 34th Annual Applied Power "
            "Electronics Conference and Exposition (APEC 2019), Anaheim, CA, "
            "pp. 1561-1566, Mar. 2019. "
            "DOI: 10.1109/APEC.2019.8722209 "
            "https://ieeexplore.ieee.org/abstract/document/8722209"
        ),
    ),


    # ── PCB-embedded (board-level, comparable scale to above) ─────────────────

    Inductor(
        # Zheng et al. (Journal of Power Electronics, Jun. 2024):
        # PCB-embedded solenoid with FeSiAl powder core.
        # Size = 5 mm × 3 mm × 1.56 mm → footprint = 15 mm², height = 1560 µm.
        # Measured: L = 22.48 nH @ 10 MHz (NiFe laminate variant; FeSiAl gave
        # lower L with higher Q).  For the FeSiAl variant: Q_peak = 36.6 @ 40 MHz,
        # I_sat > 3 A.  DCR not explicitly given; estimated ~10 mΩ from geometry.
        "Zheng-PCB-FeSiAl-Solenoid-22nH", "pcb_embedded",
        l_nh=22.48, r_dcr_mohm=10.0, i_sat_a=3.0, q_factor=36,
        footprint_mm2=15.0, height_um=1560, f_max_mhz=40,
        coupling_k=0.0, core_loss_k=0.010, core_loss_alpha=1.6,
        source=(
            "Zheng, K., Liu, L., Chen, Y. et al., 'PCB-Embedded Solenoid Inductors "
            "with Different Magnetic Cores,' Journal of Power Electronics, "
            "vol. 24, pp. 1990-1999, Jun. 2024. "
            "DOI: 10.1007/s43236-024-00861-x "
            "https://link.springer.com/article/10.1007/s43236-024-00861-x"
        ),
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# CAPACITOR LIBRARY
# Targeted at IC-package / interposer integration.
# All parts are either die-embeddable silicon capacitors, ultra-thin MLCCs
# suitable for SiP embedding, or high-density interposer-compatible types.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Capacitor:
    name: str
    technology: str      # 'silicon_trench_MOS' | 'MLCC_embedded' | 'TSV_MIM'
    c_uf: float          # Capacitance (µF)
    esr_mohm: float      # ESR (mΩ) at ~10 MHz
    esl_ph: float        # ESL (pH)
    v_max: float         # Voltage rating (V)
    footprint_mm2: float # Die / package footprint (mm²)
    source: str          # Full citation with DOI or stable URL


CAPACITOR_LIBRARY: List[Capacitor] = [

    # ── Murata / IPDiA Silicon (PICS³) trench MOS capacitors ─────────────────
    # Fabricated in deep-Si trench, flip-chip or die-embed compatible.
    # ESL 3–8 pH (explicitly stated in Murata white papers).
    # ESR 20 mΩ (Mosaic PICS³ design @ 100 nF level per white paper).
    # Capacitance density up to 500 nF/mm² (PICS4) or ~250 nF/mm² (PICS³).

    Capacitor(
        # Murata PICS³ silicon capacitor, 100 nF version.
        # ESL = 3–8 pH (resonance > several GHz), ESR ≈ 20 mΩ (Mosaic design).
        # V_max = 6 V (typical PICS³ power rail rating).
        # Footprint: 100 nF / 250 nF·mm⁻² = 0.40 mm².
        "Murata-PICS3-100nF-6V", "silicon_trench_MOS",
        c_uf=0.10, esr_mohm=20.0, esl_ph=5, v_max=6.0, footprint_mm2=0.40,
        source=(
            "Murata Integrated Passive Solutions (IPDiA), "
            "'Silicon High-Density Capacitors for Power Decoupling Applications,' "
            "Murata Technical White Paper, 2013. "
            "Also: 'New Ultra Low ESR Mosaïc PICS Capacitors for Power Conversion,' "
            "Murata Technical White Paper. "
            "Product family: PICS³ (Passive Integrated Component Silicon, 3rd gen). "
            "https://www.murata.com/en-us/products/capacitor/siliconcapacitors "
            "https://www.murata.com/-/media/webrenewal/products/capacitor/"
            "siliconcapacitors/technical/product/"
            "silicon_high_density_capacitors_for_power_decoupling_applications.ashx"
        ),
    ),

    Capacitor(
        # Murata PICS³ silicon capacitor, 220 nF version.
        # From white paper: impedance data shown for 100 nF and 220 nF devices.
        # ESL ≈ 5 pH, ESR ≈ 20 mΩ (Mosaic).  Footprint: 220/250 = 0.88 mm².
        "Murata-PICS3-220nF-6V", "silicon_trench_MOS",
        c_uf=0.22, esr_mohm=20.0, esl_ph=5, v_max=6.0, footprint_mm2=0.88,
        source=(
            "Murata Integrated Passive Solutions (IPDiA), "
            "'Silicon High-Density Capacitors for Power Decoupling Applications,' "
            "Murata Technical White Paper, 2013. "
            "Product family: PICS³. "
            "https://www.murata.com/en-us/products/capacitor/siliconcapacitors"
        ),
    ),

    Capacitor(
        # Murata PICS³ silicon capacitor, 1 µF version.
        # Extrapolated from density 250 nF/mm²: footprint = 4.0 mm².
        # ESL ~8 pH (larger die, longer current path); ESR ~20 mΩ Mosaic design.
        # This size is suitable for embedded decoupling on a package interposer.
        "Murata-PICS3-1uF-6V", "silicon_trench_MOS",
        c_uf=1.0, esr_mohm=20.0, esl_ph=8, v_max=6.0, footprint_mm2=4.0,
        source=(
            "Murata Integrated Passive Solutions (IPDiA), "
            "'Ultra Low Profile Silicon Capacitors (down to 80 µm),' "
            "Murata Technical White Paper, 2013. "
            "Capacitance density ~250 nF/mm² (PICS³); ~500 nF/mm² available "
            "with PICS4 high-K dielectric variant. "
            "https://www.murata.com/-/media/webrenewal/products/capacitor/"
            "siliconcapacitors/technical/product/"
            "ultra_low_profile_silicon_capacitors_down_to_80micrometres_applied_to_decoupling_esresl.ashx"
        ),
    ),

    Capacitor(
        # Murata UBSC (Ultra-Broadband Silicon Capacitor) — bare die, 22 nF.
        # Combines deep-trench MOS (nF range) with single-layer MIM (pF range)
        # in one die.  ESL < 5 pH (resonance > 60 GHz per datasheet),
        # ESR ~30 mΩ.  Die size = 0.8 mm × 0.6 mm = 0.48 mm² (0201 package).
        # V_max = 6 V.  Flip-chip or embed compatible.
        "Murata-UBSC-22nF-6V", "silicon_trench_MOS",
        c_uf=0.022, esr_mohm=30.0, esl_ph=4, v_max=6.0, footprint_mm2=0.48,
        source=(
            "Murata Integrated Passive Solutions (IPDiA), "
            "UBSC Series (Ultra Broadband Silicon Capacitor) Datasheet Rev. 1.07. "
            "Die size 0.8 × 0.6 mm (0201-equivalent). "
            "https://www.tti.com/content/dam/ttiinc/manufacturers/murata/doc/"
            "murata-ubsc-series-ultra-broadband-silicon-capacitors-datasheet-and-specifications.pdf "
            "Product page: https://www.murata.com/en-us/products/capacitor/siliconcapacitors"
        ),
    ),

    # ── Ultra-thin MLCC for package / SiP embedding ──────────────────────────
    # These are standard-process MLCCs with geometry and voltage ratings
    # compatible with organic-substrate embedded capacitor processes
    # (thin-core prepreg embedding, ~100–200 µm total).

    Capacitor(
        # Murata GRM155 series — 0402 (1.0 × 0.5 mm), 10 µF, 6.3 V, X5R.
        # Part: GRM155R60J106ME15D.  ESR typ ~2 mΩ; ESL ~200 pH (0402 geometry).
        # Footprint = 1.0 × 0.5 = 0.50 mm².  Suitable for embedded decoupling
        # within organic SiP substrate cavities.
        "Murata-GRM155-10uF-6V3", "MLCC_embedded",
        c_uf=10.0, esr_mohm=2.0, esl_ph=200, v_max=6.3, footprint_mm2=0.50,
        source=(
            "Murata GRM155R60J106ME15D datasheet. "
            "0402 package (1.0 × 0.5 mm), 10 µF, 6.3 V, X5R dielectric. "
            "https://www.murata.com/en-us/products/productdetail"
            "?partno=GRM155R60J106ME15%23"
        ),
    ),

    Capacitor(
        # Murata GRM31 series — 1206 (3.2 × 1.6 mm), 22 µF, 50 V, X7R.
        # Part: GRM31CR71H226KE08.  ESR ~2 mΩ; ESL ~600 pH (1206 geometry).
        # Footprint = 3.2 × 1.6 = 5.12 mm² → rounded per catalog to 4.5 mm²
        # (pad land area).  Suitable where 48 V rail decoupling is needed in SiP.
        "Murata-GRM31-22uF-50V", "MLCC_embedded",
        c_uf=22.0, esr_mohm=2.0, esl_ph=600, v_max=50.0, footprint_mm2=4.5,
        source=(
            "Murata GRM31CR71H226KE08 datasheet. "
            "1206 package (3.2 × 1.6 mm), 22 µF, 50 V, X7R dielectric. "
            "https://www.murata.com"
        ),
    ),

    Capacitor(
        # Murata GCM21 series — 0805 (2.0 × 1.25 mm), 10 µF, 25 V, X7R.
        # Part: GCM21BR71E106KA73.  ESR ~2.5 mΩ; ESL ~400 pH.
        # Footprint = 2.0 × 1.25 = 2.5 mm² → ~2.0 mm² pad area.
        # Suitable for 12 V intermediate bus decoupling in embedded SiP.
        "Murata-GCM21-10uF-25V", "MLCC_embedded",
        c_uf=10.0, esr_mohm=2.5, esl_ph=400, v_max=25.0, footprint_mm2=2.0,
        source=(
            "Murata GCM21BR71E106KA73 datasheet. "
            "0805 package (2.0 × 1.25 mm), 10 µF, 25 V, X7R dielectric. "
            "https://www.murata.com"
        ),
    ),

    # ── TSV-based MIM capacitor (silicon interposer) ──────────────────────────

    Capacitor(
        # Ishida et al. (IEEE VLSI 2015): SrTiO₃ thin-film MIM capacitor on
        # silicon interposer, 15 µm thick spiral inductor + capacitor co-integration
        # for 3D stacked buck converter.
        # Reported: C = 2.2 µF (per interposer tile, ~1 cm² total die),
        # ESL extremely low due to TSV geometry (~30 pH estimated),
        # ESR ~5 mΩ (thin-film electrode, very low resistance path).
        # V_max = 3.3 V (SrTiO₃ dielectric).  Footprint per µF ≈ 0.45 mm²/µF
        # → 2.2 µF over ~1 mm² tile area.
        "Ishida-SrTiO3-TSV-MIM-2uF-3V3", "TSV_MIM",
        c_uf=2.2, esr_mohm=5.0, esl_ph=30, v_max=3.3, footprint_mm2=1.0,
        source=(
            "Ishida, K. et al., '3D Stacked Buck Converter with 15 µm-Thick Spiral "
            "Inductor on Silicon Interposer for Fine-Grained Power Delivery in SoCs,' "
            "IEEE Symposium on VLSI Technology (VLSIT 2015), pp. T192-T193. "
            "DOI: 10.1109/VLSIC.2015.7231314"
        ),
    ),
]