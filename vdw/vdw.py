"""Mixed van der Waerden numbers  w(j+r; 2^j, t_1, ..., t_r).

A colour with target 2 admits an AP of length 2 = any two elements, so such a
colour class holds at most one element.  Hence

    w(j+r; 2^j, t_1..t_r) = 1 + max{ n : exists S subset [n], |S| <= j, and an
                                     r-colouring of [n]\\S with no t_i-term AP
                                     in colour i }

Encoding: one variable per (position, class) with class in {S, 1..r};
exactly-one per position; |S| <= j via a totalizer; one clause per bad AP.

Verification of a SAT answer is trivial and is done independently in `check`.
"""
import sys
import time

from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from pysat.solvers import Cadical195


def aps(n, t):
    """All t-term APs inside [1, n]."""
    out = []
    for d in range(1, (n - 1) // (t - 1) + 1):
        for a in range(1, n - (t - 1) * d + 1):
            out.append([a + k * d for k in range(t)])
    return out


def build(n, j, targets):
    """CNF for: can [1,n] be coloured with <=j wildcards and no t_i-AP in colour i?"""
    r = len(targets)
    pool = IDPool()
    v = lambda i, c: pool.id(('v', i, c))          # c = 0 -> wildcard, 1..r -> real colour
    cnf = []
    for i in range(1, n + 1):
        cnf.append([v(i, c) for c in range(r + 1)])
        for c1 in range(r + 1):
            for c2 in range(c1 + 1, r + 1):
                cnf.append([-v(i, c1), -v(i, c2)])
    for c, t in enumerate(targets, start=1):
        for ap in aps(n, t):
            cnf.append([-v(i, c) for i in ap])
    card = CardEnc.atmost(lits=[v(i, 0) for i in range(1, n + 1)], bound=j,
                          vpool=pool, encoding=EncType.totalizer)
    cnf.extend(card.clauses)
    return cnf, pool, v


def solve(n, j, targets, timeout=None):
    """Return (True, colouring) if a good colouring of [1,n] exists, else (False, None)."""
    cnf, pool, v = build(n, j, targets)
    r = len(targets)
    with Cadical195(bootstrap_with=cnf) as s:
        ok = s.solve()
        if not ok:
            return False, None
        model = set(l for l in s.get_model() if l > 0)
        col = []
        for i in range(1, n + 1):
            col.append(next(c for c in range(r + 1) if v(i, c) in model))
        return True, col


def check(col, targets):
    """Independent verifier: recompute wildcard count and scan every AP by hand."""
    n = len(col)
    wild = sum(1 for c in col if c == 0)
    for c, t in enumerate(targets, start=1):
        pos = [i + 1 for i, x in enumerate(col) if x == c]
        ps = set(pos)
        for a in pos:
            for d in range(1, n):
                if all((a + k * d) in ps for k in range(t)):
                    if a + (t - 1) * d <= n:
                        return False, wild, (c, a, d)
    return True, wild, None


def wvalue(j, targets, lo=1, hi=400, verbose=True):
    """Least n that is UNSAT = the van der Waerden number."""
    n = lo
    last_col = None
    while n <= hi:
        t0 = time.time()
        ok, col = solve(n, j, targets)
        if verbose:
            print(f'    n={n:4d} {"SAT  " if ok else "UNSAT"} {time.time()-t0:8.2f}s', flush=True)
        if not ok:
            return n, last_col
        last_col = col
        n += 1
    return None, last_col


if __name__ == '__main__':
    j = int(sys.argv[1])
    targets = [int(a) for a in sys.argv[2:]]
    t0 = time.time()
    w, col = wvalue(j, targets, lo=1)
    print(f'w({j}+{len(targets)}; 2^{j}, {targets}) = {w}   [{time.time()-t0:.1f}s]')
    if col:
        ok, wild, bad = check(col, targets)
        print(f'  witness for n={len(col)}: verified={ok} wildcards={wild} (limit {j}) bad={bad}')
