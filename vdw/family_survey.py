"""Rank the unexplored families by how hard their known frontier is.

Two terms have been added so far, both from families whose difficulty was
already measured.  Five families have never been timed here, and their costs are
not obvious from the shape of the problem: a larger n means more variables, but
these families also have far fewer wildcards (A217236 and A217237 are only four
terms in, so the next term runs at j=4 rather than j=19), and a small wildcard
budget makes the instance much more constrained and the refutation much easier.
Those two effects pull in opposite directions, so it is cheaper to measure than
to argue.

For each family this refutes n = a(last), the published value, under a conflict
budget on a single core.  Completing quickly means the family's frontier is
within reach and its next term is worth attacking; timing out means it is not,
at least not tonight.

Usage:  python family_survey.py [budget_conflicts] [workers]
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

from pysat.solvers import Cadical195

from vdw4 import build

HERE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(os.path.dirname(HERE), 'logs')

# family -> (targets, published terms).  Only the ones never timed here.
UNEXPLORED = [
    ('A217007', [4, 4],    [35, 40, 53, 54, 56, 66, 67]),
    ('A217059', [3, 5],    [22, 32, 43, 44, 50, 55, 61, 65, 70]),
    ('A217060', [3, 6],    [32, 40, 48, 56, 60, 65, 71]),
    ('A217236', [4, 5],    [55, 71, 75, 79]),
    ('A217237', [4, 6],    [73, 83, 93, 101]),
]


def one(args):
    seq, targets, j, n, budget = args
    t0 = time.time()
    try:
        cnf, pool, v = build(n, j, targets, symbreak=True, revsym=True)
        with Cadical195(bootstrap_with=cnf) as s:
            s.conf_budget(budget)
            r = s.solve_limited()
        dt = time.time() - t0
        status = {True: 'SAT', False: 'UNSAT', None: 'TIMEOUT'}[r]
        return {'seq': seq, 'targets': targets, 'j': j, 'n': n,
                'status': status, 'sec': dt, 'clauses': len(cnf),
                'vars': pool.top}
    except Exception as e:
        return {'seq': seq, 'targets': targets, 'j': j, 'n': n,
                'status': f'ERR {type(e).__name__}', 'sec': time.time() - t0}


def main():
    budget = int(sys.argv[1]) if len(sys.argv) > 1 else 60_000_000
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    os.makedirs(LOGDIR, exist_ok=True)
    logf = open(os.path.join(LOGDIR, 'family_survey.log'), 'a', encoding='utf-8')

    def say(m):
        print(m, flush=True)
        logf.write(m + '\n')
        logf.flush()
        os.fsync(logf.fileno())

    tasks = []
    for seq, targets, vals in UNEXPLORED:
        jlast = len(vals) - 1
        tasks.append((seq, targets, jlast, vals[jlast], budget))

    say(f'refuting n = a(last) for {len(tasks)} unexplored families, '
        f'budget {budget} conflicts, {workers} workers, one core each')
    say(f'{"seq":10s} {"targets":9s} {"j":>3s} {"n":>4s} {"status":8s} '
        f'{"sec":>9s}  {"clauses":>8s}')

    out = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, tasks):
            out.append(r)
            say(f'{r["seq"]:10s} {str(r["targets"]):9s} {r["j"]:3d} {r["n"]:4d} '
                f'{r["status"]:8s} {r["sec"]:9.1f}  {r.get("clauses", 0):8d}')
            json.dump(out, open(os.path.join(HERE, 'family_survey.json'), 'w'),
                      indent=1)

    done = sorted([r for r in out if r['status'] == 'UNSAT'], key=lambda r: r['sec'])
    say('')
    say('reachable frontiers, cheapest first:')
    for r in done:
        say(f'  {r["seq"]:10s} {str(r["targets"]):9s} refuted a({r["j"]})={r["n"]} '
            f'in {r["sec"]:.0f}s -> next term is a({r["j"]+1})')
    for r in out:
        if r['status'] != 'UNSAT':
            say(f'  {r["seq"]:10s} {r["status"]} -- out of reach tonight')


if __name__ == '__main__':
    main()
