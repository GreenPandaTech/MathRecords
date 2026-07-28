"""Mixed van der Waerden numbers, parallel cube-and-conquer edition.

w(j+r; 2^j, t_1..t_r) = 1 + max{ n : some assignment of [n] to {wildcard, 1..r}
                                 uses <= j wildcards and has no t_i-term AP in colour i }

SAT (a lower bound) is cheap and yields a certificate anyone can check in
milliseconds.  UNSAT (the matching upper bound) is the whole cost, so that is
what is engineered here:

  * symmetry breaking on the colour permutation (colours with equal targets are
    interchangeable) -- the first non-wildcard position is forced to colour 1,
    the first position not in colour 1 to colour 2, and so on;
  * cube-and-conquer: branch on the classes of the first k positions, discard
    cubes that already contain a monochromatic AP, and run the residual
    formulas across all cores.

Every SAT answer is re-verified from scratch by `check`, which never looks at
the CNF.
"""
import itertools
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from pysat.solvers import Cadical195


def aps(n, t):
    out = []
    for d in range(1, (n - 1) // (t - 1) + 1):
        for a in range(1, n - (t - 1) * d + 1):
            out.append([a + k * d for k in range(t)])
    return out


def build(n, j, targets, symbreak=True):
    r = len(targets)
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
        cnf.extend(_symbreak(n, targets, pool, v))
    return cnf, pool, v


def _symbreak(n, targets, pool, v):
    """Colours sharing a target value are interchangeable; force the first
    occurrences into increasing colour order.  Sound: every solution has a
    unique image under the colour permutation group that satisfies this."""
    r = len(targets)
    cls = []
    groups = {}
    for c, t in enumerate(targets, start=1):
        groups.setdefault(t, []).append(c)
    for t, cols in groups.items():
        if len(cols) < 2:
            continue
        # within this group, colour cols[m] may not appear before cols[m-1]
        for m in range(1, len(cols)):
            c_prev, c_cur = cols[m - 1], cols[m]
            # p[i] = "no position < i carries colour c_prev"
            p = [None] * (n + 2)
            for i in range(1, n + 2):
                p[i] = pool.id(('sb', t, m, i))
            cls.append([p[1]])
            for i in range(1, n + 1):
                # p[i+1] <-> p[i] AND NOT v(i, c_prev)
                cls.append([-p[i + 1], p[i]])
                cls.append([-p[i + 1], -v(i, c_prev)])
                cls.append([p[i + 1], -p[i], v(i, c_prev)])
                # if nothing before i has colour c_prev, i cannot have c_cur
                cls.append([-p[i], -v(i, c_cur)])
    return cls


def _has_mono_ap(prefix, targets):
    """prefix[i] = class of position i+1 (0 = wildcard).  Reject a cube that is
    already dead on its own."""
    k = len(prefix)
    for c, t in enumerate(targets, start=1):
        pos = [i + 1 for i, x in enumerate(prefix) if x == c]
        ps = set(pos)
        for a in pos:
            for d in range(1, k):
                if a + (t - 1) * d <= k and all((a + m * d) in ps for m in range(t)):
                    return True
    return False


def make_cubes(n, j, targets, k):
    """All class-assignments of positions 1..k that survive the local AP test,
    the wildcard budget, and the colour-symmetry rule."""
    r = len(targets)
    groups = {}
    for c, t in enumerate(targets, start=1):
        groups.setdefault(t, []).append(c)
    cubes = []
    for pre in itertools.product(range(r + 1), repeat=k):
        if pre.count(0) > j:
            continue
        ok = True
        for t, cols in groups.items():                  # colour-symmetry filter
            seen = []
            for x in pre:
                if x in cols and x not in seen:
                    seen.append(x)
            if seen != cols[:len(seen)]:
                ok = False
                break
        if not ok or _has_mono_ap(pre, targets):
            continue
        cubes.append(pre)
    return cubes


def _cube_job(args):
    n, j, targets, cube, symbreak = args
    cnf, pool, v = build(n, j, targets, symbreak=symbreak)
    assume = [v(i + 1, c) for i, c in enumerate(cube)]
    with Cadical195(bootstrap_with=cnf) as s:
        ok = s.solve(assumptions=assume)
        if not ok:
            return None
        model = set(l for l in s.get_model() if l > 0)
        return [next(c for c in range(len(targets) + 1) if v(i, c) in model)
                for i in range(1, n + 1)]


def solve_direct(n, j, targets, conflicts=3_000_000, symbreak=True):
    """One solver on the whole formula, conflict-limited.
    Returns True / False / None(unknown), and the colouring when SAT."""
    cnf, pool, v = build(n, j, targets, symbreak=symbreak)
    with Cadical195(bootstrap_with=cnf) as s:
        s.conf_budget(conflicts)
        r = s.solve_limited()
        if r is not True:
            return r, None
        model = set(l for l in s.get_model() if l > 0)
        return True, [next(c for c in range(len(targets) + 1) if v(i, c) in model)
                      for i in range(1, n + 1)]


def solve_par(n, j, targets, k=None, workers=16, symbreak=True, probe=20_000):
    """Return (sat?, colouring or None).

    A short single-solver probe catches the easy instances for free; everything
    else goes to cube-and-conquer.  The probe budget is deliberately small --
    a generous one wastes minutes solving a hard UNSAT serially that the cubes
    would have split across 16 cores.  Cube results are consumed as they
    complete, not in submission order, so one slow cube cannot hold up a SAT
    answer."""
    if probe:
        r, col = solve_direct(n, j, targets, conflicts=probe, symbreak=symbreak)
        if r is True:
            return True, col
        if r is False:
            return False, None
    if k is None:
        k = 4 if len(targets) == 2 else 3
    cubes = make_cubes(n, j, targets, k)
    if not cubes:
        return False, None
    tasks = [(n, j, targets, c, symbreak) for c in cubes]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_cube_job, t) for t in tasks]
        done = 0
        try:
            for f in as_completed(futs):
                res = f.result()          # a dead worker must not be mistaken for UNSAT
                done += 1
                if res is not None:
                    return True, res
        finally:
            for f in futs:
                f.cancel()
        if done != len(futs):
            raise RuntimeError(f'only {done}/{len(futs)} cubes completed; UNSAT not proven')
    return False, None


def check(col, targets, j):
    """Independent verifier -- reads only the colouring, never the CNF."""
    n = len(col)
    wild = sum(1 for c in col if c == 0)
    if wild > j:
        return False, wild, ('wildcard budget', wild, j)
    for c, t in enumerate(targets, start=1):
        pos = [i + 1 for i, x in enumerate(col) if x == c]
        ps = set(pos)
        for a in pos:
            for d in range(1, n):
                if a + (t - 1) * d > n:
                    break
                if all((a + m * d) in ps for m in range(t)):
                    return False, wild, ('mono AP', c, a, d)
    return True, wild, None


if __name__ == '__main__':
    n, j = int(sys.argv[1]), int(sys.argv[2])
    targets = [int(a) for a in sys.argv[3:]]
    t0 = time.time()
    ok, col = solve_par(n, j, targets)
    dt = time.time() - t0
    print(f'n={n} j={j} targets={targets}: {"SAT" if ok else "UNSAT"}  {dt:.2f}s')
    if ok:
        print('  verify:', check(col, targets, j))
