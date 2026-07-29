"""Search for elliptic curves over Q of high rank, with verifiable certificates.

Method (Mestre's idea, in its simplest form).  Rather than pick a curve and hunt
for points on it, pick the points and solve for the curve.  A general Weierstrass
equation has five coefficients and the defining relation is linear in them, so
five prescribed rational points determine a curve through all five.  Those five
points are then, generically, independent -- giving rank >= 5 immediately -- and
any further points found on the curve push the bound higher.

What comes out is a certificate, not an assertion:

    the curve            (a1, a2, a3, a4, a6)
    k rational points    each verifiably on the curve
    the Gram matrix      of canonical heights, with nonzero determinant

Anyone can recheck all three without trusting this code, and a nonzero
determinant proves the points are independent, hence rank(E) >= k.

Honesty about scale.  The record is rank >= 29 (Elkies and Klagsbrun, 2024),
reached with specialist machinery and enormous search.  Nothing here is going to
approach that.  This produces genuine, checkable lower bounds for the curves it
finds, and reports exactly what it found.

Usage:  python ec_search.py [--workers 2] [--seconds 3600] [--target 8]
"""
import argparse
import json
import os
import random
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction as F
from math import isqrt

from ec_core import (Curve, curve_through, independent_subset,
                     normalised_regulator)

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


def is_square(n):
    if n < 0:
        return False
    r = isqrt(n)
    return r * r == n


def rational_sqrt(q):
    """Exact square root of a Fraction, or None."""
    a, b = q.numerator, q.denominator
    if a < 0:
        return None
    ra, rb = isqrt(a), isqrt(b)
    if ra * ra != a or rb * rb != b:
        return None
    return F(ra, rb)


def integral_model(E):
    """Scale to integral coefficients: (x,y) -> (u^2 x, u^3 y) sends a_i to u^i a_i.

    Taking u to be a common multiple of every denominator makes u^i a_i integral
    for all i >= 1.  Returns (E', u) so points can be pushed back and forth.
    """
    u = 1
    for a in (E.a1, E.a2, E.a3, E.a4, E.a6):
        d = a.denominator
        u = u * d // _gcd(u, d)
    E2 = Curve(E.a1 * u, E.a2 * u ** 2, E.a3 * u ** 3, E.a4 * u ** 4, E.a6 * u ** 6)
    return E2, u


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def points_on(E, xmax=60, qmax=6):
    """Rational points found by scanning x = a/b with small a and b.

    Searched on the curve as given, NOT on a rescaled integral model.  Making
    the model integral multiplies a6 by u^6, which pushes every genuine point
    far outside any reasonable window -- the first version of this searched the
    integral model and found essentially nothing beyond the points it had been
    handed.  The canonical height is invariant under isomorphism, so working in
    the small model costs nothing and is where the points actually live.
    """
    out = []
    seen = set()
    for b in range(1, qmax + 1):
        for a in range(-xmax * b, xmax * b + 1):
            x = F(a, b)
            if x in seen:
                continue
            seen.add(x)
            c = E.a1 * x + E.a3
            disc = c * c + 4 * (x ** 3 + E.a2 * x * x + E.a4 * x + E.a6)
            r = rational_sqrt(disc)
            if r is None:
                continue
            for s in (r, -r):
                y = (-c + s) / 2
                if E.contains((x, y)):
                    out.append((x, y))
    return out


def one_trial(args):
    """Build a curve through five random points, then push the rank as high as
    the extra points on it allow."""
    seed, coord, xmax, qmax, iters = args
    rng = random.Random(seed)
    pts = []
    seen = set()
    while len(pts) < 5:
        x = F(rng.randint(-coord, coord))
        y = F(rng.randint(-coord, coord))
        if x in seen:
            continue
        seen.add(x)
        pts.append((x, y))
    E = curve_through(pts)
    if E is None:
        return None
    try:
        if not all(E.contains(p) for p in pts):
            return None
        extra = points_on(E, xmax=xmax, qmax=qmax)
        cand = pts + [p for p in extra if p not in pts]
        kept, det, nrm = independent_subset(E, cand, iters=iters)
    except (ZeroDivisionError, ValueError, OverflowError):
        return None
    if not kept:
        return None
    return {'rank_lower_bound': len(kept),
            'curve': [str(E.a1), str(E.a2), str(E.a3), str(E.a4), str(E.a6)],
            'disc': str(E.disc),
            'points': [[str(p[0]), str(p[1])] for p in kept],
            'regulator_det': det, 'normalised_regulator': nrm,
            'seed': seed, 'points_examined': len(cand)}


def verify_best(rec, lo=5, hi=7, decay_tol=2.5, floor=1e-4, relation_bound=1):
    """Re-establish a candidate at higher precision before it is believed.

    A nonzero regulator is the rigorous independence criterion, but it is
    computed in floating point from a *truncated* limit, and truncation error is
    always positive.  So a small nonzero value is ambiguous, and a fixed
    threshold is the wrong test entirely.

    The right test is how the value behaves as precision increases:

        independent points  -> the normalised regulator converges to a positive
                               constant
        dependent points    -> the true value is 0 and the computed one decays
                               towards it, roughly by a factor of 4 per extra
                               doubling

    This was not hypothetical.  The search's rank-7 candidates showed
    0.00125 -> 0.00049 -> 0.000074 across iters 5, 6, 7 -- a clean decay to
    zero.  Under a fixed threshold at low precision every one of them would have
    been reported as a rank-7 curve.  They are dependent.

    So: re-select the independent subset at high precision, require the
    normalised regulator to be stable rather than merely nonzero, and finish
    with an exact search for a short relation using the group law and no
    floating point at all.
    """
    E = Curve(*[F(s) for s in rec['curve']])
    pts = [(F(a), F(b)) for a, b in rec['points']]
    if not all(E.contains(p) for p in pts):
        return {'verified': False, 'reason': 'a listed point is not on the curve'}

    # re-select at high precision; the low-precision greedy pass over-admits
    kept, det_hi, nrm_hi = independent_subset(E, pts, iters=hi, tol=floor)
    if not kept:
        return {'verified': False, 'rank_verified': 0,
                'reason': 'no independent subset survives at higher precision'}

    det_lo, G_lo = E.regulator(kept, iters=lo)
    nrm_lo = normalised_regulator(G_lo, det_lo)
    decay = (nrm_lo / nrm_hi) if nrm_hi > 0 else float('inf')
    stable = nrm_hi > floor and decay < decay_tol

    # exact short-relation search: no floating point anywhere in this part
    k = len(kept)
    bad = None
    for combo in _combos(range(-relation_bound, relation_bound + 1), k):
        if all(c == 0 for c in combo):
            continue
        S = None
        for c, P in zip(combo, kept):
            if c:
                S = E.add(S, E.mul(c, P))
        if S is None:
            bad = combo
            break

    return {'verified': bool(stable and bad is None),
            'rank_verified': len(kept) if (stable and bad is None) else 0,
            'points_verified': [[str(p[0]), str(p[1])] for p in kept],
            'normalised_regulator_lo': nrm_lo,
            'normalised_regulator_hi': nrm_hi,
            'decay': decay, 'stable': bool(stable),
            'relation_found': list(bad) if bad else None,
            'iters_lo': lo, 'iters_hi': hi, 'relation_bound': relation_bound}


def _combos(rng, k):
    if k == 0:
        yield ()
        return
    for head in rng:
        for tail in _combos(rng, k - 1):
            yield (head,) + tail


def main():
    global _LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--seconds', type=int, default=3600)
    ap.add_argument('--target', type=int, default=10)
    ap.add_argument('--coord', type=int, default=12)
    ap.add_argument('--xmax', type=int, default=60)
    ap.add_argument('--qmax', type=int, default=5)
    ap.add_argument('--iters', type=int, default=5)
    ap.add_argument('--tag', default='ec_search')
    a = ap.parse_args()

    os.makedirs(LOGDIR, exist_ok=True)
    _LOGF = open(os.path.join(LOGDIR, f'{a.tag}.log'), 'a', encoding='utf-8')
    log(f'rank search: workers={a.workers} budget={a.seconds}s target={a.target} '
        f'coord={a.coord} xmax={a.xmax} qmax={a.qmax} pid={os.getpid()}')
    log('record for context: rank >= 29 (Elkies-Klagsbrun 2024). '
        'This is not expected to approach it.')

    t0 = time.time()
    best = None
    hist = {}
    seed = 1
    tried = 0
    outp = os.path.join(HERE, f'{a.tag}_best.json')

    while time.time() - t0 < a.seconds:
        batch = [(seed + i, a.coord, a.xmax, a.qmax, a.iters)
                 for i in range(a.workers * 4)]
        seed += len(batch)
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for f in as_completed([ex.submit(one_trial, b) for b in batch]):
                try:
                    r = f.result()
                except Exception:
                    continue
                tried += 1
                if r is None:
                    continue
                k = r['rank_lower_bound']
                hist[k] = hist.get(k, 0) + 1
                if best is None or k > best['rank_lower_bound']:
                    v = verify_best(r)
                    r['verification'] = v
                    kv = v.get('rank_verified', 0)
                    if not v['verified'] or kv == 0:
                        log(f'  rejected rank>={k} candidate (seed {r["seed"]}): '
                            f'normreg_hi={v.get("normalised_regulator_hi", 0):.3g} '
                            f'relation={v.get("relation_found")}')
                        continue
                    # Report only what verification actually confirmed.  The
                    # search's own count is an optimistic low-precision figure
                    # and the high-precision re-selection routinely keeps fewer
                    # points; storing the larger number would put an unverified
                    # rank in the results file.
                    if kv < k:
                        log(f'  seed {r["seed"]}: search claimed rank>={k}, '
                            f'verification confirms {kv} -- recording {kv}')
                    r['rank_claimed_by_search'] = k
                    r['rank_lower_bound'] = kv
                    r['points'] = v['points_verified']
                    k = kv
                    if best is not None and k <= best['rank_lower_bound']:
                        continue
                    best = r
                    log(f'new best: rank >= {k}  normreg={r["normalised_regulator"]:.4g} '
                        f'-> verified at higher precision '
                        f'{v["normalised_regulator_hi"]:.4g}  seed={r["seed"]}')
                    log(f'  curve [a1,a2,a3,a4,a6] = {r["curve"]}')
                    json.dump(best, open(outp, 'w'), indent=1)
        if best and best['rank_lower_bound'] >= a.target:
            log(f'target rank {a.target} reached, stopping')
            break
        log(f'  {tried} curves examined, {(time.time()-t0)/60:.1f} min, '
            f'best so far {best["rank_lower_bound"] if best else 0}, '
            f'distribution {dict(sorted(hist.items()))}')

    log('')
    if best:
        log(f'BEST: rank >= {best["rank_lower_bound"]}  '
            f'normalised regulator {best["normalised_regulator"]:.6g}')
        log(f'  curve  {best["curve"]}')
        for p in best['points']:
            log(f'  point  ({p[0]}, {p[1]})')
        json.dump({'best': best, 'curves_examined': tried,
                   'rank_distribution': dict(sorted(hist.items())),
                   'seconds': time.time() - t0},
                  open(outp, 'w'), indent=1)
        log(f'wrote {outp}')
    else:
        log('no curve produced an independent set')


if __name__ == '__main__':
    main()
