# A217059 extension: a(9) = 74

## Proposed DATA line

22,32,43,44,50,55,61,65,70,74

(previously 9 terms, a(0..8); this adds a(9) = 74)

## Name (unchanged)

Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 3, 5) with t_0 = t_1 = ... = t_{j-1} = 2.

## Proposed EXTENSIONS line

a(9) from <contributor>, <date>

## What was computed

a(9) = w(9+2; 2^9, 3, 5) = 74.

Lower bound. The following colouring of [1,73] uses 9 wildcards (limit 9), has no 3-term AP in colour 1 and no 5-term AP in colour 2, so a(9) > 73:

  21121222212222.22221122112..2.2222.2222.2122..2211221212222.2222121221122

  ('.' = one of the j colours with target 2, each holding at most one element)

Upper bound. No such colouring of [1,74] exists: the corresponding SAT instance is unsatisfiable (3860 s, all 76 cubes).

## How to check the lower bound without trusting any of this

  python verify_certificate.py "21121222212222.22221122112..2.2222.2222.2122..2211221212222.2222121221122" 9 3 5

The verifier is standard-library-only and never invokes a SAT solver; it applies the definition directly to the string.

## b-file

0 22
1 32
2 43
3 44
4 50
5 55
6 61
7 65
8 70
9 74
