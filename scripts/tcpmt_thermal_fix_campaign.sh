#!/usr/bin/env bash
# TCPMT revision -- the regeneration campaign after the thermal-model corrections:
#
#   1 cold-plate Nu: Shah & London three-wall H1 fit, short wall adiabatic (was the long-wall
#     table)                                              scripts/phase0m/cooling.py
#   2 water properties at the bulk mean temperature (was ~50 C), entrance + plenum dp
#   3 top plate: streamwise-sink coefficient in production (caloric double count removed)
#                                                         final_closure_physical_etm.TOP_PLATE_COEFF
#   4 cooling B: every second plate sized to the top plate's coolant rise, pumping per plate
#                                                         final_closure_physical_etm.BOTTOM_PLATE_RULE
#   5 converter-tier cards by unit-cell homogenization    scripts/tcpmt_converter_cards.py
#   6 die_T_max_C / die_T_mean_C in every case file
#   7 die hot-spot map variant (die_hotmap_*)
#
# EVERY E-T case changes (1-3, 5 act on all of them), so every solver stage is repeated. This
# file is the run list; it is not executed by the agent that wrote it. Lanes are independent
# except where noted ("after"). Thread budget per run: FC_THREADS (default 2 here).
#
# Usage:  nohup nice -n 10 scripts/tcpmt_thermal_fix_campaign.sh LANE &
#   LANE = cards | production | ladder | cooling | legacy | review | classb | z3land |
#          fields | local | references | derived
# Log:    $HVR_SCRATCH/thermal_fix_<lane>.log
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export HVR_SCRATCH=${HVR_SCRATCH:-/home/beams0/SABDELZAHER/ETM_project/scratch}
export HVR_FIELDS=${HVR_FIELDS:-$HVR_SCRATCH/fields}
export JOINT_BAND_FRAC=0.16666666666666666
export FC_THREADS=${FC_THREADS:-2} FC_POOL_MAX=${FC_POOL_MAX:-6}
export SOURCE_DATE_EPOCH=1793000000
LANE=${1:-}
LOG=$HVR_SCRATCH/thermal_fix_${LANE}.log

run() {   # run "label" cmd...
    local label=$1; shift
    echo "=== $(date '+%F %T') START $label" >> "$LOG"
    if "$@" >> "$LOG" 2>&1; then
        echo "=== $(date '+%F %T') DONE  $label" >> "$LOG"
    else
        echo "!!! $(date '+%F %T') FAILED $label (exit $?)" >> "$LOG"
        return 1
    fi
}
P="ITERATIVE CHOLESKY"

case "$LANE" in
cards)       # seconds; first, so the record matches the code the solvers will import
    run "converter cards (both designs)" python scripts/tcpmt_converter_cards.py
    run "cooling spec (plate only; tiers re-read in 'derived')" python scripts/tcpmt_cooling_spec.py
    ;;
production)  # production mesh r21 with mechanics: the paper's cases
    run "production Z1/Z2/Z3 HV-S0" python scripts/final_closure_physical_etm.py \
        "Z1:HV_S0:1.1:r21:$P:2" "Z2:HV_S0:1.1:r21:$P:2" "Z3:HV_S0:1.1:r21:$P:2"
    run "production Z1/Z2 HV-S1, Z2BF control HV-S0" python scripts/final_closure_physical_etm.py \
        "Z1:HV_S1:1.1:r21:$P:2" "Z2:HV_S1:1.1:r21:$P:2" "Z2BF:HV_S0:1.1:r21:$P:2"
    run "production Z1/Z2 HV-S2" python scripts/final_closure_physical_etm.py \
        "Z1:HV_S2:1.1:r21:$P:2" "Z2:HV_S2:1.1:r21:$P:2"
    ;;
ladder)      # nested mesh ladder around r21 (mesh-convergence statements)
    run "mesh ladder r11/r12" python scripts/final_closure_physical_etm.py \
        "Z1:HV_S0:1.1:r11:$P:1" "Z2:HV_S0:1.1:r11:$P:1" \
        "Z1:HV_S0:1.1:r12:$P:1" "Z2:HV_S0:1.1:r12:$P:1"
    run "mesh ladder r31" python scripts/final_closure_physical_etm.py \
        "Z1:HV_S0:1.1:r31:$P:2" "Z2:HV_S0:1.1:r31:$P:2" "Z3:HV_S0:1.1:r31:$P:2"
    ;;
cooling)     # the three cooling tiers (A, B production rule; I = interface-free bounds)
    run "cooling A (Z3 top only) and B (all), I (Z2)" python scripts/final_closure_sensitivity.py \
        z3_top_only z1_bottom_plate_tim z2_cooled_tim z3_plate_tim z2_cooled
    ;;
legacy)      # the superseded settings, one at a time, on the production tiers
    run "legacy thermal-model settings A" python scripts/final_closure_sensitivity.py \
        conv_k_legacy nu_legacy_table props_legacy_50C plate_caloric_legacy wall_viscosity
    run "legacy full-flow bottom plates" python scripts/final_closure_sensitivity.py \
        z1_bottom_plate_tim_fullflow z2_cooled_tim_fullflow z3_plate_tim_fullflow \
        z2_cooled_fullflow z3_plate_fullflow
    for t in A B; do
        for a in Z1 Z2 Z3; do
            run "caloric legacy $a $t" python scripts/tcpmt_review_variants.py caloric "$a" "$t"
        done
    done
    ;;
review)      # review variants on both cooling tiers ('after' cooling for the B bases)
    for t in A B; do
        for a in Z1 Z2 Z3; do
            [ "$t" = A ] && [ "$a" = Z3 ] || \
                run "die hot spot 3:1 $a $t" python scripts/tcpmt_review_variants.py hotspot "$a" "$t"
            run "die hot-spot map $a $t" python scripts/tcpmt_review_variants.py hotmap "$a" "$t"
            run "implemented decoupling $a $t" python scripts/tcpmt_review_variants.py sdec "$a" "$t"
        done
        for m in ratedcf ratedcfref ratedcfmax ratedcfmaxref; do
            run "rated flying caps (A1) $m $t" python scripts/tcpmt_review_variants.py "$m" Z1 "$t"
        done
    done
    # TIM warpage feedback: AFTER 'fields' (it starts from the collected converged fields)
    ;;
feedback)    # after 'fields'
    for t in A B; do
        for a in Z1 Z2 Z3; do
            run "TIM warpage feedback $a $t" python scripts/tcpmt_review_variants.py feedback "$a" "$t"
        done
    done
    ;;
classb)      # every class-B sensitivity of the robustness map (mech-only kinds 'after' fields)
    run "class-B full variants" python scripts/final_closure_sensitivity.py \
        tsv_min tsv_mid f2_void attach_sparse attach_sparse_stiff attach_dense attach_h20 \
        attach_h40 attach_sn attach_eng_p34 attach_eng_p37 attach_eng_p41 f1_sidewall_filled \
        z1_tier_reference icepak_equivalent board_hbot100 board_hbot500 board_h1 \
        board_h0_h1grid gan_k_half board_t3p2 board_eta025 board_eta075 conv_k_tenth \
        pad_drop bga_depop feed_heat_at_crossover
    ;;
classb_mech) # after 'fields': mechanics-only variants on the converged production fields
    run "class-B mechanics-only variants" python scripts/final_closure_sensitivity.py \
        attach_stiff attach_uf_soft attach_uf_stiff conv_E80_a4 conv_E80_a10 conv_E160_a4 \
        conv_E160_a10
    run "local response at every variant's critical joint" \
        python scripts/final_closure_sensitivity.py --local
    ;;
z3land)      # Z3 1-V spreading in the coupled ledger (the Z3 entries of cooling A/B)
    for v in z3_land_t40_A_fvmap z3_land_t40_B_fvmap z3_land_t40_A z3_land_t40_B \
             z3_land_t10_B z3_land_t20_B z3_land_t100_B z3_land_t40_B_noplane \
             z3_land_t10_B_fvmap z3_land_t20_B_fvmap z3_land_t100_B_fvmap; do
        run "z3 land $v" python scripts/tcpmt_z3land_variants.py run "$v"
    done
    ;;
fields)      # after 'production' (+ 'cooling' for the variant fields the feedback needs)
    run "collect fields" python scripts/final_closure_collect_fields.py \
        Z1:HV_S0 Z2:HV_S0 Z3:HV_S0 Z1:HV_S1 Z2:HV_S1
    run "collect variant fields (cooling tiers)" python scripts/tcpmt_collect_variant_fields.py \
        Z3:z3_top_only Z1:z1_bottom_plate_tim Z2:z2_cooled_tim Z3:z3_plate_tim Z2:z2_cooled
    ;;
local)       # after 'fields'
    run "direct-feed crossover" python scripts/final_closure_direct_feed.py
    run "local temporal study" python scripts/final_closure_local_mesh.py --temporal &&
    run "local cycle study" python scripts/final_closure_local_mesh.py --cycles &&
    run "local mesh study" python scripts/final_closure_local_mesh.py
    for s in HV_S0 HV_S1 HV_S2; do
        run "local solder $s" python scripts/final_closure_local_solder.py "$s"
    done
    ;;
references)  # after 'fields': matched thermal references on the corrected model
    for a in Z1 Z2; do
        run "MOOSE thermal column $a" python scripts/reference_tools/moose_thermal_column.py "$a"
        run "AEDT thermal column $a" timeout 5400 \
            python scripts/reference_tools/thermal_column_benchmark.py "$a" HV_S0
    done
    run "complete-package CalculiX vs MOOSE" python scripts/tcpmt_fullpkg_verify.py Z1 Z2 Z3
    ;;
derived)     # after everything above: records that read the case files
    run "cooling spec (per-case plates)" python scripts/tcpmt_cooling_spec.py
    run "platform-inclusive loss" python scripts/tcpmt_platform.py
    run "feasibility (die limit, components)" python scripts/tcpmt_feasibility.py
    run "layer temperatures" python scripts/tcpmt_layer_temperatures.py
    run "uncertainty" python scripts/tcpmt_uncertainty.py
    run "manuscript macros" python scripts/tcpmt_manuscript_macros.py
    run "final-closure rebuild" bash scripts/final_closure_rebuild.sh
    ;;
*)
    echo "usage: $0 cards|production|ladder|cooling|legacy|review|feedback|classb|classb_mech|z3land|fields|local|references|derived"
    exit 2 ;;
esac
echo "=== LANE $LANE COMPLETE $(date '+%F %T')" >> "$LOG"
