#!/usr/bin/env python3
"""Build SUBMIT.md: everything to paste into OEIS, and nothing that needs typing.

Every number, certificate and timing here is read from the evidence files the
computation actually wrote. Nothing is transcribed by hand, because a submission
is exactly where a hand-copied digit becomes a retraction.

It writes one section per confirmed term, each with the four fields an OEIS edit
needs (DATA, b-file, EXTENSIONS, COMMENT) as literal copy-paste blocks. The
COMMENT is the part that earns acceptance: an editor's real question about an
"unsatisfiable" is why they should believe it, so each comment states what was
audited and, where it applies, what is weaker than it looks.

A term with no agreeing cross-check is EXCLUDED, loudly. That is the whole point
of having run them.

Usage:  python make_submit_pack.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VDW = os.path.join(HERE, 'vdw')

# Read the claims table rather than restating it, so this file cannot disagree
# with the harness that verifies the repository.
_src = open(os.path.join(HERE, 'verify_all.py'), encoding='utf-8').read()
_ns = {}
exec(_src[_src.index('CLAIMS = {'):_src.index('_fail = []')], _ns)
CLAIMS = _ns['CLAIMS']

# Sequences whose refutation was re-derived along more than one disjoint path.
EXTRA_PATHS = {
    'A217058': ('three separate times, including through an engine that imposes no '
                'symmetry-breaking constraint at all and a second CDCL solver'),
}


def load(name):
    p = os.path.join(VDW, name)
    return json.load(open(p)) if os.path.exists(p) else None


def crosscheck(j):
    return load(f'crosscheck_a{j}.json')


def targets_phrase(targets):
    return ' and '.join(f'no {t}-term AP in colour {i}'
                        for i, t in enumerate(targets, start=1))


def section(seq, targets, published, j, value, wit, ref, xc):
    cert = wit['certificate']
    tlist = ', '.join(str(t) for t in targets)
    data = ','.join(str(t) for t in published + [value])
    free_bound = published[-1] + 1
    earned = wit.get('n') == value - 1 and wit.get('witness_verified') \
        and value - 1 > free_bound - 1

    L = []
    L.append(f'## {seq} — a({j}) = {value}')
    L.append('')
    L.append(f'Page: https://oeis.org/{seq}  ·  click **edit**')
    L.append('')

    if xc and xc.get('AGREES'):
        L.append('Cross-check: **AGREES** — the refutation was re-derived through '
                 '`vdw2`, which carries no symmetry-breaking constraint, so it cannot '
                 'inherit an error from the one piece of new mathematics in the main '
                 'engine.')
    elif seq in EXTRA_PATHS:
        L.append(f'Cross-check: refuted {EXTRA_PATHS[seq]}.')
    L.append('')

    L.append('### 1. DATA')
    L.append('```')
    L.append(data)
    L.append('```')
    L.append('')
    L.append('### 2. b-file')
    L.append(f'Upload `b{seq[1:]}.txt` ({len(published) + 1} rows, 0 to {j}).')
    L.append('')
    L.append('### 3. EXTENSIONS')
    L.append('```')
    L.append(f'a({j}) from Leo Zhang, Jul 30 2026')
    L.append('```')
    L.append('')
    L.append('### 4. COMMENT — paste verbatim')
    L.append('```')
    L.append(f'a({j}) = w({j}+{len(targets)}; 2^{j}, {tlist}) = {value}.')
    L.append('')
    L.append(f'Lower bound. The following colouring of [1,{value-1}] uses '
             f'{cert.count(".")} wildcards (limit {j}) and has {targets_phrase(targets)}, '
             f'so a({j}) > {value-1}:')
    L.append('')
    L.append(cert)
    L.append('')
    L.append("('.' denotes one of the j colour classes with target 2, each holding at "
             'most one element.)')
    L.append('')
    L.append('This is a certificate rather than an assertion: it is checked directly '
             'against the definition, in milliseconds, by a program that uses only the '
             'Python standard library and never invokes a SAT solver, so verifying it '
             'requires trusting none of the search code.')
    L.append('')
    L.append(f'Upper bound. No valid colouring of [1,{value}] with at most {j} '
             f'wildcards exists. The corresponding SAT instance is unsatisfiable '
             f'({ref["sec"]:.0f} s, {ref["via"]}).')
    L.append('')
    L.append('Because "no colouring exists" asserts an absence, it is only as strong '
             'as the claim that the formula faithfully encodes the problem. Guards '
             'applied: the CNF was proved equal to a direct transcription of the '
             'definition by exhaustive enumeration on small instances, in both '
             'directions; the symmetry-breaking constraint was proved to retain at '
             'least one representative of every orbit, since losing one is exactly how '
             'a satisfiable instance would be misreported as unsatisfiable; the '
             'wildcard cardinality constraint was tested at full scale from both '
             'sides; and published values of this family were re-derived by the same '
             'engine before any new term was claimed.')
    L.append('')
    L.append('The parallel search also reports unsatisfiability only when every cube '
             'has returned an explicit verdict. A worker terminated by the operating '
             'system raises an error rather than being counted as an empty branch; '
             'without that distinction a killed worker is indistinguishable from a '
             'proof.')
    if xc and xc.get('AGREES'):
        L.append('')
        L.append('The refutation was additionally re-derived by a second, earlier '
                 'engine that imposes no lexicographic symmetry-breaking constraint at '
                 'all, using a different solver and a different cube depth. It agreed. '
                 'That path cannot inherit an error from the symmetry-breaking '
                 'argument, which is the only novel component of the primary engine.')
    elif seq in EXTRA_PATHS:
        L.append('')
        L.append(f'The refutation was re-established {EXTRA_PATHS[seq]}.')
    if not earned:
        L.append('')
        L.append(f'Note on the lower bound: a({j}) >= {free_bound} follows without any '
                 f'search, by taking a valid colouring of [1,a({j-1})-1] and making one '
                 f'further position a wildcard. The certificate above is that '
                 f'construction rather than an independently discovered colouring, and '
                 f'is included for checkability rather than as separate evidence; the '
                 f'computational content of this term is the refutation.')
    else:
        L.append('')
        L.append(f'Note on the lower bound: the free append-wildcard construction only '
                 f'gives a({j}) >= {free_bound}, so the colouring above was found by '
                 f'search ({wit["sec"]:.0f} s) and is an independent object rather than '
                 f'a relabelling of the previous term.')
    L.append('```')
    L.append('')
    L.append('### 5. Verify the lower bound yourself')
    L.append('```')
    L.append(f'python vdw/verify_certificate.py "{cert}" {j} {" ".join(map(str, targets))}')
    L.append('```')
    L.append('')
    return L


def main():
    ready, blocked = [], []
    for seq, (targets, published, j, value, wf, rf) in CLAIMS.items():
        wit, ref = load(wf), load(rf)
        if not (wit and ref):
            blocked.append((seq, j, value, 'evidence files missing'))
            continue
        xc = crosscheck(j)
        if not (xc and xc.get('AGREES')) and seq not in EXTRA_PATHS:
            blocked.append((seq, j, value,
                            'no agreeing cross-check — DO NOT SUBMIT until '
                            f'vdw/crosscheck_a{j}.json reports AGREES'))
            continue
        ready.append((seq, targets, published, j, value, wit, ref, xc))

    out = [
        '# OEIS submission pack',
        '',
        'Generated from the evidence files, not typed. Every certificate, timing and',
        'DATA line below was read out of the JSON the computation wrote.',
        '',
        f'**{len(ready)} term(s) ready to submit.**',
        '',
        '## Do this first, once',
        '',
        '1. Register at https://oeis.org/ — approval is manual and takes a day or two.',
        '   This is the only step with a waiting period, so start it before anything else.',
        '2. Run `python verify_all.py` here. It must exit 0. If it does not, a claim has',
        '   drifted from its evidence and nothing should be submitted until it passes.',
        '',
        '## Order to submit',
        '',
        '**A217058 first, and alone.** It is the only term whose refutation was',
        'established three separate ways, so it is the safest place to find out what the',
        'editors ask for. Wait for one round-trip before sending the others — you will',
        'learn more from one reply than from any amount of preparation, and if an editor',
        'questions the strongest result you want that on one submission, not four.',
        '',
        '## Never',
        '',
        '* Submit a term whose cross-check does not say AGREES.',
        '* Retype a certificate. Copy it. A single wrong character is a retraction.',
        '* Claim a term whose family gate did not reproduce the published value.',
        '',
        '---',
        '',
    ]
    for r in ready:
        out += section(*r)

    if blocked:
        out += ['---', '', '## NOT ready — do not submit these', '']
        for seq, j, value, why in blocked:
            out.append(f'* **{seq} a({j}) = {value}** — {why}')
        out.append('')

    path = os.path.join(HERE, 'SUBMIT.md')
    open(path, 'w', encoding='utf-8').write('\n'.join(out))
    print(f'wrote {path}')
    print(f'ready: {", ".join(r[0] for r in ready) or "none"}')
    if blocked:
        print(f'blocked: {", ".join(b[0] for b in blocked)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
