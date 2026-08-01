"""Produce and machine-check a DRAT refutation certificate for an upper bound.

`PAPER.md` records the one honest gap in this project: the *lower* bounds each
carry a colouring that anyone can check in milliseconds, while the *upper* bounds
rest on a SAT solver answering UNSAT, with five guards around the **encoding**
and nothing at all around the **solver**. "No colouring exists" is an absence,
and an absence is exactly what a buggy solver reports.

This closes that half. It builds the CNF, has a standalone solver emit an ASCII
DRAT proof of unsatisfiability, and has `drat-trim` replay that proof against the
formula. What is then trusted is `drat-trim` plus the claim that the CNF says
what the definition says -- and that second half is already audited exhaustively
and in both directions by `encoding_audit.py`.

**Symmetry breaking is OFF here on purpose.** The certificate then covers the raw
encoding, so the reversal-symmetry lex-leader argument -- the one piece of new
mathematics in `vdw4` -- stays outside the trusted base rather than being assumed
by the thing meant to check it. The cost is a slower solve; the point is that a
proof of a symmetry-broken formula would not prove the original statement.

Neither binary lives in this repository. Build them with the recipe in
`vdw/DRAT.md`, then put them on PATH or point at them:

    python vdw/drat_certify.py --rung 7
    python vdw/drat_certify.py --ladder 0-6 --json
    KISSAT=... DRAT_TRIM=... python vdw/drat_certify.py --n 42 --j 7 --targets 3 4

Exit codes are the interface `verify_all.py` relies on:

    0   every requested rung verified
    1   a proof did NOT verify -- a real problem, not a missing tool
    3   the tools are not installed; nothing was checked, so callers should
        SKIP rather than fail (a clean clone and a CI runner both land here)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vdw4 import build  # noqa: E402  (after the path insert, by necessity)

TOOLS_MISSING = 3

# Published terms, used only by --rung/--ladder for convenience at the command
# line. verify_all.py does NOT read this: it passes n, j and targets explicitly
# from its own CLAIMS, so there is one source of truth. The gate additionally
# checks this table against CLAIMS, so the two cannot drift apart in silence.
FAMILIES = {
    'A217058': {'targets': [3, 4],
                'published': [18, 21, 25, 29, 33, 36, 40, 42, 45, 48, 52, 55]},
    'A217005': {'targets': [3, 3],
                'published': [9, 14, 17, 20, 21, 24, 25, 28, 31, 33, 35, 37, 39,
                              42, 44, 46, 48, 50, 51]},
    'A217007': {'targets': [4, 4],
                'published': [35, 40, 53, 54, 56, 66, 67]},
    'A217236': {'targets': [4, 5],
                'published': [55, 71, 75, 79]},
}


def find_tools(kissat=None, drat_trim=None):
    """Locate the two binaries, or return what is missing.

    Explicit argument, then environment, then PATH. No absolute path from any
    one machine is baked in: this repository is public, and a hardcoded build
    directory is both useless to a reader and a detail about someone's disk.
    """
    found = {}
    missing = []
    for key, explicit, env, exe in (
            ('kissat', kissat, 'KISSAT', 'kissat'),
            ('drat_trim', drat_trim, 'DRAT_TRIM', 'drat-trim')):
        path = explicit or os.environ.get(env) or shutil.which(exe)
        if path and os.path.exists(path):
            found[key] = path
        elif path and shutil.which(path):
            found[key] = shutil.which(path)
        else:
            missing.append(exe)
    return found, missing


def write_dimacs(cnf, nvars, path):
    """DIMACS for the solver. Written in one join rather than per-clause writes:
    these formulas run to millions of clauses and the loop is the slow part."""
    body = '\n'.join(' '.join(map(str, c)) + ' 0' for c in cnf)
    with open(path, 'w', encoding='ascii', newline='\n') as fh:
        fh.write(f'p cnf {nvars} {len(cnf)}\n')
        fh.write(body)
        fh.write('\n')


def certify(n, j, targets, tools, workdir, timeout=None):
    """Refute [1,n] with j wildcards and check the refutation.

    Returns a dict whose 'verdict' is one of VERIFIED, NOT_VERIFIED, SAT,
    SOLVER_ERROR or TIMEOUT. SAT is not a failure of this script -- it means the
    upper bound being certified is false, which is the single most important
    thing this could ever discover, so it is reported distinctly and never
    folded into a generic error.
    """
    cnf, pool, _v = build(n, j, targets, symbreak=False, revsym=False)
    formula = os.path.join(workdir, f'f_n{n}_j{j}.cnf')
    proof = os.path.join(workdir, f'p_n{n}_j{j}.drat')

    t0 = time.time()
    write_dimacs(cnf, pool.top, formula)
    t_build = time.time() - t0

    rec = {'n': n, 'j': j, 'targets': list(targets), 'symbreak': False,
           'revsym': False, 'clauses': len(cnf), 'vars': pool.top,
           'build_s': round(t_build, 1)}

    # --no-binary is mandatory: kissat's binary proof does not check under
    # drat-trim (it fails RAT on all pivots, at a different line for every
    # inprocessing setting -- a format mismatch, not a technique to disable).
    t0 = time.time()
    try:
        solve = subprocess.run([tools['kissat'], '-q', '--no-binary', formula, proof],
                               capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        rec.update(verdict='TIMEOUT', solve_s=round(time.time() - t0, 1))
        return rec
    rec['solve_s'] = round(time.time() - t0, 1)

    if solve.returncode == 10:
        rec['verdict'] = 'SAT'
        return rec
    if solve.returncode != 20:
        rec['verdict'] = 'SOLVER_ERROR'
        rec['detail'] = (solve.stderr or solve.stdout or '').strip()[-400:]
        return rec

    rec['proof_mb'] = round(os.path.getsize(proof) / 1e6, 1)

    t0 = time.time()
    try:
        chk = subprocess.run([tools['drat_trim'], formula, proof],
                             capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        rec.update(verdict='TIMEOUT', check_s=round(time.time() - t0, 1))
        return rec
    rec['check_s'] = round(time.time() - t0, 1)

    out = chk.stdout or ''
    # Match the checker's own verdict line, not its exit code: drat-trim reports
    # 's VERIFIED' on stdout and its exit status has meant different things
    # across builds.
    if 's VERIFIED' in out:
        rec['verdict'] = 'VERIFIED'
    elif 's NOT VERIFIED' in out:
        rec['verdict'] = 'NOT_VERIFIED'
        rec['detail'] = out.strip()[-400:]
    else:
        rec['verdict'] = 'SOLVER_ERROR'
        rec['detail'] = (out + (chk.stderr or '')).strip()[-400:]
    return rec


def rungs_for(seq, spec):
    """'0-6' or '7' or '0,3,7' -> [(n, j)] using the published terms."""
    fam = FAMILIES[seq]
    want = []
    for part in str(spec).split(','):
        if '-' in part:
            lo, hi = part.split('-')
            want.extend(range(int(lo), int(hi) + 1))
        else:
            want.append(int(part))
    out = []
    for j in want:
        if not 0 <= j < len(fam['published']):
            raise SystemExit(f'{seq} has no published a({j}) to certify')
        out.append((fam['published'][j], j))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--seq', default='A217058', choices=sorted(FAMILIES))
    ap.add_argument('--rung', help='wildcard count j, e.g. 7')
    ap.add_argument('--ladder', help='range of j, e.g. 0-6')
    ap.add_argument('--n', type=int, help='certify this n directly')
    ap.add_argument('--j', type=int, help='with this wildcard budget')
    ap.add_argument('--targets', type=int, nargs='+', help='and these AP targets')
    ap.add_argument('--timeout', type=float, help='seconds per solve and per check')
    ap.add_argument('--keep', metavar='DIR', help='keep the CNF and proof here')
    ap.add_argument('--json', action='store_true', help='machine-readable output')
    ap.add_argument('--kissat')
    ap.add_argument('--drat-trim', dest='drat_trim')
    args = ap.parse_args()

    tools, missing = find_tools(args.kissat, args.drat_trim)
    if missing:
        print(f'DRAT tools not installed: {", ".join(missing)} not found on PATH '
              f'or in KISSAT / DRAT_TRIM. Nothing was checked. See vdw/DRAT.md.',
              file=sys.stderr)
        return TOOLS_MISSING

    if args.n is not None:
        if args.j is None or not args.targets:
            raise SystemExit('--n needs --j and --targets')
        jobs, targets = [(args.n, args.j)], args.targets
    else:
        spec = args.ladder or args.rung
        if spec is None:
            raise SystemExit('give --rung, --ladder, or --n/--j/--targets')
        jobs, targets = rungs_for(args.seq, spec), FAMILIES[args.seq]['targets']

    workdir = args.keep or tempfile.mkdtemp(prefix='drat_')
    os.makedirs(workdir, exist_ok=True)
    results, bad = [], False
    try:
        for n, j in jobs:
            rec = certify(n, j, targets, tools, workdir, args.timeout)
            results.append(rec)
            if rec['verdict'] != 'VERIFIED':
                bad = True
            if not args.json:
                print(f"a({j}) <= {n}, targets {targets}: {rec['verdict']:<13}"
                      f" solve {rec.get('solve_s', '-')}s"
                      f" proof {rec.get('proof_mb', '-')}MB"
                      f" check {rec.get('check_s', '-')}s")
                if rec.get('detail'):
                    print(f"    {rec['detail']}")
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    if args.json:
        print(json.dumps(results, indent=1))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
