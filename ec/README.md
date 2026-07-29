# Elliptic curve ranks — the finite, checkable end of BSD

The Birch and Swinnerton-Dyer conjecture is a Millennium Prize problem and is
not going to be settled by computation. But one object attached to it *is*
finite and checkable, and its records are publicly tracked: the rank of an
elliptic curve over **Q**.

A claim of the form *"this curve has rank at least k"* is backed entirely by a
finite artifact — the curve, `k` rational points on it, and the determinant of
their height-pairing matrix. Anyone can recompute all three. That is what this
directory produces.

## Result

**`rank E(Q) ≥ 7`** for

```
E : y² + (80/7)·xy + (−1182/13)·y = x³ + (−175/13)·x² + (1667/13)·x + (−5585/13)
```

witnessed by

```
(5, 0)   (0, 5)   (11, 14)   (9, 14)   (7, −8)   (−29, 280)   (15, 130/7)
```

Normalised regulator 0.2043, stable across 5 and 7 doublings (factor 0.999), no
short relation. Verify it with:

```bash
python verify_rank.py ec_search_best.json
python verify_rank.py --selftest      # controls, including negative ones
```

`verify_rank.py` imports nothing from the search and nothing outside the
standard library.

## Honest placement of this result

The record is **rank ≥ 29** (Elkies and Klagsbrun, 2024), reached with
specialist machinery and enormous search. Rank ≥ 7 from a few hours of random
construction is nowhere near it, and was never going to be. What it is: a
genuine, independently verifiable lower bound, produced by machinery that
refuses to over-claim.

## Method

Mestre's idea in its simplest form: rather than pick a curve and hunt for points
on it, **pick the points and solve for the curve**. The general Weierstrass
equation has five coefficients and is linear in them, so five prescribed
rational points determine a curve through all five. Those five are generically
independent — rank ≥ 5 immediately — and any further points found on the curve
push the bound up.

## Why the numerical part is the dangerous part

Point membership and the relation search are exact. The height pairing is not,
and cannot be: the canonical height is a limit,

```
ĥ(P) = limₙ h(x(2ⁿP)) / 4ⁿ
```

computed by truncating. **Truncation error here is always positive**, so a small
nonzero determinant is not evidence of independence — it is what dependent
points look like at low precision.

This was not hypothetical. The first version of the search reported rank-7
curves whose normalised regulator read:

| doublings | 5 | 6 | 7 |
|---|---|---|---|
| normalised regulator | 0.00125 | 0.00049 | 0.000074 |

A clean decay toward zero — those points are **dependent**. Under any fixed
threshold at low precision, every one of them would have been published as a
rank-7 curve.

Independence is therefore judged by **stability**, not size: the value must
converge rather than decay. Measured decay is ≈1.00 for genuinely independent
points and ≈17 for the spurious ones. It is backed by an exact search for a
short relation `Σ nᵢPᵢ = O` using the group law and no floating point at all —
which has caught concrete dependencies such as `P₅ = P₁ + P₂`.

## Three defects found, all of the over-claiming kind

1. **Fixed threshold accepted noise** — replaced by the stability test above.
2. **The results file recorded the search's rank, not the verified one.** The
   high-precision re-selection routinely keeps fewer points than the fast greedy
   pass; every rank-8 claim in this run downgraded to a verified 7. The verified
   count is now authoritative, with the search's claim retained beside it.
3. **The standalone checker could not detect torsion.** For a *single* point the
   normalised regulator is identically 1 — determinant and diagonal product are
   the same number — so a torsion point, of canonical height 0, would have been
   accepted as a rank-1 certificate. Now rejected explicitly, before the
   regulator test.

## Measured negatives, recorded so they are not repeated

* **Widening the point scan does not raise rank.** `xmax` 80→250 and `qmax` 6→10
  moved the average candidate count from 10.2 to 10.3 and left the rank
  distribution unchanged. Curves through five random points generically have
  rank exactly 5 and carry few further small points. The lever is volume of
  curves; going materially higher needs a *constructed* family in the style of
  Mestre's polynomial identities, which is a separate project, not a parameter
  change.
* **No Sage, PARI, gmpy2 or flint on this machine.** Everything is written from
  scratch on `Fraction` and `int`.

## Files

```
ec_core.py      curves over Q: exact group law, canonical heights, regulator
ec_search.py    the search, with high-precision verification before acceptance
verify_rank.py  standalone checker - no project imports, standard library only
```

Validated against known ranks: 37a1 (1), 389a1 (2), 5077a1 (3), with negative
controls for dependent sets, torsion, and points not on the curve.
