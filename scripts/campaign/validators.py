"""Output validators of the campaign manifest (scripts/campaign/manifest.yaml `validate:`).

Each check returns (ok, reason). A job counts as done only when its process exited 0 AND
every declared output validates, and an output that validates is never recomputed unless
--force: that is what makes the runner idempotent and resumable.

kinds
  exists     the file (or a non-empty directory) is present and non-empty
  json       parses; optional `keys: [...]` must all be top-level keys; optional
             `nonempty: [...]` keys must hold a non-empty value; with `fresh: true` every
             file the record names in its top-level `inputs_sha1` ({absolute path: sha1})
             must still hash the same (a record built on an input that has since been
             re-run is stale, not valid)
  csv        parses with at least `min_rows` (default 1) data rows
  etm        an ETM case file: et_converged is True, |thermal.energy_residual_rel| <=
             `tol_energy` (1e-4), |thermal.deposit_residual_rel| <= `tol_deposit` (1e-6) when
             present, mechanics present without mechanics_error (unless `mechanics: false`),
             and with `local: true` a local solder response without error; `fresh: true` as
             for json (a mechanics-only run's base case and converged field unchanged)
  feedback   an interface-feedback case (tcpmt_review_variants feedback): converged is True,
             or a recorded, explained runaway (non_convergence.kind 'runaway' with its reason
             and last iterates; a pass-limit stop is not accepted), the energy residual as
             above, mechanics present
  frd        a CalculiX result file at least `min_kb` (default 4) kB long that ends with the
             9999 end record
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _load(f):
    try:
        return json.loads(Path(f).read_text()), None
    except FileNotFoundError:
        return None, "missing"
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return None, f"not JSON ({e})"


def check_exists(f, spec):
    f = Path(f)
    if f.is_dir():
        return (any(f.iterdir()), "directory" if any(f.iterdir()) else "empty directory")
    if not f.exists():
        return False, "missing"
    return (f.stat().st_size > 0, f"{f.stat().st_size} bytes")


def check_json(f, spec):
    c, err = _load(f)
    if err:
        return False, err
    miss = [k for k in spec.get("keys", []) if not (isinstance(c, dict) and k in c)]
    if miss:
        return False, f"missing keys {miss}"
    empty = [k for k in spec.get("nonempty", []) if not (isinstance(c, dict) and c.get(k))]
    if empty:
        return False, f"empty {empty}"
    if spec.get("fresh"):
        ok, why = _fresh(c)
        return (ok, f"json ok, {why}" if ok else why)
    return True, "json ok"


def _fresh(c):
    """Every file the record names in `inputs_sha1` still hashes the same."""
    ins = (c.get("inputs_sha1") if isinstance(c, dict) else None) or {}
    if not ins:
        return False, "no inputs_sha1 to check freshness against"
    for p, h in ins.items():
        if not Path(p).is_file():
            return False, f"input gone: {p}"
        if _sha1(p) != h:
            return False, f"stale: input re-written since ({Path(p).name})"
    return True, f"{len(ins)} input(s) unchanged"


def _sha1(p):
    import hashlib
    h = hashlib.sha1()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def check_csv(f, spec):
    try:
        with open(f, newline="") as fh:
            rows = list(csv.DictReader(fh))
    except FileNotFoundError:
        return False, "missing"
    except (csv.Error, UnicodeDecodeError) as e:
        return False, f"bad csv ({e})"
    n = int(spec.get("min_rows", 1))
    return (len(rows) >= n, f"{len(rows)} rows")


def _residuals(c, spec):
    th = c.get("thermal") or {}
    er = th.get("energy_residual_rel")
    if not _num(er):
        return False, "no thermal.energy_residual_rel"
    if abs(er) > float(spec.get("tol_energy", 1e-4)):
        return False, f"energy residual {er:.2e} > {spec.get('tol_energy', 1e-4)}"
    dr = th.get("deposit_residual_rel")
    if dr is not None and _num(dr) and abs(dr) > float(spec.get("tol_deposit", 1e-6)):
        return False, f"deposit residual {dr:.2e}"
    return True, f"energy residual {er:.1e}"


def _mech(c, spec):
    if spec.get("mechanics", True) is False:
        return True, "thermal only"
    if c.get("mechanics_error"):
        return False, f"mechanics_error: {str(c['mechanics_error'])[-120:]}"
    mm = c.get("mechanics") or {}
    crit = (mm.get("joint_search") or {}).get("critical")
    if not mm or not crit:
        return False, "no mechanics / critical joint"
    return True, f"du_c {crit.get('du_um', float('nan')):.4f} um"


def check_etm(f, spec):
    c, err = _load(f)
    if err:
        return False, err
    if c.get("et_converged") is not True:
        return False, f"et_converged={c.get('et_converged')}"
    ok, why = _residuals(c, spec)
    if not ok:
        return False, why
    ok2, why2 = _mech(c, spec)
    if not ok2:
        return False, why2
    if spec.get("local"):
        loc = c.get("local") or {}
        if loc.get("error") or loc.get("d_peeq_per_cycle") is None:
            return False, f"local response missing/failed ({loc.get('error')})"
    if spec.get("design_tag") is not None:
        tag = (c.get("design") or {}).get("tag", "")
        if tag != spec["design_tag"]:
            return False, f"design tag {tag!r} != {spec['design_tag']!r}"
    if spec.get("fresh"):                       # a mechanics-only run on a converged field
        ok3, why3 = _fresh(c)
        if not ok3:
            return False, why3
    return True, f"converged, {why}, {why2}"


def recorded_runaway(c):
    """The case records an explained runaway (tcpmt_review_variants feedback: the changes grew
    over two consecutive passes): non_convergence.kind == 'runaway' with its reason and at
    least three last iterates. A loop stopped by the pass limit is NOT accepted (it needs more
    passes, not a record)."""
    nc = c.get("non_convergence") or {}
    return (nc.get("kind") == "runaway" and bool(nc.get("reason"))
            and len(nc.get("last_iterates") or []) >= 3)


def check_feedback(f, spec):
    c, err = _load(f)
    if err:
        return False, err
    runaway = c.get("converged") is not True and recorded_runaway(c)
    if c.get("converged") is not True and not runaway:
        return False, (f"feedback converged={c.get('converged')}"
                       + (f" ({c['stop_reason']})" if c.get("stop_reason") else ""))
    ok, why = _residuals(c, spec)
    if not ok:
        return False, why
    ok2, why2 = _mech(c, spec)
    state = (f"recorded runaway after {len(c.get('iterations', []))} pass(es)" if runaway else
             f"feedback converged in {len(c.get('iterations', []))} pass(es)")
    return (ok2, f"{state}, {why}, {why2}" if ok2 else why2)


def check_frd(f, spec):
    f = Path(f)
    if not f.exists():
        return False, "missing"
    kb = f.stat().st_size / 1024
    if kb < float(spec.get("min_kb", 4)):
        return False, f"{kb:.1f} kB"
    with open(f, "rb") as fh:
        fh.seek(max(0, f.stat().st_size - 200))
        tail = fh.read()
    return (b"9999" in tail, f"{kb / 1024:.1f} MB" + ("" if b"9999" in tail else ", no end record"))


KINDS = {"exists": check_exists, "json": check_json, "csv": check_csv, "etm": check_etm,
         "feedback": check_feedback, "frd": check_frd}


def check(f, spec):
    fn = KINDS.get(spec.get("kind", "exists"))
    if fn is None:
        return False, f"unknown validator {spec.get('kind')}"
    try:
        return fn(f, spec)
    except Exception as e:                        # noqa: BLE001 - a broken file is invalid
        return False, f"{type(e).__name__}: {e}"
