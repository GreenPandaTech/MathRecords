"""Attack the Feb-1994 Hardin/Sloane/Smith maximal-volume records.

The incumbents are fully converged local maxima, so the only way through is to
reach a *different* basin.  The move-set is therefore structural rather than
random: on S^2 the hull is a triangulation whose vertices are mostly degree 6
with a scattering of degree-5/7 disclinations, and the good moves are the ones
that relocate a defect or move a point into an under-filled facet.

Run:  python mv_attack.py <lo> <hi> <seconds-per-N> [workers]
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.spatial import ConvexHull

from mv_core import REF, hull_volume, local

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mv_attack_results.json')


def incumbent(N):
    P = np.loadtxt(os.path.join(HERE, 'mvref', f'maxvol.3.{N}.txt')).reshape(N, 3)
    return P / np.linalg.norm(P, axis=1, keepdims=True)


def facet_data(P):
    h = ConvexHull(P)
    S = h.simplices
    A, B, C = P[S[:, 0]], P[S[:, 1]], P[S[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    cent = (A + B + C) / 3.0
    cent = cent / np.linalg.norm(cent, axis=1, keepdims=True)
    deg = np.bincount(S.ravel(), minlength=len(P))
    return S, area, cent, deg


def least_useful(P):
    """Index of the point whose deletion costs the least volume (vectorised enough)."""
    N = len(P)
    base = hull_volume(P)
    loss = np.empty(N)
    keep = np.ones(N, bool)
    for i in range(N):
        keep[i] = False
        try:
            loss[i] = base - hull_volume(P[keep])
        except Exception:
            loss[i] = np.inf
        keep[i] = True
    return int(np.argmin(loss))


def move(P, rng):
    """One structural perturbation of a converged configuration."""
    N = len(P)
    c = P.copy()
    m = rng.integers(0, 6)
    if m == 0:                                          # gentle global jiggle
        c += rng.normal(scale=rng.uniform(0.004, 0.09), size=c.shape)
    elif m == 1:                                        # relocate a defect vertex
        _, _, cent, deg = facet_data(c)
        cand = np.where(deg != 6)[0]
        if len(cand) == 0:
            cand = np.arange(N)
        i = int(rng.choice(cand))
        c[i] = cent[rng.integers(0, len(cent))] + rng.normal(scale=0.05, size=3)
    elif m == 2:                                        # least-useful point -> biggest facet
        i = least_useful(c)
        _, area, cent, _ = facet_data(c)
        p = area / area.sum()
        f = rng.choice(len(cent), p=p)
        c[i] = cent[f] + rng.normal(scale=0.02, size=3)
    elif m == 3:                                        # shake a defect and its neighbours
        S, _, _, deg = facet_data(c)
        cand = np.where(deg != 6)[0]
        i = int(rng.choice(cand)) if len(cand) else int(rng.integers(0, N))
        nb = np.unique(S[(S == i).any(axis=1)].ravel())
        c[nb] += rng.normal(scale=rng.uniform(0.05, 0.25), size=(len(nb), 3))
    elif m == 4:                                        # single random teleport
        c[rng.integers(0, N)] = rng.normal(size=3)
    else:                                               # patch rotation
        i = rng.integers(0, N)
        d = np.linalg.norm(c - c[i], axis=1)
        nb = np.argsort(d)[:max(3, int(rng.integers(3, max(4, N // 8))))]
        ang = rng.uniform(0.05, 0.6)
        ax = c[i] / np.linalg.norm(c[i])
        K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        R = np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)
        c[nb] = c[nb] @ R.T
    c /= np.linalg.norm(c, axis=1, keepdims=True)
    return c


def attack(N, seconds, seed0, T=3e-6):
    rng = np.random.default_rng(seed0)
    x0 = incumbent(N)
    best, bx = local(x0, N)
    cur_v, cur_x = best, bx.copy()
    t0, it = time.time(), 0
    while time.time() - t0 < seconds:
        it += 1
        try:
            v, xv = local(move(cur_x, rng), N)
        except Exception:
            continue
        if v > best:
            best, bx = v, xv
        if v > cur_v or rng.random() < np.exp(min(0.0, (v - cur_v) / T)):
            cur_v, cur_x = v, xv
        if rng.random() < 0.02:                         # occasional reset to the best
            cur_v, cur_x = best, bx.copy()
    return best, bx, it


def job(a):
    N, secs, seed0 = a
    v, x, it = attack(N, secs, seed0)
    return N, v, x.tolist(), it


if __name__ == '__main__':
    lo, hi, secs = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    W = int(sys.argv[4]) if len(sys.argv) > 4 else 16
    Ns = [n for n in sorted(REF) if lo <= n <= hi]
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    tasks = [(N, secs, 5150 + 31 * N) for N in Ns]
    t0 = time.time()
    nbeat = 0
    with ProcessPoolExecutor(max_workers=W) as ex:
        for N, v, x, it in ex.map(job, tasks):
            d = v - REF[N]
            prev = res.get(str(N))
            if prev is None or v > prev['v']:
                res[str(N)] = {'v': v, 'ref': REF[N], 'delta': d, 'x': x, 'iters': it}
            json.dump(res, open(OUT, 'w'))
            tag = ''
            if d > 1e-11:
                tag = '   <<<<<< BEATS 1994'
                nbeat += 1
            print(f'N={N:4d} ref={REF[N]:.12f} best={v:.12f} delta={d:+.3e} moves={it:6d}{tag}',
                  flush=True)
    print(f'\n{nbeat} improvements, {time.time()-t0:.0f}s')
