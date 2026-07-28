"""Pick the UNSAT engine before committing hours to it.

The whole cost of a new mixed van der Waerden term is the UNSAT proof at the
top of the climb, so a 2x engine is worth an hour of wall clock.  vdw2 used
Cadical195 because that is what the first draft reached for; pysat on this
machine also ships Cadical300 and Kissat404, and OR-Tools ships CP-SAT.

Benchmark instance: n=42, j=7, targets [3,4].  Published a(7)=42 for A217058,
so this is UNSAT, and it sits about 2.5x below the survey's j=8 point -- big
enough to rank engines, small enough to finish in minutes.

One core per engine, run concurrently.
"""
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from vdw2 import build

N, J, TARGETS = 42, 7, [3, 4]
LIMIT = 1200


def run_pysat(name):
    import pysat.solvers as ps
    cnf, pool, v = build(N, J, TARGETS, symbreak=True)
    cls = getattr(ps, name)
    t0 = time.time()
    with cls(bootstrap_with=cnf) as s:
        r = s.solve()
    return name, {True: 'SAT', False: 'UNSAT', None: '?'}[r], time.time() - t0


def run_cpsat(_):
    from ortools.sat.python import cp_model
    m = cp_model.CpModel()
    r = len(TARGETS)
    # x[i] in 0..r ; 0 = wildcard
    x = [m.NewIntVar(0, r, f'x{i}') for i in range(N)]
    lit = [[m.NewBoolVar(f'b{i}_{c}') for c in range(r + 1)] for i in range(N)]
    for i in range(N):
        m.AddExactlyOne(lit[i])
        for c in range(r + 1):
            m.Add(x[i] == c).OnlyEnforceIf(lit[i][c])
            m.Add(x[i] != c).OnlyEnforceIf(lit[i][c].Not())
    for c, t in enumerate(TARGETS, start=1):
        for d in range(1, (N - 1) // (t - 1) + 1):
            for a in range(0, N - (t - 1) * d):
                m.AddBoolOr([lit[a + k * d][c].Not() for k in range(t)])
    m.Add(sum(lit[i][0] for i in range(N)) <= J)
    sol = cp_model.CpSolver()
    sol.parameters.num_search_workers = 1
    sol.parameters.max_time_in_seconds = LIMIT
    t0 = time.time()
    st = sol.Solve(m)
    name = {cp_model.OPTIMAL: 'SAT', cp_model.FEASIBLE: 'SAT',
            cp_model.INFEASIBLE: 'UNSAT'}.get(st, '?')
    return 'CP-SAT', name, time.time() - t0


def job(spec):
    kind, name = spec
    try:
        return (run_cpsat(name) if kind == 'cpsat' else run_pysat(name))
    except Exception as e:                       # a missing/odd solver must not kill the bake-off
        return name, f'ERR {type(e).__name__}: {e}'[:120], -1.0


if __name__ == '__main__':
    specs = [('pysat', 'Cadical195'), ('pysat', 'Cadical300'),
             ('pysat', 'Kissat404'), ('pysat', 'MapleCM'), ('cpsat', 'CP-SAT')]
    print(f'instance n={N} j={J} targets={TARGETS} (expect UNSAT), one core each', flush=True)
    with ProcessPoolExecutor(max_workers=len(specs)) as ex:
        out = []
        for name, status, dt in ex.map(job, specs):
            print(f'  {name:12s} {status:8s} {dt:9.1f}s', flush=True)
            out.append((name, status, dt))
    ok = [o for o in out if o[1] == 'UNSAT']
    ok.sort(key=lambda o: o[2])
    print('\nranking (UNSAT only):', flush=True)
    for name, _, dt in ok:
        print(f'  {name:12s} {dt:9.1f}s', flush=True)
    if ok:
        print(f'\nWINNER: {ok[0][0]}', flush=True)
