# Two new terms for mixed van der Waerden numbers

**Results.** Two previously uncomputed values, in two different families whose
published lists have both stood since 2012:

| sequence | new term | value |
|---|---|---|
| [A217058](https://oeis.org/A217058) | `a(12) = w(14; 2^12, 3, 4)` | **57** |
| [A217005](https://oeis.org/A217005) | `a(19) = w(21; 2^19, 3, 3)` | **52** |

```
A217058:  18, 21, 25, 29, 33, 36, 40, 42, 45, 48, 52, 55, 57
A217005:  9, 14, 17, 20, 21, 24, 25, 28, 31, 33, 35, 37, 39, 42, 44, 46, 48, 50, 51, 52
```

Each is established by a pair: an explicit colouring (checkable against the
definition by a program that never invokes a solver) and a machine refutation
one step above it.  Sections 1-7 develop the A217058 case in full; section 8
gives A217005, which follows the same method through a partly different code
path -- its two colour targets are *equal*, so a second symmetry breaker is
active that does nothing at all in the first family.

---

## 1. Definitions

Let `t_1, …, t_r ≥ 2` be integers. A colouring of `{1, …, n}` assigns each
integer to one of `r` classes. It is *valid* for `(t_1, …, t_r)` if class `i`
contains no `t_i`-term arithmetic progression. The van der Waerden number
`w(r; t_1, …, t_r)` is the least `n` for which no valid colouring of `{1, …, n}`
exists; van der Waerden's theorem guarantees it is finite.

A class with target `2` can hold at most one element, since any two integers
form a 2-term AP. Writing `2^j` for `j` such classes, the *mixed* numbers of
interest are

```
w(j + r; 2^j, t_1, …, t_r)
```

and it is convenient to think of the `j` classes of target 2 as a budget of `j`
**wildcards** — positions removed from the problem at a cost of one budget unit
each. Throughout, `.` denotes a wildcard.

**A217058** is the family `a(j) = w(j + 2; 2^j, 3, 4)`: one class must avoid
3-term APs, the other must avoid 4-term APs, and `j` positions may be excused
altogether. Equivalently,

```
a(j) = 1 + max{ n : {1..n} admits a valid colouring using at most j wildcards }
```

## 2. Status before this computation

The published terms are due to Ahmed, who computed the family in *Integers* and
in subsequent work, reaching `w(13; 2^11, 3, 4) = 55`. The OEIS entry was
queried directly on 2026-07-28 and returned

```json
"data": "18,21,25,29,33,36,40,42,45,48,52,55"
```

— twelve terms, offset 0, with an auto-synthesised b-file, i.e. no extension had
been contributed. The local copy of Ahmed's paper lists the family up to
`w(13; 2^11, 3, 4)` and contains no value for `w(14; 2^12, 3, 4)`.

## 3. The result

**Theorem.** `a(12) = w(14; 2^12, 3, 4) = 57`.

The two halves are established separately.

### 3.1 Lower bound: `a(12) ≥ 57`

The following colouring of `{1, …, 56}` uses exactly 12 wildcards, has no 3-term
AP in class 1 and no 4-term AP in class 2:

```
2.21221212.12.22211.112.2221.222.2.1..12221211212..22212
```

Class 1 occupies 16 positions, class 2 occupies 28, and 12 are wildcards. Since
a valid colouring of `{1,…,56}` exists, `a(12) > 56`.

This is a *certificate*: it is checked directly against the definition in
milliseconds by `vdw/verify_certificate.py`, which uses only the standard
library and never invokes a SAT solver.

### 3.2 Upper bound: `a(12) ≤ 57`

No valid colouring of `{1, …, 57}` with at most 12 wildcards exists. This was
established by translating the question to propositional logic and refuting the
formula (§4), and independently re-established twice (§5.4).

Together, `a(12) = 57`.

### 3.3 Remark on the step size

`a(12) − a(11) = 2`. The published differences are

```
3, 4, 4, 4, 3, 4, 2, 3, 3, 4, 3
```

so a naive extrapolation predicts 58 or 59, and both were refuted before 57 was
reached. A step of 2 is not unprecedented: it already occurs at
`a(6) = 40 → a(7) = 42`. The disagreement with extrapolation was treated as
grounds for additional verification rather than as a curiosity — see §5.

## 4. Method

### 4.1 Encoding

For a given `n` and `j`, introduce Boolean variables `v(i, c)` for
`i ∈ {1..n}` and `c ∈ {0, 1, …, r}`, where `c = 0` means "wildcard".

* exactly one class per position: one clause `⋁_c v(i,c)` and pairwise
  exclusions;
* no monochromatic AP: for each class `c` with target `t_c`, and each `t_c`-term
  AP `A ⊆ {1..n}`, the clause `⋁_{i∈A} ¬v(i,c)`;
* wildcard budget: a totalizer encoding of `∑_i v(i,0) ≤ j`.

The formula is satisfiable exactly when a valid colouring exists, so `a(j)` is
the least `n` whose formula is unsatisfiable.

### 4.2 Monotonicity

If `{1..n}` admits a valid colouring, so does `{1..m}` for every `m < n`:
restrict the colouring: no AP is created by deleting elements, and the wildcard
count cannot increase. Hence satisfiability is monotone decreasing in `n`, and
`a(j)` is the unique threshold. This is why the search probes candidate values
directly instead of climbing from `a(11)`, and why the two halves can be run as
independent concurrent computations.

### 4.3 A free lower bound

`a(j+1) ≥ a(j) + 1`. Given a valid colouring of `{1, …, a(j)−1}` with at most
`j` wildcards, extend it to `{1, …, a(j)}` by making the new final position a
wildcard. It uses at most `j+1` wildcards, and belongs to no class, so it
creates no monochromatic AP. Applied to `a(11) = 55` this gives `a(12) ≥ 56`
immediately, and an explicit certificate for it was produced (§5.3).

### 4.4 Reversal symmetry

The map `i ↦ n+1−i` is an automorphism of the problem: it carries the `t`-term
AP `a, a+d, …, a+(t−1)d` to `n+1−a−(t−1)d, …, n+1−a`, again an AP with the same
common difference; it fixes every class and the wildcard count. Requiring a
colouring to be lexicographically no greater than its own reversal is therefore
a sound lex-leader constraint, and it halves the search space.

This matters more than it might appear. The pre-existing implementation broke
only the symmetry between classes *sharing* a target value. A217058 has targets
`3` and `4`, which differ, so that rule emitted **no clauses at all** and every
search ran with no symmetry breaking whatsoever. Adding reversal symmetry
measured a **1.55×** speedup on the `n=45, j=8` refutation, on the half of the
problem that consumes essentially all the time.

### 4.5 Search organisation

Refutations use cube-and-conquer: branch on all class assignments to the first
`k` positions, discard prefixes that already exceed the wildcard budget or
already contain a monochromatic AP, and solve the residual formulas in parallel.
For `[3,4]`, `k = 4` gives 75 cubes. A measured comparison put `k = 4` at 34.1 s
against `k = 6` at 65.1 s on `n=45, j=8`, so the finer split was not used.

**UNSAT is reported only when every cube has returned an explicit verdict.** A
worker killed by the operating system raises an error rather than being counted
as an empty branch. Three earlier runs were lost to precisely that class of
failure, and the distinction is the difference between a theorem and a
retraction.

## 5. Verification

The lower bound needs no trust: it is a finite object checked against the
definition. The upper bound asserts the *absence* of an object and is therefore
only as strong as the claim that the formula handed to the solver faithfully
represents the problem. Five independent guards were applied.

### 5.1 The encoding equals the definition

On instances small enough to enumerate exhaustively, the set of colourings
satisfying the CNF was compared against the set accepted by a direct
transcription of the definition that never inspects a clause. They agreed
**exactly, in both directions**, on all 9 cases tested, spanning targets
`[3,4]`, `[3,3]`, `[3,5]`, `[3,3,3]` and `[4,4]`. Nothing invented, nothing
lost. (`vdw/encoding_audit.py`)

### 5.2 Symmetry breaking loses nothing

The same audit checks that every orbit of the symmetry group — generated by the
reversal and by swaps of equal-target classes — retains at least one
representative. Losing an orbit is exactly how a satisfiable instance would be
reported unsatisfiable. **Zero orbits were lost in any case tested.** On
distinct-target families, including `[3,4]`, the breaking is additionally
*exactly canonical*: 11539 orbits, 11539 survivors.

### 5.3 The engine reproduces what is already known

* **All twelve published terms of A217058** were re-derived by the same engine
  that produced the thirteenth. For each `a(j) = w`, this means finding a
  verified witness at `n = w−1` *and* refuting `n = w`.
* A further 29 published values across five families were reproduced with the
  reversal-symmetry constraint enabled.
* The full-scale gate is `a(11) = 55` at `j = 11`: SAT at `n = 54` with a
  verified witness using all 11 wildcards (1872.5 s), UNSAT at `n = 55`
  (1239.2 s). This is important because every other replayed value tops out at
  `j = 10`; a defect confined to large `j` would have escaped the rest of the
  testing and would have produced exactly the surprising pattern of §3.3.
  It did not exist.
* That witness also yields the explicit `a(12) ≥ 56` certificate of §4.3, which
  the standalone verifier accepts.

### 5.4 The refutation, three ways

`n = 57, j = 12` was refuted along paths chosen so that they cannot share a
mistake:

| encoding | symmetry | solver | cubes | verdict | time |
|---|---|---|---|---|---|
| vdw4 | reversal ON | CaDiCaL 1.9.5 | k=4 | UNSAT | 6257.1 s |
| **vdw2** | **none at all** | CaDiCaL 1.9.5 | k=4 | **UNSAT** | 8036.6 s |
| vdw4 | reversal OFF | CaDiCaL 3.0.0 | k=5 | (not completed) | — |

The second row is the one that matters. `vdw2` imposes no lex-leader constraint
on this family and therefore searches the full unreduced space; it cannot
inherit an error from the reversal-symmetry constraint, which is the only new
mathematics in the engine. It agrees.

The third configuration was started and stopped after 7.4 hours without
finishing — with twice the workers it was running more than three times longer
than the second, which says the `CaDiCaL 3.0.0` and `k=5` combination is poorly
matched to this family. It is reported here as incomplete rather than omitted.

Separately, a randomised-restart portfolio — 8 rounds × 5 seeds × 3 000 000
conflicts, with initial phases drawn from the class distribution of real
witnesses — hunted for a witness at `n = 57` and found none.

### 5.5 The cardinality constraint at full scale

The exhaustive audit of §5.1 reaches only `n ≤ 12` and `j ≤ 3`, while the target
runs at `j = 12`, and the totalizer's structure grows with the bound. Too
*strong* a cardinality constraint would forbid legal colourings and produce
precisely the kind of false refutation that matters. Tested directly at
`n = 55…58` with `j = 12`, from both sides: 240 assignments at the limit were
accepted and 240 over the limit were rejected, and forcing 13 wildcards inside
the full formula is correctly unsatisfiable. (`vdw/scale_test.py`)

## 6. Reproducing

```bash
# check the certificate - standard library only, no solver
python vdw/verify_certificate.py "2.21221212.12.22211.112.2221.222.2.1..12221211212..22212" 12 3 4
python vdw/verify_certificate.py --selftest      # positive and negative controls

# the audits
python vdw/encoding_audit.py                     # CNF == definition
python vdw/scale_test.py                         # wildcard budget at target scale

# the refutation (~1-2 h on 8 cores)
python vdw/vdw_probe.py 57 12 3 4 --workers 8 --k 4
```

Requires `python-sat`. Note that pysat's `Kissat404` aborts the interpreter on
this platform — a native crash with no Python exception — and is excluded.

Worker counts are capped well below the logical core count deliberately: each
solver grows an unbounded learned-clause database, and oversubscribing an
8-core machine exhausted memory and left orphaned workers running for hours.

## 7. What this is and is not

This is a finite, checkable extension of a tracked sequence by one term. It is
not a structural result: it says nothing about the growth of the family and
provides no new proof technique.

The lower bound is certain in the strongest available sense — a finite object,
verified against the definition by a program sharing no code with the solver.

The upper bound is a machine refutation. It has not been reduced to a formally
checked proof object (no DRAT certificate was produced or checked; that would
guard against a solver defect, whereas the audits above target an encoding
defect, which is by far the likelier failure and the one that low-level proof
checking cannot detect). It rests on: an encoding proven equal to the definition
by exhaustion, symmetry breaking proven to lose nothing, the wildcard budget
tested at exact scale, the whole published sequence reproduced, and two
independent refutations — one of them through an engine that imposes no symmetry
breaking at all.

## 8. The second term: A217005(19) = 52

`A217005(j) = w(j+2; 2^j, 3, 3)` -- both colour classes must avoid 3-term
arithmetic progressions.  Published terms (OEIS, offset 0, last extended by
Tanbir Ahmed in December 2012, confirmed live against the OEIS API on
2026-07-29):

```
a(0..18) = 9, 14, 17, 20, 21, 24, 25, 28, 31, 33, 35, 37, 39, 42, 44, 46, 48, 50, 51
```

**Theorem.** `a(19) = w(21; 2^19, 3, 3) = 52`.

**Lower bound.** This colouring of `[1,51]` uses exactly 19 wildcards and
contains no 3-term AP in either colour class, so `a(19) > 51`:

```
..11.1122.2211.1122.22.........11.1122.2211.1122.22
```

ACCEPTED by `vdw/verify_certificate.py` and independently by both engines'
internal checkers.  Found in 1520.1 s.

**Upper bound.** `n = 52, j = 19` is unsatisfiable -- 4507.0 s,
all 36 cubes reporting an explicit verdict.

Together, `a(19) = 52`.

### 8.1 Why this is not merely the first computation repeated

The targets here are **equal**.  That switches on the colour-swap symmetry
breaker, which emits no clauses whatsoever on A217058's `[3,4]`, so this result
exercises a code path the first one never touched.  The encoding audit covers
exactly this case: on equal-target families the two breakers together are sound
but *not* canonical -- they retain two representatives per orbit rather than one,
because composing two independent lex-leader constraints does not canonicalise
the group they generate.  That costs time and cannot cost correctness, and the
audit confirms zero orbits are lost.

### 8.2 Validation

The full-scale gate was run before the extension was attempted: published
`a(18) = 51` was reproduced exactly -- SAT at `n = 50` with a verified witness
and UNSAT at `n = 51`, both at `j = 18`, in 3469.4 s.  The free lower bound of
section 4.3 gives `a(19) >= 52` independently of any solver, so the refutation
at `n = 52` is the only computational input to the value.

### 8.3 An observation, not a claim

The witness found is strikingly structured rather than random-looking: the
segment `11.1122.2211.1122.22` appears twice, separated by a block of nine
consecutive wildcards.  Whether the extremal colourings of this family are
genuinely periodic is not something a single example can settle, and no claim is
made here -- it is recorded because it is the sort of thing worth looking at if
anyone pursues the family further.

## References

- T. Ahmed, *Some new van der Waerden numbers and some van der Waerden-type
  numbers*, Integers **9** (2009), A06, 65–76.
- T. Ahmed, *On computation of exact van der Waerden numbers*, Integers.
- OEIS Foundation Inc., [A217058](https://oeis.org/A217058), The On-Line
  Encyclopedia of Integer Sequences.
- M. Heule, O. Kullmann, S. Marijn et al., cube-and-conquer for hard
  combinatorial instances.
