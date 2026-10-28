#!/usr/bin/env bash
# Regenerate every final-closure artifact from the solver outputs, in dependency order.
# Solver runs themselves (package network, physical ETM, local solder, references) are
# NOT repeated here; this rebuilds everything derived from them.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH
python scripts/final_closure_literature_rules.py
python scripts/final_closure_accuracy_matrix.py
python scripts/final_closure_results.py
python scripts/phase0nw/audit_physical_gates.py > /dev/null
python scripts/final_closure_gate_classes.py
python scripts/final_closure_manuscript_tables.py
python scripts/final_closure_manuscript_figure.py
python scripts/final_closure_manuscript_patch.py
python scripts/final_closure_results.py > /dev/null          # decision sees gates AND manuscript
python scripts/phase0nw/audit_physical_gates.py > /dev/null
python scripts/phase0mr3c/audit_manuscript.py > /tmp/manuscript_audit.txt \
  || { echo "MANUSCRIPT AUDIT FAILED"; grep FAIL /tmp/manuscript_audit.txt; exit 1; }
( cd manuscript && pdflatex -interaction=nonstopmode ETM_DVPD_JOURNAL_MANUSCRIPT.tex > /dev/null \
  && bibtex ETM_DVPD_JOURNAL_MANUSCRIPT > /dev/null \
  && pdflatex -interaction=nonstopmode ETM_DVPD_JOURNAL_MANUSCRIPT.tex > /dev/null \
  && pdflatex -interaction=nonstopmode ETM_DVPD_JOURNAL_MANUSCRIPT.tex > /dev/null ) \
  || { echo "MANUSCRIPT BUILD FAILED"; grep -n "^!" manuscript/ETM_DVPD_JOURNAL_MANUSCRIPT.log | head; exit 1; }
python scripts/final_closure_evidence.py
python scripts/prelim_make_figs.py > /dev/null
python scripts/prelim_make_figs_final.py
python scripts/prelim_build_deck.py
python scripts/prelim_qa_slides.py
echo "REBUILD COMPLETE"
