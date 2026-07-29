"""Decide ONE instance (n, j, targets) and record the verdict durably.

The climb in vdw_run.py walks n upward from the previous term, but satisfiability
here is monotone -- truncating a witness for n to [1,m] is a witness for m, since
no new AP and no new wildcard can appear -- so every step below the answer is
wasted work.  a(12) is the least n that is UNSAT, and the two halves that
establish it are independent:

    lower bound   witness at n = a(12)-1     (SAT)
    upper bound   no colouring at n = a(12)  (UNSAT)

so they are run as separate concurrent processes, each with its own slice of
the cores, rather than one after the other.

Every SAT answer is re-verified by `check` before being written, and the
certificate is emitted in the same '.'/digit alphabet that
verify_certificate.py consumes, so the result can be checked by a program that
shares no code with the solver.

Usage:  python vdw_probe.py <n> <j> <t1> <t2> [--workers 4] [--k 4] [--tag name]
"""
import argparse
import json
import os
import threading
import time
import traceback

import vdw_run
from vdw4 import check
from vdw_run import solve_resilient

HERE = os.path.dirname(os.path.abspath(__file__))
LOGDIR = os.path.join(os.path.dirname(HERE), 'logs')

_LOGF = None


def log(m):
    """Write progress to stdout AND to a file the script owns itself.

    Relying on the launcher to redirect stdout lost every line of two hours of
    unattended compute once already -- shell quoting between bash, PowerShell
    and Start-Process is one layer too many.  Owning the file here removes that
    failure mode: the log exists because Python opened it.
    """
    line = f'[{time.strftime("%H:%M:%S")}] {m}'
    print(line, flush=True)
    if _LOGF is not None:
        _LOGF.write(line + '\n')
        _LOGF.flush()
        os.fsync(_LOGF.fileno())


def open_log(tag):
    global _LOGF
    os.makedirs(LOGDIR, exist_ok=True)
    _LOGF = open(os.path.join(LOGDIR, f'probe_{tag}.log'), 'a', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('n', type=int)
    ap.add_argument('j', type=int)
    ap.add_argument('targets', type=int, nargs='+')
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--k', type=int, default=4)
    ap.add_argument('--engine', default='Cadical195')
    ap.add_argument('--tag', default=None)
    ap.add_argument('--no-revsym', action='store_true',
                    help='search the unreduced space (for independent re-derivation)')
    a = ap.parse_args()

    tag = a.tag or f'n{a.n}_j{a.j}'
    open_log(tag)
    out = os.path.join(HERE, f'probe_{tag}.json')
    log(f'probe n={a.n} j={a.j} targets={a.targets} workers={a.workers} '
        f'k={a.k} engine={a.engine} revsym={not a.no_revsym} pid={os.getpid()}')

    # retry/step-down messages from the solver belong in this log too
    vdw_run.log = log

    t0 = time.time()

    # An UNSAT proof at this size can run for hours with nothing to say.  A
    # heartbeat distinguishes "still working" from "silently dead", which is
    # the only question that matters when checking on it from a new session.
    stop = threading.Event()

    def beat():
        while not stop.wait(300):
            log(f'  ... still running, {(time.time()-t0)/60:.0f} min elapsed')

    hb = threading.Thread(target=beat, daemon=True)
    hb.start()
    try:
        sat, col, how = solve_resilient(a.n, a.j, a.targets, a.k, a.workers,
                                        a.engine, revsym=not a.no_revsym)
    finally:
        stop.set()
    dt = time.time() - t0

    rec = {'n': a.n, 'j': a.j, 'targets': a.targets, 'sat': bool(sat),
           'sec': dt, 'via': how, 'workers': a.workers, 'k': a.k,
           'engine': a.engine, 'revsym': not a.no_revsym,
           'finished': time.strftime('%Y-%m-%d %H:%M:%S')}

    if sat:
        good, wild, bad = check(col, a.targets, a.j)
        cert = ''.join('.' if c == 0 else str(c) for c in col)
        rec.update({'witness_verified': bool(good), 'wildcards': wild,
                    'colouring': col, 'certificate': cert})
        if not good:
            rec['rejected'] = str(bad)
            log(f'*** WITNESS REJECTED: {bad} ***')
        else:
            open(os.path.join(HERE, f'cert_{tag}.txt'), 'w').write(cert)
            log(f'SAT   {dt:.1f}s  ({how})  wildcards {wild}/{a.j}  witness verified')
            log(f'  certificate written to cert_{tag}.txt')
            log(f'  {cert}')
    else:
        log(f'UNSAT {dt:.1f}s  ({how})')

    json.dump(rec, open(out, 'w'), indent=1)
    log(f'wrote {out}')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
