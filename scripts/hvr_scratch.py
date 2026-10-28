"""Scratch root for solver work directories -- never inside the repository and never
/tmp, which is a small shared volume on this host (it filled once at 50 GB).

Override with the HVR_SCRATCH environment variable; the default is
~/claude_scratch/hvr_work. Reference-tool scripts import this file by path.
"""
import os
from pathlib import Path

ROOT = Path(os.environ.get("HVR_SCRATCH", Path.home() / "claude_scratch" / "hvr_work"))


def path(*parts: str) -> Path:
    p = ROOT.joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p
