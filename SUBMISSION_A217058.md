# A217058 extension: a(12) = 57

## Proposed DATA line

18,21,25,29,33,36,40,42,45,48,52,55,57

(previously 12 terms, a(0..11); this adds a(12) = 57)

## Name (unchanged)

Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 3, 4) with t_0 = t_1 = ... = t_{j-1} = 2.

## Proposed EXTENSIONS line

a(12) from <contributor>, <date>

## What was computed

a(12) = w(12+2; 2^12, 3, 4) = 57.

Lower bound. The following colouring of [1,56] uses 12 wildcards (limit 12), has no 3-term AP in colour 1 and no 4-term AP in colour 2, so a(12) > 56:

  2.21221212.12.22211.112.2221.222.2.1..12221211212..22212

  ('.' = one of the j colours with target 2, each holding at most one element)

Upper bound. No such colouring of [1,57] exists: the corresponding SAT instance is unsatisfiable (6257 s, all 75 cubes).

## How to check the lower bound without trusting any of this

  python verify_certificate.py "2.21221212.12.22211.112.2221.222.2.1..12221211212..22212" 12 3 4

The verifier is standard-library-only and never invokes a SAT solver; it applies the definition directly to the string.

## b-file

0 18
1 21
2 25
3 29
4 33
5 36
6 40
7 42
8 45
9 48
10 52
11 55
12 57
