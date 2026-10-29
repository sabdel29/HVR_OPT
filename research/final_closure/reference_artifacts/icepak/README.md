# Icepak cooling benchmark: preserved project files

These are the AEDT 2026 R1 Icepak projects behind `research/final_closure/reference_cooling_icepak.json`: one microchannel half-pitch, steady laminar conjugate CFD, four mesh levels. Each project's SHA256 and original path are in `MANIFEST.json`, together with the boundary conditions and the reproduction command.

Kept here:
- the `.aedt` project file of every level;
- Icepak's own inlet/outlet flow reports (`fs_*.csv`);
- the round-1 convergence-criteria record.

Not kept:
- the solved `.aedtresults` folders, which are solver scratch. Re-solving a project regenerates them.
- the AEDT/PyAEDT logs, which carry licence-server details.

Reproduce:

    export PATH=/home/beams0/MGHARIB/envs/etm/bin:$PATH; python scripts/reference_tools/icepak_cooling_benchmark.py driver baseline fine baseline_x fine_x   (AEDT 2026 R1 with an Icepak licence; writes under $AEDT_WORK, default ~/claude_scratch/aedt_work)
