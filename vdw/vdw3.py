"""Faster UNSAT engine for mixed van der Waerden numbers.

Two changes over vdw2:

1. BATCHED CUBES.  vdw2 rebuilt the CNF and spun up a fresh solver for every
   cube.  Here each worker builds the formula once and solves its whole share
   of cubes under assumptions on one solver instance, so clauses learned on
   cube 1 still help on cube 40.

2. REVERSAL SYMMETRY BREAKING.  i -> n+1-i maps APs to APs and preserves the
   wildcard count, so solutions come in mirror pairs.  A lex-leader constraint
   keeps only the smaller of each pair.

   Soundness note: this is applied ONLY when every target is distinct, i.e.
   when there is no colour-permutation symmetry to interact with.  Breaking two
   symmetries independently is not sound in general, so for families like
   (3,3) and (3,3,3) the colour-permutation break is used alone.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from pysat.solvers import Cadical195

from vdw2 import _has_mono_ap, aps, check, make_cubes


def build(n, j, targets, symbreak=True, reversal=None):
    r = len(targets)
    if reversal is None:
        reversal = len(set(targets)) == len(targets)   # no colour symmetry present
    pool = IDPool()
    v = lambda i, c: pool.id(('v', i, c))
    cnf = []
    for i in range(1, n + 1):
        cnf.append([v(i, c) for c in range(r + 1)])
        for c1 in range(r + 1):
            for c2 in range(c1 + 1, r + 1):
                cnf.append([-v(i, c1), -v(i, c2)])
    for c, t in enumerate(targets, start=1):
        for ap in aps(n, t):
            cnf.append([-v(i, c) for i in ap])
    cnf.extend(CardEnc.atmost(lits=[v(i, 0) for i in range(1, n + 1)], bound=j,
                              vpool=pool, encoding=EncType.totalizer).clauses)
    if symbreak:
        groups = {}
        for c, t in enumerate(targets, start=1):
            groups.setdefault(t, []).append(c)
        for t, cols in groups.items():
            for m in range(1, len(cols)):
                cp, cc = cols[m - 1], cols[m]
                p = [pool.id(('sb', t, m, i)) for i in range(1, n + 2)]
                cnf.append([p[0]])
                for i in range(1, n + 1):
                    cnf.append([-p[i], p[i - 1]])
                    cnf.append([-p[i], -v(i, cp)])
                    cnf.append([p[i], -p[i - 1], v(i, cp)])
                    cnf.append([-p[i - 1], -v(i, cc)])
    if reversal:
        cnf.extend(_reversal_lex(n, r, pool, v))
    return cnf, pool, v


def _reversal_lex(n, r, pool, v):
    """Require the colouring to be lex <= its own reversal."""
    cls = []
    e = [pool.id(('rev', i)) for i in range(1, n + 2)]      # e[i-1] = agree on 1..i-1
    cls.append([e[0]])
    for i in range(1, n + 1):
        m = n + 1 - i
        if i >= m:
            break
        # e_i AND c_i > c_m  is forbidden
        for a in range(r + 1):
            for b in range(a):
                cls.append([-e[i - 1], -v(i, a), -v(m, b)])
        # e_{i+1} <-> e_i AND (c_i == c_m)
        cls.append([-e[i], e[i - 1]])
        for a in range(r + 1):
            cls.append([-e[i], -v(i, a), v(m, a)])
        lits = [e[i], -e[i - 1]]
        for a in range(r + 1):
            d = pool.id(('reveq', i, a))
            cls.append([-d, v(i, a)])
            cls.append([-d, v(m, a)])
            cls.append([d, -v(i, a), -v(m, a)])
            lits.append(-d)
        cls.append(lits)
    return cls


def _batch(args):
    n, j, targets, cubes, symbreak, reversal = args
    cnf, pool, v = build(n, j, targets, symbreak=symbreak, reversal=reversal)
    with Cadical195(bootstrap_with=cnf) as s:
        for cube in cubes:
            assume = [v(i + 1, c) for i, c in enumerate(cube)]
            if s.solve(assumptions=assume):
                model = set(l for l in s.get_model() if l > 0)
                return [next(c for c in range(len(targets) + 1) if v(i, c) in model)
                        for i in range(1, n + 1)]
    return None


def solve(n, j, targets, k=None, workers=16, symbreak=True, reversal=None, verbose=False):
    if k is None:
        k = 6 if len(targets) == 2 else 4
    cubes = make_cubes(n, j, targets, k)
    if not cubes:
        return False, None
    W = min(workers, max(1, len(cubes)))
    batches = [cubes[i::W] for i in range(W)]
    batches = [b for b in batches if b]
    if verbose:
        print(f'    {len(cubes)} cubes over {len(batches)} workers', flush=True)
    tasks = [(n, j, targets, b, symbreak, reversal) for b in batches]
    with ProcessPoolExecutor(max_workers=W) as ex:
        futs = [ex.submit(_batch, t) for t in tasks]
        done = 0
        try:
            for f in as_completed(futs):
                res = f.result()
                done += 1
                if res is not None:
                    return True, res
        finally:
            for f in futs:
                f.cancel()
        if done != len(futs):
            raise RuntimeError(f'only {done}/{len(futs)} batches completed; UNSAT not proven')
    return False, None


if __name__ == '__main__':
    n, j = int(sys.argv[1]), int(sys.argv[2])
    targets = [int(a) for a in sys.argv[3:]]
    t0 = time.time()
    ok, col = solve(n, j, targets, verbose=True)
    print(f'n={n} j={j} {targets}: {"SAT" if ok else "UNSAT"}  {time.time()-t0:.2f}s')
    if ok:
        print('  verify:', check(col, targets, j))
