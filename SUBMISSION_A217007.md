# A217007 extension: a(7) = 68

## Proposed DATA line

35,40,53,54,56,66,67,68

(previously 7 terms, a(0..6); this adds a(7) = 68)

## Name (unchanged)

Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 4, 4) with t_0 = t_1 = ... = t_{j-1} = 2.

## Proposed EXTENSIONS line

a(7) from <contributor>, <date>

## What was computed

a(7) = w(7+2; 2^7, 4, 4) = 68.

Lower bound. The following colouring of [1,67] uses 7 wildcards (limit 7), has no 4-term AP in colour 1 and no 4-term AP in colour 2, so a(7) > 67:

  ..1112112111.2221221222.1112112111.2221221222.1112112111.2221221222

  ('.' = one of the j colours with target 2, each holding at most one element)

Upper bound. No such colouring of [1,68] exists: the corresponding SAT instance is unsatisfiable (7269 s, all 40 cubes).

## How to check the lower bound without trusting any of this

  python verify_certificate.py "..1112112111.2221221222.1112112111.2221221222.1112112111.2221221222" 7 4 4

The verifier is standard-library-only and never invokes a SAT solver; it applies the definition directly to the string.

## b-file

0 35
1 40
2 53
3 54
4 56
5 66
6 67
7 68
