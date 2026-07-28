"""Extend one mixed van der Waerden family by one term, durably.

Design notes, all of them paid for by a failure that already happened tonight:

* RESUMABLE.  Every decided n is checkpointed to state_<seq>.json the moment it
  is decided.  Restarting the script re-reads that file and skips finished
  work, so a frozen terminal, a session limit or a reboot costs one instance,
  not the run.

* DETACHED.  Launched with Start-Process (see launch_run.ps1) it is a child of
  nothing in particular, so closing or freezing the chat window does not kill
  it.  Three earlier attempts died exactly that way.

* MEMORY-BOUNDED.  This machine has ~6 GB free and 8 physical cores.  Sixteen
  concurrent CaDiCaLs, each growing an unbounded learned-clause database, is
  what exhausted RAM, orphaned 39 worker processes and froze the desktop.
  Workers are capped and recycled after every cube so memory returns to the OS.

* CRASH-HONEST.  UNSAT is only ever reported when every single cube has
  returned an explicit verdict.  A worker killed by the OS raises; it is never
  mistaken for "this branch has no solutions".  That distinction is the whole
  difference between a new theorem and a retraction.

Usage:  python vdw_run.py A217058 [--workers 8] [--k 6] [--start N]
"""
import argparse
import json
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

from vdw4 import _cube_job, check, make_cubes, solve_direct

HERE = os.path.dirname(os.path.abspath(__file__))

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


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def solve_checked(n, j, targets, k, workers, engine, probe=20_000):
    """(sat?, colouring).  Raises unless every cube reported a verdict."""
    if probe:
        r, col = solve_direct(n, j, targets, conflicts=probe, engine=engine)
        if r is True:
            return True, col, 'probe'
        if r is False:
            return False, None, 'probe'
    cubes = make_cubes(n, j, targets, k)
    if not cubes:
        return False, None, 'no-cubes'
    tasks = [(n, j, targets, c, True, True, engine) for c in cubes]
    done = 0
    # max_tasks_per_child: a worker is retired after each cube, which hands the
    # solver's memory straight back to the OS instead of letting it accumulate.
    with ProcessPoolExecutor(max_workers=workers, max_tasks_per_child=1) as ex:
        futs = [ex.submit(_cube_job, t) for t in tasks]
        try:
            for f in as_completed(futs):
                res = f.result()
                done += 1
                if res is not None:
                    return True, res, f'cube {done}/{len(tasks)}'
        finally:
            for f in futs:
                f.cancel()
    if done != len(tasks):
        raise RuntimeError(f'only {done}/{len(tasks)} cubes reported -- UNSAT NOT proven')
    return False, None, f'all {len(tasks)} cubes'


def solve_resilient(n, j, targets, k, workers, engine, attempts=3):
    """Retry with progressively gentler settings; a crash must cost time, not
    correctness."""
    last = None
    for a in range(attempts):
        w = max(2, workers - 3 * a)
        kk = k + a                      # more, smaller cubes on each retry
        try:
            return solve_checked(n, j, targets, kk, w, engine)
        except Exception as e:
            last = e
            log(f'    attempt {a+1}/{attempts} failed (workers={w} k={kk}): '
                f'{type(e).__name__}: {e}')
            time.sleep(5)
    raise RuntimeError(f'all {attempts} attempts failed at n={n}: {last}')


def statefile(seq):
    return os.path.join(HERE, f'state_{seq}.json')


def load_state(seq, targets, vals, jnew):
    p = statefile(seq)
    if os.path.exists(p):
        st = json.load(open(p))
        if st.get('seq') == seq and st.get('j_new') == jnew:
            return st
    return {'seq': seq, 'targets': targets, 'known': vals, 'j_new': jnew,
            'probes': {}, 'started': time.strftime('%Y-%m-%d %H:%M:%S')}


def save_state(st):
    p = statefile(st['seq'])
    json.dump(st, open(p, 'w'), indent=1)
    os.replace(p, p)                    # cheap durability nudge


def run(seq, workers, k, engine, start=None):
    targets, vals = FAM[seq]
    jm = len(vals) - 1
    jnew = jm + 1
    st = load_state(seq, targets, vals, jnew)

    log(f'{seq}: targets={targets}  published a(0..{jm}) last = a({jm})={vals[jm]}')
    log(f'goal: a({jnew}) = w({jnew + len(targets)}; 2^{jnew}, '
        f'{", ".join(map(str, targets))})   [unpublished]')
    log(f'engine={engine} workers={workers} k={k}')

    # a(j) is non-decreasing: any witness for j can absorb one more wildcard.
    n = start if start is not None else vals[jm]
    while str(n) in st['probes'] and st['probes'][str(n)]['sat']:
        n += 1

    best_col = st.get('best_col')
    while True:
        if str(n) in st['probes']:
            rec = st['probes'][str(n)]
            log(f'n={n:4d} {"SAT" if rec["sat"] else "UNSAT"} (from checkpoint)')
            if not rec['sat']:
                break
            best_col = rec.get('col') or best_col
            n += 1
            continue

        t0 = time.time()
        sat, col, how = solve_resilient(n, jnew, targets, k, workers, engine)
        dt = time.time() - t0

        if sat:
            good, wild, bad = check(col, targets, jnew)
            if not good:
                raise AssertionError(f'witness rejected at n={n}: {bad}')
            best_col = col
            st['best_col'] = col
            st['probes'][str(n)] = {'sat': True, 'sec': dt, 'via': how,
                                    'wildcards': wild, 'col': col}
            save_state(st)
            log(f'n={n:4d} SAT   {dt:8.1f}s  ({how}, {wild}/{jnew} wildcards, verified)')
            n += 1
        else:
            st['probes'][str(n)] = {'sat': False, 'sec': dt, 'via': how}
            save_state(st)
            log(f'n={n:4d} UNSAT {dt:8.1f}s  ({how})')
            break

    w = n
    good, wild, bad = check(best_col, targets, jnew)
    st.update({'value': w, 'witness_n': w - 1, 'witness': best_col,
               'witness_verified': bool(good), 'witness_wildcards': wild,
               'finished': time.strftime('%Y-%m-%d %H:%M:%S')})
    save_state(st)
    json.dump(st, open(os.path.join(HERE, f'result_{seq}.json'), 'w'), indent=1)

    log('')
    log(f'=== {seq}:  a({jnew}) = w({jnew + len(targets)}; 2^{jnew}, '
        f'{", ".join(map(str, targets))}) = {w} ===')
    log(f'    previously published last term: a({jm}) = {vals[jm]}')
    log(f'    lower bound witness at n={w-1}: verified={good}, '
        f'wildcards {wild} <= {jnew}')
    log(f'    upper bound: UNSAT at n={w}')
    return st


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('seq')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--k', type=int, default=6)
    ap.add_argument('--engine', default='Cadical195')
    ap.add_argument('--start', type=int, default=None)
    a = ap.parse_args()
    try:
        run(a.seq, a.workers, a.k, a.engine, a.start)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
