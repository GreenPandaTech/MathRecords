"""Turn a verified result into the exact text an OEIS extension needs.

Deliberately mechanical: it reads the result JSON and the certificate, re-runs
the independent verifier on the certificate before writing anything, and refuses
to emit a submission if that check fails.  Nothing here is hand-typed, so the
number in the write-up cannot drift from the number that was computed.

This PREPARES a submission.  It does not send one.  Submitting is an
outward-facing act that needs an explicit go-ahead.

A single OEIS edit may add SEVERAL terms at once, and for a family where we hold
two consecutive new values that is the right way to send them: one review instead
of two, and the second term never sits blocked behind the first being accepted.
Pass the earlier new term(s) with --prior.

Usage:
    python make_submission.py <sat_json> <unsat_json>
    python make_submission.py <sat_json> <unsat_json> --prior 12:57
        ^ a(12)=57 is also new and unpublished, so the DATA line carries both.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Every family this engine can extend.  Keeping the published terms here rather
# than in the prose means the DATA line is assembled from the same list the
# computation was gated against.
FAMILIES = {
    'A217058': {
        'targets': [3, 4],
        'name': ('Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 3, 4) '
                 'with t_0 = t_1 = ... = t_{j-1} = 2.'),
        'published': [18, 21, 25, 29, 33, 36, 40, 42, 45, 48, 52, 55],
    },
    'A217005': {
        'targets': [3, 3],
        'name': ('Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 3, 3) '
                 'with t_0 = t_1 = ... = t_{j-1} = 2.'),
        'published': [9, 14, 17, 20, 21, 24, 25, 28, 31, 33, 35, 37, 39, 42,
                      44, 46, 48, 50, 51],
    },
    'A217008': {
        'targets': [3, 3, 3],
        'name': ('Van der Waerden numbers w(j+3; t_0,...,t_{j-1}, 3, 3, 3) '
                 'with t_0 = ... = t_{j-1} = 2.'),
        'published': [27, 40, 41, 42, 45, 49, 52],
    },
    'A217007': {
        'targets': [4, 4],
        'name': ('Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 4, 4) '
                 'with t_0 = t_1 = ... = t_{j-1} = 2.'),
        'published': [35, 40, 53, 54, 56, 66, 67],
    },
    'A217060': {
        'targets': [3, 6],
        'name': ('Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 3, 6) '
                 'with t_0 = t_1 = ... = t_{j-1} = 2.'),
        'published': [32, 40, 48, 56, 60, 65, 71],
    },
    'A217236': {
        'targets': [4, 5],
        'name': ('Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 4, 5) '
                 'with t_0 = t_1 = ... = t_{j-1} = 2.'),
        'published': [55, 71, 75, 79],
    },
    'A217237': {
        'targets': [4, 6],
        'name': ('Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 4, 6) '
                 'with t_0 = t_1 = ... = t_{j-1} = 2.'),
        'published': [73, 83, 93, 101],
    },
    'A217059': {
        'targets': [3, 5],
        'name': ('Van der Waerden numbers w(j+2; t_0,t_1,...,t_{j-1}, 3, 5) '
                 'with t_0 = t_1 = ... = t_{j-1} = 2.'),
        'published': [22, 32, 43, 44, 50, 55, 61, 65, 70],
    },
}


def family_for(targets):
    """Identify the sequence from the colour targets recorded in the result."""
    for seq, f in FAMILIES.items():
        if f['targets'] == list(targets):
            return seq, f
    raise SystemExit(f'no known OEIS family with targets {targets}')


def parse_priors(argv):
    """--prior j:value, repeatable. Earlier new terms not yet in the OEIS."""
    priors = {}
    for i, a in enumerate(argv):
        if a == '--prior' and i + 1 < len(argv):
            j_s, v_s = argv[i + 1].split(':')
            priors[int(j_s)] = int(v_s)
    return priors


def main():
    wit = json.load(open(sys.argv[1]))          # SAT at n = a(j)-1
    ref = json.load(open(sys.argv[2]))          # UNSAT at n = a(j)
    priors = parse_priors(sys.argv)

    j = wit['j']
    targets = wit['targets']
    cert = wit['certificate']
    value = ref['n']
    SEQ, fam = family_for(targets)
    NAME, PUBLISHED = fam['name'], fam['published']
    # The result must be the next index after the published list PLUS any earlier
    # new terms being sent in the same edit. Without the priors this would refuse
    # a second-generation term outright, which is correct on its own and wrong
    # when both terms go in one submission.
    expected_j = len(PUBLISHED) + len(priors)
    assert j == expected_j, (
        f'{SEQ} has {len(PUBLISHED)} published terms a(0..{len(PUBLISHED)-1}) and '
        f'{len(priors)} prior new term(s) supplied, so the next index is '
        f'a({expected_j}); this result is a({j}). Supply the missing term(s) with '
        f'--prior j:value, or compute them first.')
    for k in range(len(PUBLISHED), j):
        assert k in priors, (
            f'a({k}) is neither published nor supplied via --prior, so the DATA '
            f'line would have a hole in it. OEIS terms must be contiguous.')

    assert ref['sat'] is False, 'the refutation file does not record UNSAT'
    assert wit['sat'] is True, 'the witness file does not record SAT'
    assert len(cert) == value - 1, \
        f'witness length {len(cert)} != a(j)-1 = {value-1}'
    assert ref['j'] == j and ref['targets'] == targets, 'mismatched instances'

    # never write a submission around a certificate we have not just re-checked
    r = subprocess.run([sys.executable, os.path.join(HERE, 'verify_certificate.py'),
                        cert, str(j)] + [str(t) for t in targets],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print('INDEPENDENT VERIFIER REJECTED THE CERTIFICATE -- refusing to write')
        print(r.stdout, r.stderr)
        return 1

    terms = PUBLISHED + [priors[k] for k in sorted(priors)] + [value]
    out = []
    out.append(f'# {SEQ} extension: a({j}) = {value}')
    out.append('')
    out.append('## Proposed DATA line')
    out.append('')
    out.append(','.join(str(t) for t in terms))
    out.append('')
    out.append(f'(previously {len(PUBLISHED)} terms, a(0..{len(PUBLISHED)-1}); '
               f'this adds a({j}) = {value})')
    out.append('')
    out.append('## Name (unchanged)')
    out.append('')
    out.append(NAME)
    out.append('')
    out.append('## Proposed EXTENSIONS line')
    out.append('')
    first_new = len(PUBLISHED)
    out.append(f'a({first_new}) from <contributor>, <date>' if first_new == j
               else f'a({first_new})-a({j}) from <contributor>, <date>')
    if priors:
        out.append('')
        out.append(f'NOTE this edit adds {len(priors) + 1} terms at once: '
                   + ', '.join(f'a({k})={priors[k]}' for k in sorted(priors))
                   + f', a({j})={value}. Each was established by the same pair of '
                   'halves - an explicit checkable colouring and a machine '
                   'refutation one step above it. Sending them together means one '
                   'review rather than several, and no term waits on its '
                   'predecessor being accepted first.')
    out.append('')
    out.append('## What was computed')
    out.append('')
    out.append(f'a({j}) = w({j}+{len(targets)}; 2^{j}, '
               f'{", ".join(map(str, targets))}) = {value}.')
    out.append('')
    conds = ' and '.join(f'no {t}-term AP in colour {i}'
                         for i, t in enumerate(targets, start=1))
    out.append(f'Lower bound. The following colouring of [1,{value-1}] uses '
               f'{cert.count(".")} wildcards (limit {j}), has {conds}, '
               f'so a({j}) > {value-1}:')
    out.append('')
    out.append(f'  {cert}')
    out.append('')
    out.append("  ('.' = one of the j colours with target 2, each holding at "
               "most one element)")
    out.append('')
    out.append(f'Upper bound. No such colouring of [1,{value}] exists: the '
               f'corresponding SAT instance is unsatisfiable '
               f'({ref["sec"]:.0f} s, {ref["via"]}).')
    out.append('')
    out.append('## How to check the lower bound without trusting any of this')
    out.append('')
    out.append(f'  python verify_certificate.py "{cert}" {j} '
               f'{" ".join(map(str, targets))}')
    out.append('')
    out.append('The verifier is standard-library-only and never invokes a SAT '
               'solver; it applies the definition directly to the string.')
    out.append('')
    out.append('## b-file')
    out.append('')
    out.extend(f'{i} {t}' for i, t in enumerate(terms))
    text = '\n'.join(out) + '\n'

    path = os.path.join(os.path.dirname(HERE), f'SUBMISSION_{SEQ}.md')
    open(path, 'w', encoding='utf-8').write(text)

    bpath = os.path.join(os.path.dirname(HERE), f'b{SEQ[1:]}.txt')
    open(bpath, 'w', encoding='utf-8').write(
        '\n'.join(f'{i} {t}' for i, t in enumerate(terms)) + '\n')

    print(text)
    print(f'--- written: {path}')
    print(f'--- written: {bpath}')
    print('--- NOT submitted. Submission needs an explicit go-ahead.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
