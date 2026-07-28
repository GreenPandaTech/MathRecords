"""Core routines: maximise the volume of the convex hull of N points on S^2.

Target: the Hardin / Sloane / Smith table (Feb 1994), http://neilsloane.com/maxvolumes/
Live successor: https://cohn.mit.edu/sloane  -- diffed by recon, zero improvements in 32 years.

Bigger volume is better.  Reference values are printed to 12 dp.
"""
import json
import os

import numpy as np
from scipy.optimize import minimize
from scipy.spatial import ConvexHull

_HERE = os.path.dirname(os.path.abspath(__file__))
REF = {int(k): v for k, v in json.load(open(os.path.join(_HERE, 'maxvol_ref.json'))).items()}


def hull_volume(U):
    """Exact hull volume of unit vectors U (N,3)."""
    return ConvexHull(U).volume


def neg_vol_and_grad(x, N):
    """-V and its gradient wrt the *unconstrained* coordinates x (points get normalised)."""
    P = x.reshape(N, 3)
    nrm = np.linalg.norm(P, axis=1, keepdims=True)
    U = P / nrm
    try:
        h = ConvexHull(U)
    except Exception:
        return 1e9, np.zeros_like(x)
    g = np.zeros((N, 3))
    S = h.simplices
    A, B, C = U[S[:, 0]], U[S[:, 1]], U[S[:, 2]]
    cr = np.cross(B, C)
    sign = np.einsum('ij,ij->i', A, cr)
    flip = sign < 0
    if flip.any():                      # orient every facet outward
        S = S.copy()
        S[flip] = S[flip][:, [0, 2, 1]]
        A, B, C = U[S[:, 0]], U[S[:, 1]], U[S[:, 2]]
        cr = np.cross(B, C)
    V = np.einsum('ij,ij->i', A, cr).sum() / 6.0
    np.add.at(g, S[:, 0], cr / 6.0)
    np.add.at(g, S[:, 1], np.cross(C, A) / 6.0)
    np.add.at(g, S[:, 2], np.cross(A, B) / 6.0)
    dot = np.einsum('ij,ij->i', g, U)[:, None]
    gP = (g - dot * U) / nrm            # chain rule through U = P/|P|
    return -V, -gP.ravel()


def local(x0, N, maxiter=3000):
    r = minimize(neg_vol_and_grad, np.asarray(x0, float).ravel(), args=(N,), jac=True,
                 method='L-BFGS-B',
                 options={'maxiter': maxiter, 'maxfun': maxiter * 2, 'ftol': 1e-18, 'gtol': 1e-14})
    x = r.x.reshape(N, 3)
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    return hull_volume(x), x


def fibonacci(N, rng):
    """Fibonacci / golden-spiral sphere points with a random rotation."""
    i = np.arange(N) + 0.5
    phi = np.arccos(1 - 2 * i / N)
    th = np.pi * (1 + 5 ** 0.5) * i + rng.uniform(0, 2 * np.pi)
    P = np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]
    return random_rotate(P, rng)


def random_rotate(P, rng):
    Q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    if np.linalg.det(Q) < 0:
        Q[:, 0] *= -1
    return P @ Q


def coulomb_seed(N, rng, steps=120):
    """Cheap Thomson-like repulsion start: max-volume optima sit near well-spread configs."""
    P = rng.normal(size=(N, 3))
    P /= np.linalg.norm(P, axis=1, keepdims=True)
    for k in range(steps):
        D = P[:, None, :] - P[None, :, :]
        d2 = np.einsum('ijk,ijk->ij', D, D)
        np.fill_diagonal(d2, np.inf)
        F = (D / d2[:, :, None] ** 1.5).sum(axis=1)
        P = P + (0.05 / (1 + k / 40)) * F
        P /= np.linalg.norm(P, axis=1, keepdims=True)
    return P


def seed(N, rng, kind=None):
    kind = rng.integers(0, 3) if kind is None else kind
    if kind == 0:
        P = rng.normal(size=(N, 3))
        P /= np.linalg.norm(P, axis=1, keepdims=True)
        return P
    if kind == 1:
        return fibonacci(N, rng)
    return coulomb_seed(N, rng)


def basin_hop(N, seconds, seed0, x_init=None, v_init=-1.0, T=2e-5):
    """Basin hopping with mixed perturbation moves.  Returns (best_volume, best_points)."""
    import time
    rng = np.random.default_rng(seed0)
    t0 = time.time()
    if x_init is None:
        best, bx = local(seed(N, rng), N)
    else:
        best, bx = v_init, np.asarray(x_init, float)
        if best < 0:
            best, bx = local(bx, N)
    cur_v, cur_x = best, bx.copy()
    it = 0
    while time.time() - t0 < seconds:
        it += 1
        c = cur_x.copy()
        mode = rng.integers(0, 4)
        if mode == 0:                                   # global jiggle
            c += rng.normal(scale=rng.uniform(0.02, 0.35), size=c.shape)
        elif mode == 1:                                 # teleport a few points
            k = int(rng.integers(1, max(2, N // 6)))
            idx = rng.choice(N, size=k, replace=False)
            c[idx] = rng.normal(size=(k, 3))
        elif mode == 2:                                 # single-point teleport
            c[rng.integers(0, N)] = rng.normal(size=3)
        else:                                           # fresh restart
            c = seed(N, rng)
        c /= np.linalg.norm(c, axis=1, keepdims=True)
        v, xv = local(c, N)
        if v > cur_v or rng.random() < np.exp((v - cur_v) / T):
            cur_v, cur_x = v, xv
        if v > best:
            best, bx = v, xv
    return best, bx, it
