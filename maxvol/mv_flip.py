"""Triangulation-flip search for maximal-volume inscribed polytopes.

Coordinate perturbation always relaxes back into the incumbent basin, because a
basin here is really a *combinatorial type*: a triangulation of S^2 on N
vertices.  So search that space directly.

  * For a FIXED oriented triangulation F the volume  V = 1/6 sum_f det(a,b,c)
    is smooth and its gradient is exact -- no hull recomputation in the loop.
  * An edge flip replaces the two triangles sharing an edge by the other
    diagonal, moving to an adjacent combinatorial type.
  * After re-optimising, the *true* convex hull volume is what gets reported.
    Signed volume of a closed inscribed surface never exceeds the hull volume,
    so any configuration produced is a legitimate lower bound however weird the
    intermediate triangulation was.

Run:  python mv_flip.py <lo> <hi> <seconds-per-N> [workers]
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull

from mv_core import REF, hull_volume

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mv_flip_results.json')


def incumbent(N):
    P = np.loadtxt(os.path.join(HERE, 'mvref', f'maxvol.3.{N}.txt')).reshape(N, 3)
    return P / np.linalg.norm(P, axis=1, keepdims=True)


def oriented_faces(P):
    """Hull faces, each oriented so that det(a,b,c) > 0 (outward)."""
    S = ConvexHull(P).simplices.copy()
    d = np.einsum('ij,ij->i', P[S[:, 0]], np.cross(P[S[:, 1]], P[S[:, 2]]))
    S[d < 0] = S[d < 0][:, [0, 2, 1]]
    return S


def edge_map(F):
    """directed edge (a,b) -> face index that traverses it in that direction."""
    m = {}
    for fi, (a, b, c) in enumerate(F):
        m[(a, b)] = fi
        m[(b, c)] = fi
        m[(c, a)] = fi
    return m


def flip(F, rng):
    """One random valid edge flip.  Returns a new face array or None."""
    em = edge_map(F)
    keys = list(em.keys())
    rng.shuffle(keys)
    deg = np.bincount(F.ravel(), minlength=F.max() + 1)
    for (u, v) in keys:
        f1 = em.get((u, v))
        f2 = em.get((v, u))
        if f1 is None or f2 is None or f1 == f2:
            continue
        w = int([x for x in F[f1] if x not in (u, v)][0])
        x = int([y for y in F[f2] if y not in (u, v)][0])
        if w == x:
            continue
        if (w, x) in em or (x, w) in em:        # edge already present -> illegal
            continue
        if deg[u] <= 3 or deg[v] <= 3:          # would strand a vertex
            continue
        G = F.copy()
        G[f1] = [u, x, w]
        G[f2] = [x, v, w]
        return G
    return None


def vol_grad_fixed(z, F, N):
    """-V and gradient for a FIXED oriented face list."""
    P = z.reshape(N, 3)
    nrm = np.linalg.norm(P, axis=1, keepdims=True)
    U = P / nrm
    A, B, C = U[F[:, 0]], U[F[:, 1]], U[F[:, 2]]
    cr = np.cross(B, C)
    V = np.einsum('ij,ij->i', A, cr).sum() / 6.0
    g = np.zeros((N, 3))
    np.add.at(g, F[:, 0], cr / 6.0)
    np.add.at(g, F[:, 1], np.cross(C, A) / 6.0)
    np.add.at(g, F[:, 2], np.cross(A, B) / 6.0)
    dot = np.einsum('ij,ij->i', g, U)[:, None]
    return -V, -((g - dot * U) / nrm).ravel()


def opt_fixed(P, F, maxiter=4000):
    N = len(P)
    r = minimize(vol_grad_fixed, P.ravel(), args=(F, N), jac=True, method='L-BFGS-B',
                 options={'maxiter': maxiter, 'maxfun': 2 * maxiter, 'ftol': 1e-18, 'gtol': 1e-14})
    Q = r.x.reshape(N, 3)
    Q /= np.linalg.norm(Q, axis=1, keepdims=True)
    return Q


def polish(P, rounds=8, tol=1e-15):
    """Re-optimise against the true hull until the combinatorics stop changing.

    Two or three rounds almost always suffice; the cap keeps the move rate high
    during search.  Promising candidates get re-polished with more rounds."""
    Q = P
    last = -1.0
    for _ in range(rounds):
        F = oriented_faces(Q)
        Q = opt_fixed(Q, F)
        v = hull_volume(Q)
        if v <= last + tol:
            break
        last = v
    return last, Q


def search(N, seconds, seed0, T=2e-6):
    rng = np.random.default_rng(seed0)
    P = incumbent(N)
    best, bx = polish(P)
    cur_v, cur_x = best, bx.copy()
    t0, tried, moved = time.time(), 0, 0
    while time.time() - t0 < seconds:
        tried += 1
        F = oriented_faces(cur_x)
        G = F
        for _ in range(int(rng.integers(1, 4))):      # 1-3 flips per move
            H = flip(G, rng)
            if H is None:
                break
            G = H
        if G is F:
            continue
        try:
            Q = opt_fixed(cur_x, G)
            v, Q = polish(Q, rounds=3)
            if v > best - 1e-6:                        # only the near-misses earn a full polish
                v, Q = polish(Q, rounds=25)
        except Exception:
            continue
        moved += 1
        if v > best + 1e-14:
            best, bx = v, Q
        if v > cur_v or rng.random() < np.exp(min(0.0, (v - cur_v) / T)):
            cur_v, cur_x = v, Q
        if rng.random() < 0.03:
            cur_v, cur_x = best, bx.copy()
    return best, bx, tried, moved


def job(a):
    N, secs, seed0 = a
    v, x, tried, moved = search(N, secs, seed0)
    return N, v, x.tolist(), tried, moved


if __name__ == '__main__':
    lo, hi, secs = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    W = int(sys.argv[4]) if len(sys.argv) > 4 else 16
    Ns = [n for n in sorted(REF) if lo <= n <= hi]
    res = json.load(open(OUT)) if os.path.exists(OUT) else {}
    t0, nbeat = time.time(), 0
    with ProcessPoolExecutor(max_workers=W) as ex:
        for N, v, x, tried, moved in ex.map(job, [(N, secs, 91 + 7919 * N) for N in Ns]):
            d = v - REF[N]
            if str(N) not in res or v > res[str(N)]['v']:
                res[str(N)] = {'v': v, 'ref': REF[N], 'delta': d, 'x': x}
            json.dump(res, open(OUT, 'w'))
            tag = ''
            if d > 1e-11:
                tag = '   <<<<<< BEATS 1994'
                nbeat += 1
            print(f'N={N:4d} ref={REF[N]:.12f} best={v:.12f} delta={d:+.3e} '
                  f'flips={moved:5d}{tag}', flush=True)
    print(f'\n{nbeat} improvements in {time.time()-t0:.0f}s')
