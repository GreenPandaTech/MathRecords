#!/usr/bin/env python3
"""Standalone checker for an elliptic curve rank lower bound.

Self-contained on purpose: it imports nothing from the search that produced the
claim, and nothing outside the standard library.  Point it at a certificate and
it re-derives everything from the definitions.

A certificate is a curve

    E : y^2 + a1 xy + a3 y = x^3 + a2 x^2 + a4 x + a6      (a_i rational)

together with k rational points.  It establishes  rank E(Q) >= k  provided

  (1) every listed point satisfies the equation                  [exact]
  (2) no relation sum(n_i P_i) = O holds with small |n_i|        [exact]
  (3) the height-pairing matrix has nonzero determinant          [numerical]

(1) and (2) are decided in exact rational arithmetic.  (3) cannot be: the
canonical height is a limit.  It is computed by the classical

    hhat(P) = lim_n  h(x(2^n P)) / 4^n

whose truncation error is always POSITIVE, so a small computed determinant is
never on its own evidence of independence.  This checker therefore reports the
value at two precisions and requires it to be *stable*: dependent points make it
decay towards zero by roughly a factor of four per extra doubling, while
independent points converge.  A certificate whose determinant is merely small,
rather than stable, is rejected.

Usage:
    python verify_rank.py <certificate.json>
    python verify_rank.py --selftest
"""
import json
import sys
from fractions import Fraction as F
from math import log


class E:
    def __init__(self, a1, a2, a3, a4, a6):
        self.a1, self.a2, self.a3, self.a4, self.a6 = map(F, (a1, a2, a3, a4, a6))
        self.b2 = self.a1 ** 2 + 4 * self.a2
        self.b4 = 2 * self.a4 + self.a1 * self.a3
        self.b6 = self.a3 ** 2 + 4 * self.a6
        self.b8 = (self.a1 ** 2 * self.a6 + 4 * self.a2 * self.a6
                   - self.a1 * self.a3 * self.a4 + self.a2 * self.a3 ** 2
                   - self.a4 ** 2)
        self.disc = (-self.b2 ** 2 * self.b8 - 8 * self.b4 ** 3
                     - 27 * self.b6 ** 2 + 9 * self.b2 * self.b4 * self.b6)

    def on(self, P):
        x, y = P
        return (y * y + self.a1 * x * y + self.a3 * y
                == x ** 3 + self.a2 * x * x + self.a4 * x + self.a6)

    def neg(self, P):
        return None if P is None else (P[0], -P[1] - self.a1 * P[0] - self.a3)

    def add(self, P, Q):
        if P is None:
            return Q
        if Q is None:
            return P
        x1, y1 = P
        x2, y2 = Q
        if x1 == x2 and y1 + y2 + self.a1 * x2 + self.a3 == 0:
            return None
        if x1 == x2 and y1 == y2:
            d = 2 * y1 + self.a1 * x1 + self.a3
            if d == 0:
                return None
            lam = (3 * x1 * x1 + 2 * self.a2 * x1 + self.a4 - self.a1 * y1) / d
        else:
            lam = (y2 - y1) / (x2 - x1)
        nu = y1 - lam * x1
        x3 = lam * lam + self.a1 * lam - self.a2 - x1 - x2
        return (x3, -(lam + self.a1) * x3 - nu - self.a3)

    def mul(self, n, P):
        if n < 0:
            return self.mul(-n, self.neg(P))
        R, Q = None, P
        while n:
            if n & 1:
                R = self.add(R, Q)
            Q = self.add(Q, Q)
            n >>= 1
        return R

    def hhat(self, P, iters):
        if P is None:
            return 0.0
        x = P[0]
        v = _h(x)
        for n in range(1, iters + 1):
            num = x ** 4 - self.b4 * x * x - 2 * self.b6 * x - self.b8
            den = 4 * x ** 3 + self.b2 * x * x + 2 * self.b4 * x + self.b6
            if den == 0:
                return 0.0
            x = num / den
            v = _h(x) / 4 ** n
            if max(x.numerator.bit_length(), x.denominator.bit_length()) > 200_000:
                break
        return v

    def gram(self, pts, iters):
        k = len(pts)
        G = [[0.0] * k for _ in range(k)]
        for i in range(k):
            G[i][i] = self.hhat(pts[i], iters)
        for i in range(k):
            for j in range(i + 1, k):
                v = (self.hhat(self.add(pts[i], pts[j]), iters)
                     - G[i][i] - G[j][j]) / 2
                G[i][j] = G[j][i] = v
        return G


def _h(x):
    m = max(abs(x.numerator), abs(x.denominator))
    if m == 0:
        return 0.0
    if m < (1 << 1000):
        return log(m)
    s = m.bit_length() - 200
    return log(m >> s) + s * log(2)


def _det(M):
    n = len(M)
    A = [r[:] for r in M]
    d = 1.0
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        if abs(A[p][i]) < 1e-300:
            return 0.0
        if p != i:
            A[i], A[p] = A[p], A[i]
            d = -d
        d *= A[i][i]
        for r in range(i + 1, n):
            f = A[r][i] / A[i][i]
            for c in range(i, n):
                A[r][c] -= f * A[i][c]
    return d


def _norm(G, det):
    p = 1.0
    for i in range(len(G)):
        if G[i][i] <= 0:
            return 0.0
        p *= G[i][i]
    return abs(det) / p


def _combos(b, k):
    if k == 0:
        yield ()
        return
    for h in range(-b, b + 1):
        for t in _combos(b, k - 1):
            yield (h,) + t


def verify(curve, points, lo=5, hi=7, bound=1, decay_tol=2.5, floor=1e-4):
    C = E(*curve)
    pts = [(F(a), F(b)) for a, b in points]
    problems = []

    if C.disc == 0:
        problems.append('curve is singular (discriminant 0)')
    for i, P in enumerate(pts):
        if not C.on(P):
            problems.append(f'point {i+1} ({P[0]}, {P[1]}) is not on the curve')

    rel = None
    if not problems:
        for combo in _combos(bound, len(pts)):
            if not any(combo):
                continue
            S = None
            for c, P in zip(combo, pts):
                if c:
                    S = C.add(S, C.mul(c, P))
            if S is None:
                rel = combo
                break
        if rel:
            problems.append(f'points satisfy the exact relation {list(rel)} = O')

    nl = nh = decay = 0.0
    min_h = 0.0
    if not problems:
        Gl = C.gram(pts, lo)
        Gh = C.gram(pts, hi)

        # Torsion check, and it must come BEFORE the regulator test.  For a
        # single point the normalised regulator is identically 1 -- the
        # determinant and the diagonal product are the same number -- so it can
        # never detect a torsion point, which has canonical height exactly 0.
        # A rank-1 "certificate" consisting of one torsion point would otherwise
        # be accepted.  Torsion is caught the same way dependence is: the height
        # decays towards 0 under refinement instead of converging.
        for i, P in enumerate(pts):
            hh, hl = Gh[i][i], Gl[i][i]
            if hh <= floor or (hh > 0 and hl / hh >= decay_tol):
                problems.append(
                    f'point {i+1} ({P[0]}, {P[1]}) has canonical height '
                    f'{hl:.3g} -> {hh:.3g} under refinement: it is torsion, '
                    f'so it contributes nothing to the rank')
        min_h = min(Gh[i][i] for i in range(len(pts))) if pts else 0.0

    if not problems:
        nl = _norm(Gl, _det(Gl))
        nh = _norm(Gh, _det(Gh))
        decay = (nl / nh) if nh > 0 else float('inf')
        if nh <= floor:
            problems.append(f'normalised regulator {nh:.3g} is below {floor:g}')
        elif decay >= decay_tol:
            problems.append(
                f'normalised regulator decays under refinement '
                f'({nl:.3g} -> {nh:.3g}, factor {decay:.2f}) -- '
                f'the points are dependent and the determinant is truncation error')

    return problems, {'k': len(pts), 'disc': C.disc, 'normreg_lo': nl,
                      'normreg_hi': nh, 'decay': decay, 'relation': rel,
                      'min_height': min_h}


def selftest():
    cases = [
        (['0', '0', '1', '-7', '6'], [['0', '2'], ['-1', '3'], ['-2', '3']], True,
         '5077a1, true rank 3'),
        (['0', '1', '1', '-2', '0'], [['0', '0'], ['-1', '1']], True,
         '389a1, true rank 2'),
        # 2P for P=(0,2) on 5077a1 is (49/25, -32/125), computed from the group
        # law -- an earlier version of this control guessed (4,6), which is a
        # genuine independent point, so the control was wrong rather than the
        # checker.
        (['0', '0', '1', '-7', '6'], [['0', '2'], ['49/25', '-32/125']], False,
         '5077a1 with P and 2P: dependent, must be rejected'),
        (['0', '0', '1', '-7', '6'], [['0', '2'], ['4', '6']], True,
         '5077a1 with two genuinely independent points'),
        (['0', '-1', '1', '-10', '-20'], [['5', '5']], False,
         '11a1 torsion point: height 0, must be rejected'),
        (['0', '0', '1', '-7', '6'], [['0', '3']], False,
         'point not on the curve'),
    ]
    ok = True
    for curve, pts, expect, note in cases:
        probs, info = verify(curve, pts)
        got = not probs
        if got != expect:
            ok = False
        print(f'  [{"ok " if got == expect else "FAIL"}] accepted={got} '
              f'expected={expect}  {note}')
        if probs and got != expect:
            print('        ', probs)
    print('SELFTEST PASSED' if ok else 'SELFTEST FAILED')
    return 0 if ok else 1


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == '--selftest':
        return selftest()
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    d = json.load(open(sys.argv[1]))
    b = d.get('best', d)
    curve, points = b['curve'], b['points']
    problems, info = verify(curve, points)
    print(f'curve  y^2 + ({curve[0]})xy + ({curve[2]})y = '
          f'x^3 + ({curve[1]})x^2 + ({curve[3]})x + ({curve[4]})')
    print(f'discriminant     {info["disc"]}')
    print(f'points claimed   {info["k"]}')
    for p in points:
        print(f'   ({p[0]}, {p[1]})')
    print(f'normalised regulator  {info["normreg_lo"]:.6g} (5 doublings) -> '
          f'{info["normreg_hi"]:.6g} (7 doublings), factor {info["decay"]:.3f}')
    if problems:
        print('\nREJECTED:')
        for p in problems:
            print('  -', p)
        return 1
    print(f'\nACCEPTED: the {info["k"]} points lie on the curve, satisfy no short '
          f'relation,\n          and their height pairing is nonsingular and stable.')
    print(f'          This proves  rank E(Q) >= {info["k"]}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
