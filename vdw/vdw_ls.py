"""Stochastic local search for the LOWER-bound half of a mixed van der Waerden
number: find a colouring of [1,n] into {wildcard, 1..r} that uses at most j
wildcards and contains no t_i-term AP in colour i.

Min-conflicts with random walk and restarts.  This is far faster than a SAT
solver for satisfiable instances near the threshold, which leaves the solver
free to do the part only it can do -- the UNSAT proof.

Anything found here is a certificate, and is re-checked by vdw2.check, which
reads only the colouring.
"""
import sys
import time

import numpy as np


def ap_list(n, t):
    out = []
    for d in range(1, (n - 1) // (t - 1) + 1):
        for a in range(1, n - (t - 1) * d + 1):
            out.append([a + k * d - 1 for k in range(t)])       # 0-based
    return np.array(out, dtype=np.int32)


def search(n, j, targets, seconds=60, seed=0, restarts_every=200_000):
    r = len(targets)
    rng = np.random.default_rng(seed)
    APS = [ap_list(n, t) for t in targets]                      # per colour
    # positions -> list of (colour, ap index) they take part in
    member = [[[] for _ in range(n)] for _ in range(r)]
    for c in range(r):
        for idx, ap in enumerate(APS[c]):
            for p in ap:
                member[c][p].append(idx)
    member = [[np.array(m, dtype=np.int32) for m in mc] for mc in member]

    best_state, t0 = None, time.time()
    while time.time() - t0 < seconds:
        col = rng.integers(1, r + 1, size=n)
        wild = rng.choice(n, size=j, replace=False)
        col[wild] = 0
        steps = 0
        while time.time() - t0 < seconds and steps < restarts_every:
            steps += 1
            bad = []
            for c in range(r):
                if len(APS[c]) == 0:
                    continue
                m = (col[APS[c]] == c + 1).all(axis=1)
                if m.any():
                    for idx in np.flatnonzero(m):
                        bad.append((c, idx))
            if not bad:
                return list(int(x) for x in col), steps, time.time() - t0
            c, idx = bad[int(rng.integers(0, len(bad)))]
            ap = APS[c][idx]
            p = int(ap[rng.integers(0, len(ap))])
            if rng.random() < 0.25:                             # random walk
                newc = int(rng.integers(0, r + 1))
                if newc == 0 and (col == 0).sum() >= j and col[p] != 0:
                    q = int(rng.choice(np.flatnonzero(col == 0)))
                    col[q] = int(rng.integers(1, r + 1))
                col[p] = newc
                if (col == 0).sum() > j:
                    z = np.flatnonzero(col == 0)
                    col[int(rng.choice(z))] = int(rng.integers(1, r + 1))
                continue
            # greedy: try every class for p, keep the one with fewest mono APs
            bestc, bestv = col[p], 10 ** 9
            for cand in range(r + 1):
                if cand == 0 and col[p] != 0 and (col == 0).sum() >= j:
                    continue
                old = col[p]
                col[p] = cand
                v = 0
                for cc in range(r):
                    ids = member[cc][p]
                    if len(ids):
                        v += int((col[APS[cc][ids]] == cc + 1).all(axis=1).sum())
                col[p] = old
                if v < bestv or (v == bestv and rng.random() < 0.3):
                    bestc, bestv = cand, v
            col[p] = bestc
    return None, 0, time.time() - t0


if __name__ == '__main__':
    n, j = int(sys.argv[1]), int(sys.argv[2])
    targets = [int(a) for a in sys.argv[3:]]
    col, steps, dt = search(n, j, targets, seconds=120)
    if col is None:
        print(f'no colouring found for n={n} j={j} {targets} in {dt:.1f}s')
    else:
        from vdw2 import check
        print(f'FOUND n={n} j={j} {targets} in {dt:.2f}s ({steps} steps)')
        print('  verify:', check(col, targets, j))
        print('  colouring:', ''.join(str(c) for c in col))
