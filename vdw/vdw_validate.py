"""Soundness gate for the vdw4 engine.

A new symmetry-breaking constraint is exactly the kind of change that can turn
a satisfiable instance into a spurious UNSAT, and a spurious UNSAT here means
publishing a wrong number under a real person's name.  So the engine is not
trusted on argument; it is made to re-derive published values.

For each published a(j) = w this replays the defining pair:
    SAT   at n = w-1   (and the witness is re-verified by `check`)
    UNSAT at n = w
Both halves must come out right or the run fails loudly.

Usage:
    python vdw_validate.py quick     # every family, cheap j only
    python vdw_validate.py full34    # the whole published A217058 sequence
"""
import json
import os
import sys
import time

from vdw4 import check, solve

HERE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(os.path.dirname(HERE), 'logs')
_LOGF = None


def _open_log(plan):
    global _LOGF
    os.makedirs(LOGDIR, exist_ok=True)
    _LOGF = open(os.path.join(LOGDIR, f'validate_{plan}.log'), 'a',
                 encoding='utf-8')


def _say(msg):
    """Print and persist.  Launcher-side stdout redirection has silently
    discarded whole runs on this box more than once."""
    print(msg, flush=True)
    if _LOGF:
        _LOGF.write(msg + '\n')
        _LOGF.flush()
        os.fsync(_LOGF.fileno())


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

PLANS = {
    # cheap breadth: catches an encoding bug in seconds, across every shape of
    # target list (equal targets, distinct targets, three colours)
    'quick':  [(s, j) for s, jj in [('A217005', range(0, 8)), ('A217007', range(0, 3)),
                                    ('A217008', range(0, 4)), ('A217058', range(0, 9)),
                                    ('A217059', range(0, 4)), ('A217060', range(0, 3)),
                                    ('A217236', range(0, 2)), ('A217237', range(0, 2))]
               for j in jj],
    # depth on the family being extended: the entire published sequence
    'full34': [('A217058', j) for j in range(0, 12)],
    # the only A217058 terms this engine has not yet reproduced: j=0..6 came
    # from the quick sweep, j=8 and j=9 from the earlier difficulty survey, and
    # j=11 from the full-scale gate. Finishing these two means every published
    # term of the sequence has been re-derived before a thirteenth is added.
    'rest34': [('A217058', 7), ('A217058', 10)],
    # j=9 was only ever confirmed with the older vdw2 engine; running it here
    # means every published term of A217058 has been re-derived by the engine
    # that produced the thirteenth.
    'j9':     [('A217058', 9)],
    # gate for the next family to be extended: A217005 = w(j+2; 2^j, 3, 3),
    # published through a(18)=51.  Equal targets, so the colour-swap breaker is
    # live here as well as the reversal one.
    'gate05': [('A217005', 18)],
}


def one(seq, j, k, engine, revsym=True, workers=4):
    targets, vals = FAM[seq]
    w = vals[j]
    t0 = time.time()
    sat_lo, col = solve(w - 1, j, targets, k=k, engine=engine, revsym=revsym,
                        workers=workers)
    t1 = time.time()
    good = wild = None
    if sat_lo:
        good, wild, bad = check(col, targets, j)
    sat_hi, _ = solve(w, j, targets, k=k, engine=engine, revsym=revsym,
                      workers=workers)
    t2 = time.time()
    ok = bool(sat_lo) and bool(good) and not sat_hi
    return {'seq': seq, 'targets': targets, 'j': j, 'w': w,
            'sat_at_w_minus_1': bool(sat_lo), 'witness_verified': bool(good),
            'wildcards_used': wild, 'unsat_at_w': not sat_hi,
            'sec_lo': t1 - t0, 'sec_hi': t2 - t1, 'PASS': ok}


def main():
    plan = sys.argv[1] if len(sys.argv) > 1 else 'quick'
    engine = sys.argv[2] if len(sys.argv) > 2 else 'Cadical195'
    k = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    # Explicit, because vdw4.solve defaults to 16 workers: running validation at
    # that width oversubscribes an 8-core box, starves whatever else is running
    # and is exactly what was orphaning workers and freezing the desktop.
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    cases = PLANS[plan]
    _open_log(plan)
    _say(f'plan={plan}  engine={engine}  k={k}  workers={workers}  cases={len(cases)}')
    _say(f'{"seq":10s} {"targets":10s} {"j":>3s} {"w":>4s}  '
         f'{"SAT(w-1)":9s} {"ver":4s} {"UNSAT(w)":9s} {"sec":>9s}  verdict')
    out, failures = [], []
    for seq, j in cases:
        r = one(seq, j, k, engine, workers=workers)
        out.append(r)
        if not r['PASS']:
            failures.append(r)
        _say(f'{r["seq"]:10s} {str(r["targets"]):10s} {r["j"]:3d} {r["w"]:4d}  '
             f'{str(r["sat_at_w_minus_1"]):9s} {str(r["witness_verified"]):4s} '
             f'{str(r["unsat_at_w"]):9s} {r["sec_lo"]+r["sec_hi"]:9.1f}  '
             f'{"PASS" if r["PASS"] else "*** FAIL ***"}')
        json.dump(out, open(os.path.join(HERE, f'validate_{plan}.json'), 'w'), indent=1)
    print(f'\n{len(out)-len(failures)}/{len(out)} published values reproduced', flush=True)
    if failures:
        _say('FAILURES: ' + json.dumps(failures, indent=1))
        sys.exit(1)
    _say('ENGINE ACCEPTED')


if __name__ == '__main__':
    main()
