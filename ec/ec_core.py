"""Elliptic curves over Q: exact arithmetic, canonical heights, rank lower bounds.

Why this exists.  The Birch and Swinnerton-Dyer conjecture is a Millennium
problem and is not going to be settled by computation.  But one object attached
to it *is* finite, checkable and publicly tracked: the rank of an elliptic curve
over Q.  A claim of the form "this curve has rank at least k" is backed by a
completely finite artifact -- the curve, k rational points on it, and the
determinant of their height-pairing matrix.  Anyone can recompute that.  That is
the honest, verifiable end of BSD, and it is what this module supports.

There is no Sage, PARI or gmpy2 on this machine, so everything here is written
from scratch on Python's Fraction and int.

Conventions.  Curves are general Weierstrass over Q

    E : y^2 + a1 x y + a3 y = x^3 + a2 x^2 + a4 x + a6

because the search constructs curves by forcing them through prescribed points,
and five prescribed points determine (a1,a2,a3,a4,a6) linearly.  Heights use the
x-only duplication formula, which is stated directly for this form, so no
transformation to short Weierstrass is needed.

The canonical height here is the limit

    hhat(P) = lim_n  h(x(2^n P)) / 4^n,       h(p/q) = log max(|p|,|q|)

which is twice the "Silverman normalisation" used by some tables.  Every
quantity we care about -- whether the regulator is nonzero, hence whether points
are independent -- is invariant under that overall scaling, so the convention is
harmless as long as it is applied consistently.  It is flagged here so nobody
compares a number from this file against a table without noticing.
"""
from fractions import Fraction as F
from math import log


class Curve:
    """y^2 + a1 xy + a3 y = x^3 + a2 x^2 + a4 x + a6 over Q."""

    __slots__ = ('a1', 'a2', 'a3', 'a4', 'a6', 'b2', 'b4', 'b6', 'b8', 'disc')

    def __init__(self, a1, a2, a3, a4, a6):
        self.a1, self.a2, self.a3, self.a4, self.a6 = (F(a1), F(a2), F(a3),
                                                       F(a4), F(a6))
        a1, a2, a3, a4, a6 = self.a1, self.a2, self.a3, self.a4, self.a6
        self.b2 = a1 * a1 + 4 * a2
        self.b4 = 2 * a4 + a1 * a3
        self.b6 = a3 * a3 + 4 * a6
        self.b8 = (a1 * a1 * a6 + 4 * a2 * a6 - a1 * a3 * a4
                   + a2 * a3 * a3 - a4 * a4)
        self.disc = (-self.b2 ** 2 * self.b8 - 8 * self.b4 ** 3
                     - 27 * self.b6 ** 2 + 9 * self.b2 * self.b4 * self.b6)

    def is_singular(self):
        return self.disc == 0

    def contains(self, P):
        if P is None:
            return True
        x, y = P
        return (y * y + self.a1 * x * y + self.a3 * y
                == x ** 3 + self.a2 * x * x + self.a4 * x + self.a6)

    # ---- group law (Silverman, AEC III.2.3); None is the point at infinity ----

    def neg(self, P):
        if P is None:
            return None
        x, y = P
        return (x, -y - self.a1 * x - self.a3)

    def add(self, P, Q):
        if P is None:
            return Q
        if Q is None:
            return P
        x1, y1 = P
        x2, y2 = Q
        if x1 == x2 and (y1 + y2 + self.a1 * x2 + self.a3) == 0:
            return None
        if x1 == x2 and y1 == y2:
            den = 2 * y1 + self.a1 * x1 + self.a3
            if den == 0:
                return None
            lam = (3 * x1 * x1 + 2 * self.a2 * x1 + self.a4 - self.a1 * y1) / den
        else:
            lam = (y2 - y1) / (x2 - x1)
        nu = y1 - lam * x1
        x3 = lam * lam + self.a1 * lam - self.a2 - x1 - x2
        y3 = -(lam + self.a1) * x3 - nu - self.a3
        return (x3, y3)

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

    # ---- heights ----

    def x_double(self, x):
        """x(2P) from x(P): (x^4 - b4 x^2 - 2 b6 x - b8) / (4x^3 + b2 x^2 + 2 b4 x + b6)."""
        num = x ** 4 - self.b4 * x * x - 2 * self.b6 * x - self.b8
        den = 4 * x ** 3 + self.b2 * x * x + 2 * self.b4 * x + self.b6
        if den == 0:
            return None                      # 2P is the point at infinity
        return num / den

    def canonical_height(self, P, iters=7, max_bits=200_000):
        """hhat(P) = lim h(x(2^n P))/4^n, computed exactly then divided.

        Coordinates roughly square in size at each doubling, so this stops once
        the numbers get unwieldy; the tail dropped is O(4^-n).  Size is measured
        with bit_length, not decimal digits -- str() on a huge int raises under
        Python's integer-to-string digit limit, which is a silly way to lose a
        computation.
        """
        if P is None:
            return 0.0
        x = P[0]
        best = _h(x)
        for n in range(1, iters + 1):
            x = self.x_double(x)
            if x is None:
                return 0.0                   # 2^n P hit infinity: P is torsion
            best = _h(x) / (4 ** n)
            if max(x.numerator.bit_length(), x.denominator.bit_length()) > max_bits:
                break
        return best

    def height_pairing(self, P, Q, iters=7):
        """<P,Q> = (hhat(P+Q) - hhat(P) - hhat(Q)) / 2."""
        return (self.canonical_height(self.add(P, Q), iters)
                - self.canonical_height(P, iters)
                - self.canonical_height(Q, iters)) / 2

    def regulator(self, pts, iters=7):
        """Gram determinant of the height pairing.  Nonzero => independent."""
        k = len(pts)
        G = [[0.0] * k for _ in range(k)]
        for i in range(k):
            G[i][i] = self.canonical_height(pts[i], iters)
        for i in range(k):
            for j in range(i + 1, k):
                v = self.height_pairing(pts[i], pts[j], iters)
                G[i][j] = G[j][i] = v
        return _det(G), G


def _h(x):
    """Naive height of a rational: log max(|num|, |den|)."""
    a, b = abs(x.numerator), abs(x.denominator)
    m = a if a > b else b
    if m == 0:
        return 0.0
    return _log_big(m)


def _log_big(m):
    """log of a possibly enormous int, without overflowing float."""
    if m < (1 << 1000):
        return log(m)
    nbits = m.bit_length()
    shift = nbits - 200
    return log(m >> shift) + shift * log(2)


def _det(M):
    """Determinant by fraction-free-ish Gaussian elimination in float."""
    n = len(M)
    A = [row[:] for row in M]
    d = 1.0
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        if abs(A[p][i]) < 1e-300:
            return 0.0
        if p != i:
            A[i], A[p] = A[p], A[i]
            d = -d
        d *= A[i][i]
        inv = 1.0 / A[i][i]
        for r in range(i + 1, n):
            f = A[r][i] * inv
            if f:
                for c in range(i, n):
                    A[r][c] -= f * A[i][c]
    return d


def solve_exact(rows, rhs):
    """Exact Gaussian elimination over Q.  Returns None if singular."""
    n = len(rows)
    A = [list(map(F, r)) + [F(v)] for r, v in zip(rows, rhs)]
    for i in range(n):
        p = next((r for r in range(i, n) if A[r][i] != 0), None)
        if p is None:
            return None
        A[i], A[p] = A[p], A[i]
        piv = A[i][i]
        A[i] = [v / piv for v in A[i]]
        for r in range(n):
            if r != i and A[r][i] != 0:
                f = A[r][i]
                A[r] = [v - f * w for v, w in zip(A[r], A[i])]
    return [A[i][n] for i in range(n)]


def curve_through(points):
    """The general Weierstrass curve through five prescribed rational points.

    y^2 + a1 xy + a3 y = x^3 + a2 x^2 + a4 x + a6  is linear in the five
    coefficients, so five points determine it:

        a1(x y) - a2(x^2) + a3(y) - a4(x) - a6 = x^3 - y^2

    This is the engine of the search: instead of picking a curve and hunting for
    points on it, pick the points and solve for the curve that contains them.
    """
    rows, rhs = [], []
    for x, y in points:
        x, y = F(x), F(y)
        rows.append([x * y, -x * x, y, -x, F(-1)])
        rhs.append(x ** 3 - y * y)
    sol = solve_exact(rows, rhs)
    if sol is None:
        return None
    E = Curve(*sol)
    if E.is_singular():
        return None
    return E


def normalised_regulator(G, det):
    """det(G) divided by the product of the diagonal.

    Hadamard's inequality makes this at most 1, and it is 0 exactly when the
    points are dependent.  Unlike the raw determinant it does not change when
    the height normalisation changes or when the points happen to be tall, so a
    single fixed threshold is meaningful across every curve in a search.
    """
    prod = 1.0
    for i in range(len(G)):
        if G[i][i] <= 0:
            return 0.0
        prod *= G[i][i]
    return abs(det) / prod if prod > 0 else 0.0


def independent_subset(E, pts, iters=6, tol=1e-4, min_height=1e-3):
    """Greedily keep points that raise the rank of the height-pairing matrix.

    Returns (kept, det, normalised).  A normalised regulator bounded away from
    zero certifies the kept points are independent in E(Q) (x) R, hence
    rank(E) >= len(kept).

    Torsion points are dropped up front: their canonical height is 0, so they
    would contribute a zero row and can only ever destroy the determinant.  The
    limit converges to 0 from above rather than reaching it, hence a threshold
    rather than an equality test.
    """
    kept, det, nrm = [], 0.0, 0.0
    for P in pts:
        if P is None:
            continue
        if E.canonical_height(P, iters) < min_height:
            continue                          # torsion (or indistinguishable)
        trial = kept + [P]
        d, G = E.regulator(trial, iters)
        nd = normalised_regulator(G, d)
        if nd > tol:
            kept, det, nrm = trial, d, nd
    return kept, det, nrm
