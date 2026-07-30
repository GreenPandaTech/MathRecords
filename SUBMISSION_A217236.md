# A217236 extension: a(4) = 84

## Proposed DATA line

55,71,75,79,84

(previously 4 terms, a(0..3); this adds a(4) = 84)

## Name (unchanged)

Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 4, 5) with t_0 = t_1 = ... = t_{j-1} = 2.

## Proposed EXTENSIONS line

a(4) from <contributor>, <date>

## What was computed

a(4) = w(4+2; 2^4, 4, 5) = 84.

Lower bound. The following colouring of [1,83] uses 4 wildcards (limit 4), has no 4-term AP in colour 1 and no 5-term AP in colour 2, so a(4) > 83:

  122121221221212221.212121221121222211121.221212222.2222.212211211122221211122212122

  ('.' = one of the j colours with target 2, each holding at most one element)

Upper bound. No such colouring of [1,84] exists: the corresponding SAT instance is unsatisfiable (7965 s, all 80 cubes).

## How to check the lower bound without trusting any of this

  python verify_certificate.py "122121221221212221.212121221121222211121.221212222.2222.212211211122221211122212122" 4 4 5

The verifier is standard-library-only and never invokes a SAT solver; it applies the definition directly to the string.

## b-file

0 55
1 71
2 75
3 79
4 84
