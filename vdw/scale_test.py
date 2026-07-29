"""Close the gap the exhaustive audit cannot reach.

encoding_audit.py proves the CNF equals the definition, but only on instances
small enough to enumerate -- n <= 12, j <= 3.  The real instances are n ~ 58
with j = 12, and the one component whose behaviour genuinely depends on the
bound is the at-most-j wildcard constraint (a totalizer, whose structure grows
with the bound).  A bug that only appears at j = 12 would slip through the
small-case audit and would corrupt an UNSAT result in the worst possible way:
too *strong* a cardinality constraint forbids legal colourings, and the solver
then refutes an instance that actually has a witness.

So the constraint is tested at the exact sizes used, from both sides:

  at the limit   any assignment with exactly j wildcards must remain possible
  over the limit any assignment with j+1 wildcards must be rejected

and then the same thing again inside the full formula, by forcing j+1 positions
to be wildcards and requiring the result to be UNSAT.

Usage:  python scale_test.py
"""
import random
import sys

from pysat.card import CardEnc, EncType
from pysat.formula import IDPool
from pysat.solvers import Cadical195

from vdw4 import build

SIZES = [(58, 12), (57, 12), (56, 12), (55, 12)]
TRIALS = 60


def main():
    ok = True
    print(f'=== cardinality constraint at the exact scale used ===')
    for n, j in SIZES:
        pool = IDPool()
        xs = [pool.id(('x', i)) for i in range(n)]
        cnf = CardEnc.atmost(lits=xs, bound=j, vpool=pool,
                             encoding=EncType.totalizer).clauses
        rng = random.Random(7)
        lost = allowed = 0
        for _ in range(TRIALS):
            on = rng.sample(range(n), j)
            with Cadical195(bootstrap_with=cnf) as s:
                if not s.solve(assumptions=[xs[i] for i in on]):
                    lost += 1
        for _ in range(TRIALS):
            on = rng.sample(range(n), j + 1)
            with Cadical195(bootstrap_with=cnf) as s:
                if s.solve(assumptions=[xs[i] for i in on]):
                    allowed += 1
        good = (lost == 0 and allowed == 0)
        ok &= good
        print(f'  n={n} bound={j}: {TRIALS} at-limit accepted '
              f'({lost} wrongly lost), {TRIALS} over-limit rejected '
              f'({allowed} wrongly allowed) -> {"ok" if good else "FAIL"}')

    print()
    print('=== inside the full formula: the wildcard budget really binds ===')
    n, j, targets = 56, 12, [3, 4]
    cnf, pool, v = build(n, j, targets)
    rng = random.Random(11)
    for _ in range(5):
        on = rng.sample(range(1, n + 1), j + 1)
        with Cadical195(bootstrap_with=cnf) as s:
            r = s.solve(assumptions=[v(i, 0) for i in on])
        ok &= not r
        print(f'  forcing {j+1} wildcards: '
              f'{"SAT *** BUG ***" if r else "UNSAT (correct)"}')

    print()
    print('SCALE TEST PASSED' if ok else '*** SCALE TEST FAILED ***')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
