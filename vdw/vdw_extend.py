"""Extend one family of mixed van der Waerden numbers by one term.

Procedure, in order:
  1. GATE - reproduce the last published term (SAT at w-1, UNSAT at w).  If this
     fails, nothing downstream is trustworthy and the run aborts.
  2. LOWER BOUND - climb n while satisfiable.  Every witness is re-verified by
     `check`, which reads only the colouring.
  3. UPPER BOUND - prove UNSAT at the first failing n.
  4. Emit the certificate and the claim.

Usage:  python vdw_extend.py A217058
"""
import json
import os
import sys
import time

from vdw2 import check, solve_par

HERE = os.path.dirname(os.path.abspath(__file__))

FAM = {
    'A217005': ([3, 3],    [9, 14, 17, 20, 21, 24, 25, 28, 31, 33, 35, 37, 39, 42, 44, 46, 48, 50, 51]),
    'A217007': ([4, 4],    [35, 40, 53, 54, 56, 66, 67]),
    'A217008': ([3, 3, 3], [27, 40, 41, 42, 45, 49, 52]),
    'A217058': ([3, 4],    [18, 21, 25, 29, 33, 36, 40, 42, 45, 48, 52, 55]),
    'A217059': ([3, 5],    [22, 32, 43, 44, 50, 55, 61, 65, 70]),
    'A217060': ([3, 6],    [32, 40, 48, 56, 60, 65, 71]),
    'A217236': ([4, 5],    [55, 71, 75, 79]),
    'A217237': ([4, 6],    [73, 83, 93, 101]),
}


def run(seq, k=None, skip_gate=False):
    targets, vals = FAM[seq]
    jm = len(vals) - 1
    jnew = jm + 1
    kk = k if k is not None else (5 if len(targets) == 2 else 4)
    log = {'seq': seq, 'targets': targets, 'known': vals, 'j_new': jnew}
    T0 = time.time()

    if not skip_gate:
        print(f'[gate] reproducing published a({jm}) = {vals[jm]} for {seq} ...', flush=True)
        t0 = time.time()
        ok, col = solve_par(vals[jm] - 1, jm, targets, k=kk)
        assert ok, f'GATE FAIL: expected SAT at n={vals[jm]-1}, j={jm}'
        good, wild, bad = check(col, targets, jm)
        assert good, f'GATE FAIL: witness rejected {bad}'
        t1 = time.time()
        ok2, _ = solve_par(vals[jm], jm, targets, k=kk)
        assert not ok2, f'GATE FAIL: expected UNSAT at n={vals[jm]}, j={jm}'
        print(f'[gate] PASS  SAT(n={vals[jm]-1}) {t1-t0:.1f}s   '
              f'UNSAT(n={vals[jm]}) {time.time()-t1:.1f}s', flush=True)
        log['gate_sec'] = time.time() - t0

    # Lower bound.  a(j) is non-decreasing in j -- an extra colour with target 2
    # can always be left empty -- so the search starts at the previous term.
    n = vals[jm]
    best_col = None
    while True:
        t0 = time.time()
        ok, col = solve_par(n, jnew, targets, k=kk)
        dt = time.time() - t0
        json.dump({'seq': seq, 'j_new': jnew, 'n_probed': n, 'sat': bool(ok),
                   'sec': dt, 'colouring': col},
                  open(os.path.join(HERE, f'progress_{seq}.json'), 'w'), indent=1)
        if not ok:
            print(f'[bound] n={n:4d} UNSAT  {dt:9.1f}s   -> a({jnew}) = {n}', flush=True)
            break
        good, wild, bad = check(col, targets, jnew)
        assert good, f'witness rejected at n={n}: {bad}'
        best_col = col
        print(f'[bound] n={n:4d} SAT    {dt:9.1f}s   (wildcards used {wild}/{jnew}, verified)',
              flush=True)
        n += 1

    w = n
    log.update({'value': w, 'witness_n': w - 1, 'witness': best_col,
                'total_sec': time.time() - T0})
    good, wild, bad = check(best_col, targets, jnew)
    log['witness_verified'] = good
    log['witness_wildcards'] = wild
    print(f'\n=== {seq}: a({jnew}) = w({jnew}+{len(targets)}; 2^{jnew}, '
          f'{", ".join(map(str, targets))}) = {w} ===')
    print(f'    previous last term: a({jm}) = {vals[jm]}  (Tanbir Ahmed, 2012)')
    print(f'    witness for n={w-1} independently verified: {good} '
          f'(wildcards {wild} <= {jnew})')
    print(f'    total {time.time()-T0:.0f}s')
    json.dump(log, open(os.path.join(HERE, f'result_{seq}.json'), 'w'), indent=1)
    return log


if __name__ == '__main__':
    seq = sys.argv[1]
    kk = int(sys.argv[2]) if len(sys.argv) > 2 else None
    skip = '--skip-gate' in sys.argv
    run(seq, k=kk, skip_gate=skip)
