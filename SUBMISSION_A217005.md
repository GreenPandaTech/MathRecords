# A217005 extension: a(19) = 52

## Proposed DATA line

9,14,17,20,21,24,25,28,31,33,35,37,39,42,44,46,48,50,51,52

(previously 19 terms, a(0..18); this adds a(19) = 52)

## Name (unchanged)

Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 3, 3) with t_0 = t_1 = ... = t_{j-1} = 2.

## Proposed EXTENSIONS line

a(19) from <contributor>, <date>

## What was computed

a(19) = w(19+2; 2^19, 3, 3) = 52.

Lower bound. The following colouring of [1,51] uses 19 wildcards (limit 19), has no 3-term AP in colour 1 and no 3-term AP in colour 2, so a(19) > 51:

  ..11.1122.2211.1122.22.........11.1122.2211.1122.22

  ('.' = one of the j colours with target 2, each holding at most one element)

Upper bound. No such colouring of [1,52] exists: the corresponding SAT instance is unsatisfiable (4507 s, all 36 cubes).

## How to check the lower bound without trusting any of this

  python verify_certificate.py "..11.1122.2211.1122.22.........11.1122.2211.1122.22" 19 3 3

The verifier is standard-library-only and never invokes a SAT solver; it applies the definition directly to the string.

## b-file

0 9
1 14
2 17
3 20
4 21
5 24
6 25
7 28
8 31
9 33
10 35
11 37
12 39
13 42
14 44
15 46
16 48
17 50
18 51
19 52
