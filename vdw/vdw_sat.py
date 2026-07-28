"""Randomised-restart portfolio for the SATISFIABLE half.

Cube-and-conquer is built for refutation: it splits the space so that every
branch can be closed.  For a *satisfiable* instance that is often the wrong
shape -- the work is dominated by whichever cubes happen to be hard, and a
witness sitting in an unvisited cube is found only when its turn comes.

The instances at the top of a van der Waerden climb are barely satisfiable, so
this runs the complementary strategy instead: many independent CDCL solvers on
the whole formula, each started with randomly perturbed initial phases and a
conflict budget, restarted with a fresh seed whenever the budget runs out.
Diversity does the work -- one lucky seed ends the search for everybody.

Phases are drawn from the class distribution an actual witness has (roughly a
fifth wildcards, the 3-AP-free colour sparser than the 4-AP-free one) rather
than uniformly, so the solver starts somewhere structurally plausible.

Any witness found is re-verified by `check` before it is written.

Usage:  python vdw_sat.py <n> <j> <t1> <t2> [--workers 5] [--budget 2000000]
"""
import argparse
import json
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from vdw4 import _solver, build, check

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


def attempt(args):
    """One seeded try.  Returns a colouring, or None if the budget ran out."""
    n, j, targets, seed, engine, budget = args
    r = len(targets)
    cnf, pool, v = build(n, j, targets, symbreak=True, revsym=True)
    rng = random.Random(seed)

    # class distribution taken from real witnesses rather than uniform
    wild_p = j / n
    weights = [wild_p] + [(1 - wild_p) * w for w in (0.38, 0.62)][:r]
    if r != 2:
        weights = [wild_p] + [(1 - wild_p) / r] * r
    classes = list(range(r + 1))

    phases = []
    for i in range(1, n + 1):
        c = rng.choices(classes, weights=weights)[0]
        phases.append(v(i, c))
        phases.extend(-v(i, d) for d in classes if d != c)

    with _solver(engine)(bootstrap_with=cnf) as s:
        try:
            s.set_phases(phases)
        except Exception:
            pass                       # phase hints are an optimisation, not a requirement
        s.conf_budget(budget)
        res = s.solve_limited()
        if res is not True:
            return None
        model = set(l for l in s.get_model() if l > 0)
        return [next(c for c in classes if v(i, c) in model) for i in range(1, n + 1)]


def main():
    global _LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int)
    ap.add_argument('j', type=int)
    ap.add_argument('targets', type=int, nargs='+')
    ap.add_argument('--workers', type=int, default=5)
    ap.add_argument('--budget', type=int, default=2_000_000)
    ap.add_argument('--engine', default='Cadical195')
    ap.add_argument('--rounds', type=int, default=1000)
    ap.add_argument('--tag', default=None)
    a = ap.parse_args()

    tag = a.tag or f'sat_n{a.n}'
    os.makedirs(LOGDIR, exist_ok=True)
    _LOGF = open(os.path.join(LOGDIR, f'{tag}.log'), 'a', encoding='utf-8')
    log(f'portfolio SAT search n={a.n} j={a.j} targets={a.targets} '
        f'workers={a.workers} budget={a.budget} pid={os.getpid()}')

    t0 = time.time()
    seed = 1
    for rnd in range(a.rounds):
        tasks = [(a.n, a.j, a.targets, seed + i, a.engine, a.budget)
                 for i in range(a.workers)]
        seed += a.workers
        with ProcessPoolExecutor(max_workers=a.workers,
                                 max_tasks_per_child=1) as ex:
            futs = [ex.submit(attempt, t) for t in tasks]
            got = None
            for f in as_completed(futs):
                try:
                    res = f.result()
                except Exception as e:
                    log(f'  worker died: {type(e).__name__}: {e}')
                    continue
                if res is not None:
                    got = res
                    break
            for f in futs:
                f.cancel()

        if got is not None:
            good, wild, bad = check(got, a.targets, a.j)
            cert = ''.join('.' if c == 0 else str(c) for c in got)
            dt = time.time() - t0
            if not good:
                log(f'*** witness REJECTED by check: {bad} -- ignoring ***')
                continue
            log(f'SAT after {dt:.1f}s, round {rnd+1}  '
                f'({wild}/{a.j} wildcards, witness verified)')
            log(f'  {cert}')
            open(os.path.join(HERE, f'cert_{tag}.txt'), 'w').write(cert)
            json.dump({'n': a.n, 'j': a.j, 'targets': a.targets, 'sat': True,
                       'sec': dt, 'rounds': rnd + 1, 'wildcards': wild,
                       'witness_verified': True, 'colouring': got,
                       'certificate': cert},
                      open(os.path.join(HERE, f'{tag}.json'), 'w'), indent=1)
            log(f'wrote {tag}.json')
            return 0
        log(f'  round {rnd+1}: {a.workers} seeds exhausted {a.budget} conflicts each, '
            f'{(time.time()-t0)/60:.0f} min elapsed')

    log('no witness found within the round budget (this is NOT a proof of UNSAT)')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
