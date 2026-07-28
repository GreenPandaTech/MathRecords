"""Difficulty survey: time the UNSAT step for the last few known terms of every
family, one instance per core, so the growth rate per family is measured under
identical conditions.  This decides which frontier is cheapest to extend."""
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

from pysat.solvers import Cadical195

from vdw2 import build

HERE = os.path.dirname(os.path.abspath(__file__))

FAM = [
    ('A217005', [3, 3],    [9, 14, 17, 20, 21, 24, 25, 28, 31, 33, 35, 37, 39, 42, 44, 46, 48, 50, 51]),
    ('A217007', [4, 4],    [35, 40, 53, 54, 56, 66, 67]),
    ('A217008', [3, 3, 3], [27, 40, 41, 42, 45, 49, 52]),
    ('A217058', [3, 4],    [18, 21, 25, 29, 33, 36, 40, 42, 45, 48, 52, 55]),
    ('A217059', [3, 5],    [22, 32, 43, 44, 50, 55, 61, 65, 70]),
    ('A217060', [3, 6],    [32, 40, 48, 56, 60, 65, 71]),
    ('A217236', [4, 5],    [55, 71, 75, 79]),
    ('A217237', [4, 6],    [73, 83, 93, 101]),
]


def one(args):
    lab, tg, j, n, budget = args
    cnf, pool, v = build(n, j, tg, symbreak=True)
    t0 = time.time()
    with Cadical195(bootstrap_with=cnf) as s:
        s.conf_budget(budget)
        r = s.solve_limited()
    dt = time.time() - t0
    status = {True: 'SAT', False: 'UNSAT', None: 'TIMEOUT'}[r]
    return lab, tg, j, n, status, dt, len(cnf), pool.top


if __name__ == '__main__':
    tasks = []
    for lab, tg, vals in FAM:
        jm = len(vals) - 1
        for j in range(max(0, jm - 3), jm + 1):        # last four known terms
            tasks.append((lab, tg, j, vals[j], 200_000_000))
    tasks.sort(key=lambda t: t[3])
    out = []
    with ProcessPoolExecutor(max_workers=16) as ex:
        for r in ex.map(one, tasks):
            lab, tg, j, n, status, dt, nc, nv = r
            flag = '' if status == 'UNSAT' else f'   <<< {status}'
            print(f'{lab:9s} {str(tg):9s} j={j:2d} n={n:4d}  {status:7s} {dt:9.2f}s '
                  f'({nc} clauses, {nv} vars){flag}', flush=True)
            out.append({'seq': lab, 'targets': tg, 'j': j, 'n': n,
                        'status': status, 'sec': dt})
            json.dump(out, open(os.path.join(HERE, 'vdw_survey.json'), 'w'), indent=1)

    print('\n=== growth per family (single core, symmetry-broken) ===')
    for lab, tg, vals in FAM:
        rows = [o for o in out if o['seq'] == lab and o['status'] == 'UNSAT']
        rows.sort(key=lambda o: o['j'])
        if len(rows) >= 2:
            ratios = [rows[i + 1]['sec'] / max(rows[i]['sec'], 1e-3) for i in range(len(rows) - 1)]
            g = sum(ratios) / len(ratios)
            last = rows[-1]
            miss = (len(vals) - 1) - last['j']
            est = last['sec'] * g ** (miss + 1)
            print(f'{lab:9s} {str(tg):9s} solved j<={last["j"]:2d} in {last["sec"]:8.1f}s  '
                  f'growth x{g:5.2f}/term  -> est. NEXT UNKNOWN term j={len(vals)}: '
                  f'{est:12.0f}s single-core ({est/3600:8.1f} h)')
        else:
            print(f'{lab:9s} {str(tg):9s} insufficient data ({len(rows)} UNSAT solved)')
