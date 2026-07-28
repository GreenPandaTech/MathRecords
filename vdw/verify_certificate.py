#!/usr/bin/env python3
"""Standalone verifier for a mixed van der Waerden lower-bound certificate.

No dependencies beyond the standard library.  It does not know how the
certificate was produced and never touches a SAT solver -- it just reads the
colouring and checks the definition directly.  This file is the thing a
sceptical reader is meant to run, so it carries its own controls: run
`--selftest` and it will prove it can reject certificates it should reject.

A certificate is a string of length n over the alphabet {., 1, 2, ...}:
  '.'  -> the position is assigned to one of the j colours whose target is 2
          (each such colour holds at most one element, so at most j dots)
  'c'  -> the position has real colour c, whose target length is t_c

It witnesses   w(j + r; 2^j, t_1, ..., t_r) > n
provided (a) at most j dots, and (b) no colour c contains a t_c-term
arithmetic progression.

Usage:
    python verify_certificate.py <certificate> <j> <t_1> [t_2 ...]
    python verify_certificate.py --selftest
"""
import sys


def find_ap(positions, t, n):
    """First t-term AP inside `positions`, or None.

    Every start and every common difference is examined.  An earlier version of
    this function shared one `break` between "this start has no more room" and
    "an AP was found", which made it abandon the scan after the first element of
    the class and accept invalid certificates.  Hence the selftest below.
    """
    ps = set(positions)
    for a in positions:
        for d in range(1, n):
            if a + (t - 1) * d > n:
                break                       # no room left for THIS start only
            if all((a + m * d) in ps for m in range(t)):
                return a, d
    return None


def verify(cert, j, targets):
    n = len(cert)
    r = len(targets)
    problems = []

    dots = cert.count('.')
    if dots > j:
        problems.append(f'uses {dots} wildcards but only {j} are allowed')

    alphabet = set('.') | {str(c) for c in range(1, r + 1)}
    bad = sorted(set(cert) - alphabet)
    if bad:
        problems.append(f'unexpected symbols {bad}')

    for c, t in enumerate(targets, start=1):
        pos = [i + 1 for i, ch in enumerate(cert) if ch == str(c)]
        hit = find_ap(pos, t, n)
        if hit:
            a, d = hit
            terms = ', '.join(str(a + m * d) for m in range(t))
            problems.append(
                f'colour {c} contains the {t}-term AP {terms} (start {a}, step {d})')

    return problems, dots


def selftest():
    """Controls: the verifier must accept a valid witness and reject invalid
    ones, including an AP that does not start at the first element of its
    class -- the case the previous implementation missed."""
    cases = [
        # (cert, j, targets, should_be_accepted, note)
        ('12211221', 0, [3, 4], True,
         'valid: colour 1 {1,4,5,8} has no 3-AP, colour 2 {2,3,6,7} has no 4-AP'),
        ('1222111222', 0, [3, 4], False,
         'colour 1 on {1,5,6,7}: AP 5,6,7 does not start at the class minimum'),
        ('1122212221', 0, [3, 5], False,
         'colour 1 on {1,2,6,10}: AP 2,6,10 starts mid-class with step 4'),
        ('1122', 0, [3, 4], True, 'no 3-AP in colour 1, no 4-AP in colour 2'),
        ('...', 2, [3], False, 'wildcard budget exceeded'),
        ('11', 0, [3], True, 'two elements cannot contain a 3-term AP'),
        ('111', 0, [3], False, 'AP 1,2,3'),
        ('10101', 0, [3], False, 'symbol 0 is not in the alphabet'),
    ]
    ok = True
    for cert, j, targets, expect, note in cases:
        problems, _ = verify(cert, j, targets)
        got = not problems
        flag = 'ok ' if got == expect else 'FAIL'
        if got != expect:
            ok = False
        print(f'  [{flag}] {cert!r:14s} j={j} t={targets}  '
              f'accepted={got} expected={expect}   {note}')
        if problems and got != expect:
            print('         ', problems)
    print('SELFTEST PASSED' if ok else 'SELFTEST FAILED')
    return 0 if ok else 1


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == '--selftest':
        return selftest()
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    cert = sys.argv[1].strip()
    j = int(sys.argv[2])
    targets = [int(a) for a in sys.argv[3:]]
    problems, dots = verify(cert, j, targets)
    n = len(cert)
    r = len(targets)
    spec = f'w({j}+{r}; ' + ', '.join(['2'] * j + [str(t) for t in targets]) + ')'
    print(f'certificate length n = {n}')
    print(f'wildcards used       = {dots}  (limit {j})')
    print(f'colour targets       = {targets}')
    for c, t in enumerate(targets, start=1):
        print(f'  colour {c}: {cert.count(str(c)):4d} elements, must avoid {t}-term APs')
    if problems:
        print('\nREJECTED:')
        for p in problems:
            print('  -', p)
        return 1
    print('\nACCEPTED: no monochromatic AP, wildcard budget respected.')
    print(f'          This proves {spec} > {n}, i.e. {spec} >= {n + 1}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
