#!/usr/bin/env python3
"""Standalone verifier for a mixed van der Waerden lower-bound certificate.

No dependencies beyond the standard library.  It does not know how the
certificate was produced and never touches a SAT solver -- it just reads the
colouring and checks the definition directly.

A certificate is a string of length n over the alphabet {., 1, 2, ...}:
  '.'  -> the position is assigned to one of the j colours whose target is 2
          (each such colour holds at most one element, so at most j dots)
  'c'  -> the position has real colour c, whose target length is t_c

It witnesses   w(j + r; 2^j, t_1, ..., t_r) > n
provided (a) at most j dots, and (b) no colour c contains a t_c-term
arithmetic progression.

Usage:
    python verify_certificate.py <certificate> <j> <t_1> [t_2 ...]
"""
import sys


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
        ps = set(pos)
        for a in pos:
            for d in range(1, n):
                if a + (t - 1) * d > n:
                    break
                if all((a + m * d) in ps for m in range(t)):
                    problems.append(
                        f'colour {c} contains the {t}-term AP starting {a} step {d}')
                    break
            else:
                continue
            break

    return problems, dots


def main():
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
    print(f'\nACCEPTED: no monochromatic AP, wildcard budget respected.')
    print(f'          This proves {spec} > {n}, i.e. {spec} >= {n + 1}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
