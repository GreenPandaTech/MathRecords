"""Certify an upper bound by cubes: one DRAT proof per cube, machine-checked.

`drat_certify.py` certifies an instance with a single monolithic proof; for the
headline `a(12) = 57` of A217058 that proof is order 6-17 h and 30-150 GB, which
is why it was never produced. This module splits the same instance along the
cube set `make_cubes(n, j, targets, k)`: for every cube C it proves
`F + units(C)` UNSAT with kissat and replays the proof with drat-trim. Each
verified cube establishes, by propositional logic, that F entails neg(C).

A pile of per-cube proofs is not yet a proof of F's unsatisfiability -- that
needs the machine-checked exhaustiveness argument in `cube_exhaustive.py`,
which shows every branch of the full assignment tree is killed by a cube clause
or by a clause already in F. Run this first, then that.

**Symmetry breaking is OFF, always** (`symbreak=False, revsym=False`), for the
same reason as in `drat_certify.py`: a proof of a symmetry-broken formula does
not prove the original statement, and the reversal lex-leader constraint is the
one piece of new mathematics in `vdw4` -- it must stay outside the trusted base.

Designed to run unattended for hours and survive a restart:

  * every finished cube is appended as one JSON line to `results.jsonl`;
  * on restart, cubes already recorded as VERIFIED are skipped;
  * `status.json` is rewritten as cubes finish (counts, ETA, state);
  * each cube's proof is deleted once drat-trim accepts it -- 4487 proofs at
    ~34 MB mean would be ~150 GB -- but its size and SHA256 stay in the record.

Cubes are scheduled fewest-wildcards-first: measured cost anti-correlates with
the wildcard count of the prefix (spent wildcards make the totalizer propagate
hard), so this keeps the heavy tail from straggling at the end of the run.

    python vdw/cube_certify.py --n 45 --j 8 --targets 3 4 --k 6
    python vdw/cube_certify.py --n 57 --j 12 --targets 3 4 --k 8 --dry-run
    KISSAT=... DRAT_TRIM=... python vdw/cube_certify.py --n 57 --j 12 --targets 3 4 --k 8

Exit codes follow `drat_certify.py`, with one addition:

    0   every cube VERIFIED
    1   some cube did NOT verify (or errored / timed out)
    2   a cube is SAT -- the upper bound being certified is FALSE. This is the
        single most important thing this script could ever discover; it aborts
        the whole run and is never folded into a generic error.
    3   the tools are not installed; nothing was checked (callers SKIP)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vdw4 import build, make_cubes          # noqa: E402
from drat_certify import find_tools, TOOLS_MISSING  # noqa: E402

SAT_FOUND = 2


def dimacs_body(cnf):
    """The clause lines of F, exactly as `drat_certify.write_dimacs` writes
    them. `cube_exhaustive.py` builds F' by prepending these SAME bytes, so the
    per-cube proofs and the composition proof provably talk about one formula;
    both record sha256 of this string."""
    return '\n'.join(' '.join(map(str, c)) + ' 0' for c in cnf)


def base_formula(n, j, targets):
    """(body, nvars, nclauses, v, sha256) for the raw formula, symbreak OFF."""
    cnf, pool, v = build(n, j, targets, symbreak=False, revsym=False)
    body = dimacs_body(cnf)
    sha = hashlib.sha256(body.encode('ascii')).hexdigest()
    return body, pool.top, len(cnf), v, sha


def order_cubes(cubes):
    """Fewest wildcards first (the wildcard-free cubes are the hard ones)."""
    return sorted(cubes, key=lambda c: (c.count(0), c))


# ----------------------------------------------------------------- worker ----

_CACHE = {}


def _cached_base(n, j, targets):
    key = (n, j, tuple(targets))
    if key not in _CACHE:
        _CACHE[key] = base_formula(n, j, targets)
    return _CACHE[key]


def certify_cube(task):
    """Solve and check one cube. Returns a record dict; never raises for a
    verdict-shaped outcome -- an exception here means the run itself is broken
    and must abort (crash-honest: a dead worker is never read as UNSAT)."""
    (n, j, targets, cube, workdir, kissat, drat_trim, timeout, truncate) = task
    body, nvars, nclauses, v, sha = _cached_base(n, j, targets)
    units = [v(i + 1, c) for i, c in enumerate(cube)]
    tag = ''.join(map(str, cube))
    formula = os.path.join(workdir, f'c{tag}.cnf')
    proof = os.path.join(workdir, f'c{tag}.drat')

    with open(formula, 'w', encoding='ascii', newline='\n') as fh:
        fh.write(f'p cnf {nvars} {nclauses + len(units)}\n')
        fh.write(body)
        fh.write('\n')
        fh.write('\n'.join(f'{u} 0' for u in units))
        fh.write('\n')

    rec = {'cube': list(cube), 'wilds': cube.count(0), 'formula_sha256': sha}
    keep = False
    try:
        t0 = time.time()
        try:
            solve = subprocess.run([kissat, '-q', '--no-binary', formula, proof],
                                   capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            rec.update(verdict='TIMEOUT', solve_s=round(time.time() - t0, 1))
            return rec
        rec['solve_s'] = round(time.time() - t0, 1)

        if solve.returncode == 10:
            # The cube is SATISFIABLE: a legal colouring of [1,n] exists, so the
            # upper bound is FALSE. Keep the formula for reproduction.
            rec['verdict'] = 'SAT'
            rec['detail'] = (solve.stdout or '').strip()[:400]
            keep = True
            return rec
        if solve.returncode != 20:
            rec['verdict'] = 'SOLVER_ERROR'
            rec['detail'] = (solve.stderr or solve.stdout or '').strip()[-400:]
            keep = True
            return rec

        rec['proof_bytes'] = os.path.getsize(proof)
        if truncate:
            # Negative-control hook: hand drat-trim only half the proof. This
            # MUST come back NOT_VERIFIED; a pass here would mean the checker
            # checks nothing.
            half = rec['proof_bytes'] // 2
            with open(proof, 'r+b') as fh:
                fh.truncate(half)
            rec['negctl'] = f'proof truncated to {half} of {rec["proof_bytes"]} bytes'
        h = hashlib.sha256()
        with open(proof, 'rb') as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b''):
                h.update(chunk)
        rec['proof_sha256'] = h.hexdigest()

        t0 = time.time()
        try:
            chk = subprocess.run([drat_trim, formula, proof],
                                 capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            rec.update(verdict='TIMEOUT', check_s=round(time.time() - t0, 1))
            return rec
        rec['check_s'] = round(time.time() - t0, 1)

        out = chk.stdout or ''
        # The checker's own verdict line, never its exit code (drat_certify.py
        # explains: the exit status has meant different things across builds).
        if 's VERIFIED' in out:
            rec['verdict'] = 'VERIFIED'
        elif 's NOT VERIFIED' in out:
            rec['verdict'] = 'NOT_VERIFIED'
            rec['detail'] = out.strip()[-400:]
            keep = True
        else:
            rec['verdict'] = 'SOLVER_ERROR'
            rec['detail'] = (out + (chk.stderr or '')).strip()[-400:]
            keep = True
        return rec
    finally:
        if not keep:
            for p in (formula, proof):
                try:
                    os.remove(p)
                except OSError:
                    pass
        else:
            rec['kept_files'] = [formula, proof if os.path.exists(proof) else None]


# ----------------------------------------------------------------- driver ----

def parse_cube(text, k):
    parts = [int(x) for x in text.replace(',', ' ').split()]
    if len(parts) != k:
        raise SystemExit(f'--only cube has {len(parts)} entries, expected k={k}')
    return tuple(parts)


def load_results(path):
    """cube-tuple -> last recorded dict. Tolerates a torn final line, which is
    exactly what a killed run leaves behind."""
    done = {}
    if not os.path.exists(path):
        return done
    with open(path, encoding='ascii') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if 'cube' in rec:
                done[tuple(rec['cube'])] = rec
    return done


def write_status(path, payload):
    tmp = path + '.tmp'
    payload['updated_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
    with open(tmp, 'w', encoding='ascii', newline='\n') as fh:
        json.dump(payload, fh, indent=1)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--n', type=int, required=True)
    ap.add_argument('--j', type=int, required=True)
    ap.add_argument('--targets', type=int, nargs='+', required=True)
    ap.add_argument('--k', type=int, required=True, help='cube depth (prefix length)')
    ap.add_argument('--workers', type=int,
                    default=max(1, min(14, (os.cpu_count() or 4) - 2)))
    ap.add_argument('--timeout', type=float,
                    help='seconds per solve and per check, each')
    ap.add_argument('--limit', type=int, metavar='N',
                    help='smoke test: only the first N scheduled cubes')
    ap.add_argument('--only', metavar='CUBE',
                    help='run a single cube, e.g. "0,1,2,0,1,2,0,1" (must be in the cube set)')
    ap.add_argument('--dry-run', action='store_true',
                    help='count the cubes and exit')
    ap.add_argument('--run-dir', help='where results.jsonl / status.json / work live '
                                      '(default vdw/cube_run_n{n}_j{j}_k{k})')
    ap.add_argument('--negctl-truncate', type=int, metavar='IDX',
                    help='NEGATIVE CONTROL: truncate the proof of the IDX-th '
                         'scheduled cube to half before checking; must FAIL')
    ap.add_argument('--kissat')
    ap.add_argument('--drat-trim', dest='drat_trim')
    args = ap.parse_args()

    cubes = order_cubes(make_cubes(args.n, args.j, args.targets, args.k))
    if args.only:
        want = parse_cube(args.only, args.k)
        if want not in set(cubes):
            raise SystemExit(f'--only {want}: not in the cube set for '
                             f'n={args.n} j={args.j} k={args.k}')
        cubes = [want]
    if args.limit:
        cubes = cubes[:args.limit]

    if args.dry_run:
        hist = {}
        for c in cubes:
            hist[c.count(0)] = hist.get(c.count(0), 0) + 1
        print(f'n={args.n} j={args.j} targets={args.targets} k={args.k}: '
              f'{len(cubes)} cubes; wildcard histogram {dict(sorted(hist.items()))}')
        return 0

    tools, missing = find_tools(args.kissat, args.drat_trim)
    if missing:
        print(f'DRAT tools not installed: {", ".join(missing)} not found on PATH '
              f'or in KISSAT / DRAT_TRIM. Nothing was checked. See vdw/DRAT.md.',
              file=sys.stderr)
        return TOOLS_MISSING

    here = os.path.dirname(os.path.abspath(__file__))
    run_dir = args.run_dir or os.path.join(
        here, f'cube_run_n{args.n}_j{args.j}_k{args.k}')
    workdir = os.path.join(run_dir, 'work')
    os.makedirs(workdir, exist_ok=True)
    results_path = os.path.join(run_dir, 'results.jsonl')
    status_path = os.path.join(run_dir, 'status.json')

    _, nvars, nclauses, _, sha = base_formula(args.n, args.j, args.targets)

    done = load_results(results_path)
    todo = [c for c in cubes if done.get(c, {}).get('verdict') != 'VERIFIED']
    prev_ok = len(cubes) - len(todo)
    print(f'{len(cubes)} cubes ({prev_ok} already VERIFIED in {results_path}); '
          f'{len(todo)} to run on {args.workers} workers')

    status = {'n': args.n, 'j': args.j, 'targets': args.targets, 'k': args.k,
              'symbreak': False, 'revsym': False,
              'formula_sha256': sha, 'vars': nvars, 'clauses': nclauses,
              'total_cubes': len(cubes), 'verified': prev_ok,
              'state': 'running', 'counts': {}, 'eta_s': None}
    write_status(status_path, status)

    tasks = [(args.n, args.j, args.targets, c, workdir,
              tools['kissat'], tools['drat_trim'], args.timeout,
              args.negctl_truncate is not None and i == args.negctl_truncate)
             for i, c in enumerate(todo)]

    t_start = time.time()
    finished = 0
    bad = sat = False
    try:
        with open(results_path, 'a', encoding='ascii', newline='\n') as out, \
                ProcessPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(certify_cube, t): t[3] for t in tasks}
            for f in as_completed(futs):
                rec = f.result()   # a dead worker raises here, never reads as UNSAT
                out.write(json.dumps(rec) + '\n')
                out.flush()
                finished += 1
                v = rec['verdict']
                status['counts'][v] = status['counts'].get(v, 0) + 1
                if v == 'VERIFIED':
                    status['verified'] += 1
                else:
                    bad = True
                elapsed = time.time() - t_start
                remaining = len(tasks) - finished
                status['eta_s'] = round(elapsed / finished * remaining)
                status['elapsed_s'] = round(elapsed)
                write_status(status_path, status)
                if v == 'SAT':
                    sat = True
                    print('!' * 74)
                    print(f'!! SAT CUBE {rec["cube"]} at n={args.n} j={args.j} '
                          f'targets={args.targets}')
                    print('!! A legal colouring exists inside this cube: the upper '
                          f'bound n={args.n} is FALSE.')
                    print('!! If this is a published term, IT IS WRONG. Formula kept '
                          f'at {rec.get("kept_files")}')
                    print('!' * 74)
                    for g in futs:
                        g.cancel()
                    ex.shutdown(cancel_futures=True)
                    break
                if finished % 25 == 0 or remaining == 0:
                    print(f'  {finished}/{len(tasks)} this session '
                          f'({status["verified"]}/{len(cubes)} verified total), '
                          f'ETA {status["eta_s"]}s')
    except KeyboardInterrupt:
        status['state'] = 'interrupted'
        write_status(status_path, status)
        print('interrupted; finished cubes are recorded, rerun to resume')
        return 1

    if sat:
        status['state'] = 'SAT_ABORT'
        write_status(status_path, status)
        return SAT_FOUND

    all_ok = status['verified'] == len(cubes) and not bad
    status['state'] = 'done' if all_ok else 'failed'
    write_status(status_path, status)
    print(f'{status["verified"]}/{len(cubes)} cubes VERIFIED '
          f'({time.time() - t_start:.0f}s this session); counts {status["counts"]}')
    if all_ok:
        print(f'every cube verified -- now run cube_exhaustive.py with the same '
              f'n/j/targets/k against {results_path}')
    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
