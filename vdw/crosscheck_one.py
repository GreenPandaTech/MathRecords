"""Re-decide one instance through the older, structurally different engine.

vdw2 is the previous implementation.  It has **no reversal-symmetry constraint
at all** -- on targets [3,4] its only symmetry rule is vacuous -- so it explores
the full, unreduced search space.  That makes it the right second opinion
precisely for the claim most at risk: if the lex-leader constraint added in
vdw4 were unsound, it could delete the only orbit containing a solution and
turn a satisfiable instance into a false UNSAT.  vdw2 cannot make that mistake,
because it does not do the reduction.

Different code, different search space, optionally a different CDCL solver.
Agreement is corroboration; disagreement means stop.

Usage:  python crosscheck_one.py <n> <j> <t1> <t2> [--workers 4] [--k 4]
"""
import argparse
import json
import os
import threading
import time
import traceback

import vdw2

HERE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(os.path.dirname(HERE), 'logs')
_LOGF = None


def log(m):
    line = f'[{time.strftime("%H:%M:%S")}] {m}'
    print(line, flush=True)
    if _LOGF:
        _LOGF.write(line + '\n')
        _LOGF.flush()
        os.fsync(_LOGF.fileno())


def main():
    global _LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int)
    ap.add_argument('j', type=int)
    ap.add_argument('targets', type=int, nargs='+')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--k', type=int, default=4)
    ap.add_argument('--tag', default=None)
    a = ap.parse_args()

    tag = a.tag or f'xcheck_n{a.n}_j{a.j}'
    os.makedirs(LOGDIR, exist_ok=True)
    _LOGF = open(os.path.join(LOGDIR, f'{tag}.log'), 'a', encoding='utf-8')
    log(f'cross-check via vdw2 (NO reversal symmetry): n={a.n} j={a.j} '
        f'targets={a.targets} workers={a.workers} k={a.k} pid={os.getpid()}')

    t0 = time.time()
    stop = threading.Event()

    def beat():
        while not stop.wait(300):
            log(f'  ... still running, {(time.time()-t0)/60:.0f} min elapsed')

    threading.Thread(target=beat, daemon=True).start()
    try:
        sat, col = vdw2.solve_par(a.n, a.j, a.targets, k=a.k, workers=a.workers)
    finally:
        stop.set()
    dt = time.time() - t0

    rec = {'engine': 'vdw2 (no reversal symmetry)', 'n': a.n, 'j': a.j,
           'targets': a.targets, 'sat': bool(sat), 'sec': dt,
           'workers': a.workers, 'k': a.k,
           'finished': time.strftime('%Y-%m-%d %H:%M:%S')}
    if sat:
        good, wild, bad = vdw2.check(col, a.targets, a.j)
        cert = ''.join('.' if c == 0 else str(c) for c in col)
        rec.update({'witness_verified': bool(good), 'wildcards': wild,
                    'certificate': cert, 'colouring': col})
        open(os.path.join(HERE, f'cert_{tag}.txt'), 'w').write(cert)
        log(f'SAT   {dt:.1f}s  ({wild}/{a.j} wildcards, verified={good})')
        log(f'  {cert}')
    else:
        log(f'UNSAT {dt:.1f}s')

    json.dump(rec, open(os.path.join(HERE, f'{tag}.json'), 'w'), indent=1)
    log(f'wrote {tag}.json')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
