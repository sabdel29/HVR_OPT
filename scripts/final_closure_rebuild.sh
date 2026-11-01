#!/usr/bin/env bash
# Regenerate every final-closure artifact from the solver outputs, in dependency order.
# Solver runs themselves (package network, physical ETM, local solder family, class-B
# sensitivities, references) are NOT repeated here; this rebuilds everything derived
# from them. Scratch output goes to ~/claude_scratch (never /tmp).
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
# one fixed timestamp for every generated PDF/SVG (matplotlib, cairo, pdfTeX): a rebuild of
# unchanged artifacts is then byte-identical
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-1793000000}" FORCE_SOURCE_DATE=1
SCR="${HVR_SCRATCH:-$HOME/claude_scratch/hvr_work}"
mkdir -p "$SCR"
python scripts/final_closure_literature_rules.py
python scripts/final_closure_provenance.py                    # lane/version consistency
python scripts/final_closure_vr_attach.py > /dev/null         # attach lattices, before its readers
python scripts/final_closure_accuracy_matrix.py
python scripts/final_closure_architecture_spec.py > /dev/null
python scripts/final_closure_package_figs.py                  # the manuscript converts some
python scripts/final_closure_direct_feed.py                   # crossover R*, needs Z1 mechanics
python scripts/final_closure_results.py
python scripts/final_closure_classB.py > /dev/null
python scripts/final_closure_results.py > /dev/null          # decision sees class B
python scripts/phase0nw/audit_physical_gates.py > /dev/null
python scripts/final_closure_gate_classes.py
python scripts/final_closure_manuscript_tables.py
python scripts/final_closure_manuscript_figure.py
python scripts/final_closure_manuscript_patch.py
python scripts/final_closure_results.py > /dev/null          # decision sees gates AND manuscript
python scripts/phase0nw/audit_physical_gates.py > /dev/null
python scripts/phase0mr3c/audit_manuscript.py > "$SCR/manuscript_audit.txt" \
  || { echo "MANUSCRIPT AUDIT FAILED"; grep FAIL "$SCR/manuscript_audit.txt"; exit 1; }
( cd manuscript && pdflatex -interaction=nonstopmode ETM_DVPD_JOURNAL_MANUSCRIPT.tex > /dev/null \
  && bibtex ETM_DVPD_JOURNAL_MANUSCRIPT > /dev/null \
  && pdflatex -interaction=nonstopmode ETM_DVPD_JOURNAL_MANUSCRIPT.tex > /dev/null \
  && pdflatex -interaction=nonstopmode ETM_DVPD_JOURNAL_MANUSCRIPT.tex > /dev/null ) \
  || { echo "MANUSCRIPT BUILD FAILED"; grep -n "^!" manuscript/ETM_DVPD_JOURNAL_MANUSCRIPT.log | head; exit 1; }
python scripts/final_closure_evidence.py
python scripts/prelim_make_figs.py > /dev/null
python scripts/prelim_make_figs_final.py
python scripts/final_closure_slide_charts.py
python scripts/visualize_rdl_geometry.py > /dev/null
python scripts/final_closure_tool_map.py
python scripts/prelim_build_deck.py
python scripts/prelim_figure_manifest.py
python scripts/prelim_qa_slides.py
echo "REBUILD COMPLETE"
