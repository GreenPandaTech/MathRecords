# OEIS submission pack

Generated from the evidence files, not typed. Every certificate, timing and
DATA line below was read out of the JSON the computation wrote.

**4 term(s) ready to submit.**

## Do this first, once

1. Register at https://oeis.org/ — approval is manual and takes a day or two.
   This is the only step with a waiting period, so start it before anything else.
2. Run `python verify_all.py` here. It must exit 0. If it does not, a claim has
   drifted from its evidence and nothing should be submitted until it passes.

## Order to submit

**A217058 first, and alone.** It is the only term whose refutation was
established three separate ways, so it is the safest place to find out what the
editors ask for. Wait for one round-trip before sending the others — you will
learn more from one reply than from any amount of preparation, and if an editor
questions the strongest result you want that on one submission, not four.

## Never

* Submit a term whose cross-check does not say AGREES.
* Retype a certificate. Copy it. A single wrong character is a retraction.
* Claim a term whose family gate did not reproduce the published value.

---

## A217058 — a(12) = 57

Page: https://oeis.org/A217058  ·  click **edit**

Cross-check: refuted three separate times, including through an engine that imposes no symmetry-breaking constraint at all and a second CDCL solver.

### 1. DATA
```
18,21,25,29,33,36,40,42,45,48,52,55,57
```

### 2. b-file
Upload `b217058.txt` (13 rows, 0 to 12).

### 3. EXTENSIONS
```
a(12) from Leo Zhang, Jul 30 2026
```

### 4. COMMENT — paste verbatim
```
a(12) = w(12+2; 2^12, 3, 4) = 57.

Lower bound. The following colouring of [1,56] uses 12 wildcards (limit 12) and has no 3-term AP in colour 1 and no 4-term AP in colour 2, so a(12) > 56:

2.21221212.12.22211.112.2221.222.2.1..12221211212..22212

('.' denotes one of the j colour classes with target 2, each holding at most one element.)

This is a certificate rather than an assertion: it is checked directly against the definition, in milliseconds, by a program that uses only the Python standard library and never invokes a SAT solver, so verifying it requires trusting none of the search code.

Upper bound. No valid colouring of [1,57] with at most 12 wildcards exists. The corresponding SAT instance is unsatisfiable (6257 s, all 75 cubes).

Because "no colouring exists" asserts an absence, it is only as strong as the claim that the formula faithfully encodes the problem. Guards applied: the CNF was proved equal to a direct transcription of the definition by exhaustive enumeration on small instances, in both directions; the symmetry-breaking constraint was proved to retain at least one representative of every orbit, since losing one is exactly how a satisfiable instance would be misreported as unsatisfiable; the wildcard cardinality constraint was tested at full scale from both sides; and published values of this family were re-derived by the same engine before any new term was claimed.

The parallel search also reports unsatisfiability only when every cube has returned an explicit verdict. A worker terminated by the operating system raises an error rather than being counted as an empty branch; without that distinction a killed worker is indistinguishable from a proof.

The refutation was re-established three separate times, including through an engine that imposes no symmetry-breaking constraint at all and a second CDCL solver.

Note on the lower bound: the free append-wildcard construction only gives a(12) >= 56, so the colouring above was found by search (3926 s) and is an independent object rather than a relabelling of the previous term.
```

### 5. Verify the lower bound yourself
```
python vdw/verify_certificate.py "2.21221212.12.22211.112.2221.222.2.1..12221211212..22212" 12 3 4
```

## A217005 — a(19) = 52

Page: https://oeis.org/A217005  ·  click **edit**

Cross-check: **AGREES** — the refutation was re-derived through `vdw2`, which carries no symmetry-breaking constraint, so it cannot inherit an error from the one piece of new mathematics in the main engine.

### 1. DATA
```
9,14,17,20,21,24,25,28,31,33,35,37,39,42,44,46,48,50,51,52
```

### 2. b-file
Upload `b217005.txt` (20 rows, 0 to 19).

### 3. EXTENSIONS
```
a(19) from Leo Zhang, Jul 30 2026
```

### 4. COMMENT — paste verbatim
```
a(19) = w(19+2; 2^19, 3, 3) = 52.

Lower bound. The following colouring of [1,51] uses 19 wildcards (limit 19) and has no 3-term AP in colour 1 and no 3-term AP in colour 2, so a(19) > 51:

..11.1122.2211.1122.22.........11.1122.2211.1122.22

('.' denotes one of the j colour classes with target 2, each holding at most one element.)

This is a certificate rather than an assertion: it is checked directly against the definition, in milliseconds, by a program that uses only the Python standard library and never invokes a SAT solver, so verifying it requires trusting none of the search code.

Upper bound. No valid colouring of [1,52] with at most 19 wildcards exists. The corresponding SAT instance is unsatisfiable (4507 s, all 36 cubes).

Because "no colouring exists" asserts an absence, it is only as strong as the claim that the formula faithfully encodes the problem. Guards applied: the CNF was proved equal to a direct transcription of the definition by exhaustive enumeration on small instances, in both directions; the symmetry-breaking constraint was proved to retain at least one representative of every orbit, since losing one is exactly how a satisfiable instance would be misreported as unsatisfiable; the wildcard cardinality constraint was tested at full scale from both sides; and published values of this family were re-derived by the same engine before any new term was claimed.

The parallel search also reports unsatisfiability only when every cube has returned an explicit verdict. A worker terminated by the operating system raises an error rather than being counted as an empty branch; without that distinction a killed worker is indistinguishable from a proof.

The refutation was additionally re-derived by a second, earlier engine that imposes no lexicographic symmetry-breaking constraint at all, using a different solver and a different cube depth. It agreed. That path cannot inherit an error from the symmetry-breaking argument, which is the only novel component of the primary engine.

Note on the lower bound: a(19) >= 52 follows without any search, by taking a valid colouring of [1,a(18)-1] and making one further position a wildcard. The certificate above is that construction rather than an independently discovered colouring, and is included for checkability rather than as separate evidence; the computational content of this term is the refutation.
```

### 5. Verify the lower bound yourself
```
python vdw/verify_certificate.py "..11.1122.2211.1122.22.........11.1122.2211.1122.22" 19 3 3
```

## A217007 — a(7) = 68

Page: https://oeis.org/A217007  ·  click **edit**

Cross-check: **AGREES** — the refutation was re-derived through `vdw2`, which carries no symmetry-breaking constraint, so it cannot inherit an error from the one piece of new mathematics in the main engine.

### 1. DATA
```
35,40,53,54,56,66,67,68
```

### 2. b-file
Upload `b217007.txt` (8 rows, 0 to 7).

### 3. EXTENSIONS
```
a(7) from Leo Zhang, Jul 30 2026
```

### 4. COMMENT — paste verbatim
```
a(7) = w(7+2; 2^7, 4, 4) = 68.

Lower bound. The following colouring of [1,67] uses 7 wildcards (limit 7) and has no 4-term AP in colour 1 and no 4-term AP in colour 2, so a(7) > 67:

..1112112111.2221221222.1112112111.2221221222.1112112111.2221221222

('.' denotes one of the j colour classes with target 2, each holding at most one element.)

This is a certificate rather than an assertion: it is checked directly against the definition, in milliseconds, by a program that uses only the Python standard library and never invokes a SAT solver, so verifying it requires trusting none of the search code.

Upper bound. No valid colouring of [1,68] with at most 7 wildcards exists. The corresponding SAT instance is unsatisfiable (7269 s, all 40 cubes).

Because "no colouring exists" asserts an absence, it is only as strong as the claim that the formula faithfully encodes the problem. Guards applied: the CNF was proved equal to a direct transcription of the definition by exhaustive enumeration on small instances, in both directions; the symmetry-breaking constraint was proved to retain at least one representative of every orbit, since losing one is exactly how a satisfiable instance would be misreported as unsatisfiable; the wildcard cardinality constraint was tested at full scale from both sides; and published values of this family were re-derived by the same engine before any new term was claimed.

The parallel search also reports unsatisfiability only when every cube has returned an explicit verdict. A worker terminated by the operating system raises an error rather than being counted as an empty branch; without that distinction a killed worker is indistinguishable from a proof.

The refutation was additionally re-derived by a second, earlier engine that imposes no lexicographic symmetry-breaking constraint at all, using a different solver and a different cube depth. It agreed. That path cannot inherit an error from the symmetry-breaking argument, which is the only novel component of the primary engine.

Note on the lower bound: a(7) >= 68 follows without any search, by taking a valid colouring of [1,a(6)-1] and making one further position a wildcard. The certificate above is that construction rather than an independently discovered colouring, and is included for checkability rather than as separate evidence; the computational content of this term is the refutation.
```

### 5. Verify the lower bound yourself
```
python vdw/verify_certificate.py "..1112112111.2221221222.1112112111.2221221222.1112112111.2221221222" 7 4 4
```

## A217059 — a(9) = 74

Page: https://oeis.org/A217059  ·  click **edit**

Cross-check: **AGREES** — the refutation was re-derived through `vdw2`, which carries no symmetry-breaking constraint, so it cannot inherit an error from the one piece of new mathematics in the main engine.

### 1. DATA
```
22,32,43,44,50,55,61,65,70,74
```

### 2. b-file
Upload `b217059.txt` (10 rows, 0 to 9).

### 3. EXTENSIONS
```
a(9) from Leo Zhang, Jul 30 2026
```

### 4. COMMENT — paste verbatim
```
a(9) = w(9+2; 2^9, 3, 5) = 74.

Lower bound. The following colouring of [1,73] uses 9 wildcards (limit 9) and has no 3-term AP in colour 1 and no 5-term AP in colour 2, so a(9) > 73:

21121222212222.22221122112..2.2222.2222.2122..2211221212222.2222121221122

('.' denotes one of the j colour classes with target 2, each holding at most one element.)

This is a certificate rather than an assertion: it is checked directly against the definition, in milliseconds, by a program that uses only the Python standard library and never invokes a SAT solver, so verifying it requires trusting none of the search code.

Upper bound. No valid colouring of [1,74] with at most 9 wildcards exists. The corresponding SAT instance is unsatisfiable (3860 s, all 76 cubes).

Because "no colouring exists" asserts an absence, it is only as strong as the claim that the formula faithfully encodes the problem. Guards applied: the CNF was proved equal to a direct transcription of the definition by exhaustive enumeration on small instances, in both directions; the symmetry-breaking constraint was proved to retain at least one representative of every orbit, since losing one is exactly how a satisfiable instance would be misreported as unsatisfiable; the wildcard cardinality constraint was tested at full scale from both sides; and published values of this family were re-derived by the same engine before any new term was claimed.

The parallel search also reports unsatisfiability only when every cube has returned an explicit verdict. A worker terminated by the operating system raises an error rather than being counted as an empty branch; without that distinction a killed worker is indistinguishable from a proof.

The refutation was additionally re-derived by a second, earlier engine that imposes no lexicographic symmetry-breaking constraint at all, using a different solver and a different cube depth. It agreed. That path cannot inherit an error from the symmetry-breaking argument, which is the only novel component of the primary engine.

Note on the lower bound: the free append-wildcard construction only gives a(9) >= 71, so the colouring above was found by search (3464 s) and is an independent object rather than a relabelling of the previous term.
```

### 5. Verify the lower bound yourself
```
python vdw/verify_certificate.py "21121222212222.22221122112..2.2222.2222.2122..2211221212222.2222121221122" 9 3 5
```
