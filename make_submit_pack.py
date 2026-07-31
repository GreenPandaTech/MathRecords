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


def copyright_holder():
    """Read the author's name from LICENSE, the single place it is written down.

    Deliberately not hardcoded. A name in a source file travels with every copied
    snippet, so it lives in LICENSE alone and everything else derives it. That also
    means there is exactly one place to change if it ever needs changing.
    """
    import re
    lic = open(os.path.join(HERE, 'LICENSE'), encoding='utf-8').read()
    m = re.search(r'Copyright \(c\) \d{4} (.+?)\. All rights reserved', lic)
    if not m:
        raise SystemExit('LICENSE has no parseable copyright line; refusing to '
                         'guess the attribution for a submission')
    return m.group(1).strip()

# Read the claims table rather than restating it, so this file cannot disagree
# with the harness that verifies the repository.
_src = open(os.path.join(HERE, 'verify_all.py'), encoding='utf-8').read()
_ns = {}
exec(_src[_src.index('CLAIMS = {'):_src.index('_fail = []')], _ns)
CLAIMS = _ns['CLAIMS']


def _submit_date():
    """The date that goes in EXTENSIONS and the comment signature.

    Defaults to today, because the pack is generated on the day it is pasted and
    a stale hardcoded date is a wrong attribution date on a permanent record.
    `--date "Aug 03 2026"` overrides it. Zero-padded day, which is the OEIS form
    (the existing line on A217058 reads "Dec 07 2012").
    """
    import datetime
    if '--date' in sys.argv:
        return sys.argv[sys.argv.index('--date') + 1]
    return datetime.date.today().strftime('%b %d %Y')


SUBMIT_DATE = _submit_date()


def load(name):
    p = os.path.join(VDW, name)
    return json.load(open(p)) if os.path.exists(p) else None


def crosscheck(j):
    return load(f'crosscheck_a{j}.json')


def plain_definition(targets):
    """What a(j) counts, in words, for a reader who has not seen the setup.

    The OEIS entry's own text never mentions partitions or arithmetic
    progressions -- the definition of w() lives only in the cited papers. A
    comment that opens with "the following colouring ... no 3-term AP" is
    therefore unreadable to anyone but a specialist, which is exactly what the
    editors objected to on the first submission. So the comment now defines its
    own terms before using them.
    """
    t1, t2 = targets
    if t1 == t2:
        return f'or a {t1}-term arithmetic progression in either of the last two'
    return (f'a {t1}-term arithmetic progression in the next, or a {t2}-term one '
            f'in the last')


def plain_avoids(j, targets):
    """How to read the certificate string, in the same plain register."""
    t1, t2 = targets
    if t1 == t2:
        return f'neither of them contains a {t1}-term AP'
    return (f'no {t1}-term AP in the class marked 1 and no {t2}-term AP in the '
            f'class marked 2')


def section(seq, targets, published, j, value, wit, ref, xc):
    cert = wit['certificate']
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
    L.append('')

    L.append('### 1. DATA')
    L.append('```')
    L.append(data)
    L.append('```')
    L.append('')
    L.append('### 2. b-file — nothing to upload')
    L.append(f'`{seq}` has no uploaded b-file, so the OEIS generates one from DATA and '
             f'the new term appears there by itself. `b{seq[1:]}.txt` '
             f'({len(published) + 1} rows, 0 to {j}) is in this repository if an editor '
             f'ever asks for one.')
    L.append('')
    L.append('### 3. EXTENSIONS — ADD this line; never alter the lines already there')
    L.append('```')
    L.append(f'a({j}) from _{copyright_holder()}_, {SUBMIT_DATE}')
    L.append('```')
    L.append('')
    L.append('### 4. COMMENT — paste verbatim, including the wrapper lines')
    L.append('```')
    # US spelling throughout: the OEIS style sheet requires it, and an editor
    # corrected "colour"/"relabelling" by hand on the first submission. The word
    # "colouring" is avoided altogether in favour of "partition into classes",
    # which needs no glossary.
    L.append(f'From _{copyright_holder()}_, {SUBMIT_DATE}: (Start)')
    L.append(f'a({j}) = {value} was computed with a SAT solver.')
    L.append('')
    L.append(f'Written out, a({j}) is the least n such that every partition of [1,n] '
             f'into {j}+{len(targets)} classes contains two elements in one of the '
             f'first {j} classes, {plain_definition(targets)}.')
    L.append('')
    L.append(f'The following partition of [1,{value-1}] has none of those, so '
             f'a({j}) > {value-1}. Each "." is one of the {j} classes that must stay a '
             f'singleton, and 1 and 2 mark the two remaining classes '
             f'({plain_avoids(j, targets)}):')
    L.append('')
    L.append(cert)
    L.append('')
    if earned:
        origin = 'The partition above was found by search.'
    else:
        origin = ("The partition above is the previous term's with one more singleton, "
                  'so the content of this term is the upper bound.')
    L.append(f'That no such partition of [1,{value}] exists was confirmed by a second, '
             f'independent encoding. {origin}')
    L.append('(End)')
    L.append('```')
    L.append('')
    L.append(f'*Evidence behind the two sentences above, kept out of the comment because '
             f'the editors asked for brevity: refutation {ref["sec"]:.0f} s, {ref["via"]}; '
             f'witness {wit["sec"]:.0f} s; free construction alone would give only '
             f'a({j}) >= {free_bound}. The family gate reproduced the published '
             f'a({j-1}) before this term was claimed.*')
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
        if not (xc and xc.get('AGREES')):
            blocked.append((seq, j, value,
                            'no agreeing cross-check — DO NOT SUBMIT until '
                            f'vdw/crosscheck_a{j}.json reports AGREES'))
            continue
        ready.append((seq, targets, published, j, value, wit, ref, xc))

    # Rank by evidence, not by age. The first result is not automatically the
    # best-evidenced one, and recommending a submission order from memory rather
    # than from the files is how a weaker term ends up going first.
    def strength(r):
        seq, targets, published, j, value, wit, ref, xc = r
        paths = 1 + (1 if (xc or {}).get('vdw2_unsat_confirmed') else 0)                   + (1 if (xc or {}).get('vdw4_norevsym_unsat_confirmed') else 0)
        free = published[-1] + 1
        earned = wit.get('n') == value - 1 and wit.get('witness_verified')             and (value - 1) > (free - 1)
        return (paths, 1 if earned else 0)

    ready.sort(key=strength, reverse=True)
    best = ready[0][0] if ready else None
    ranking = []
    for r in ready:
        paths, earned = strength(r)
        ranking.append(f'* **{r[0]}** a({r[3]})={r[4]} — {paths} confirmed refutation '
                       f'path(s), lower bound '
                       f'{"found by search" if earned else "from the free construction"}')

    out = [
        '# OEIS submission pack',
        '',
        'Generated from the evidence files, not typed. Every certificate, timing and',
        'DATA line below was read out of the JSON the computation wrote.',
        '',
        f'**{len(ready)} term(s) ready to submit.**',
        '',
        '## Do this first, every time',
        '',
        'Run `python verify_all.py` here. It must exit 0. If it does not, a claim has',
        'drifted from its evidence and nothing should be submitted until it passes.',
        '',
        'Registration is already done, so there is no waiting period any more.',
        '',
        '## Order to submit',
        '',
        'Ranked by evidence actually on disk, strongest first:',
        '',
    ] + ranking + [
        '',
        f'**Submit {best} first, and alone**, then wait for it to be ACCEPTED before',
        'sending the next. One round-trip teaches more than any amount of preparation,',
        'and a question about your strongest result is better answered once than five',
        'times. `A217058` was submitted on Jul 30 2026 and is under review.',
        '',
        '## Never',
        '',
        '* Submit a term whose cross-check does not say AGREES.',
        '* Retype a certificate. Copy it. A single wrong character is a retraction.',
        '* Claim a term whose family gate did not reproduce the published value.',
        '* Alter or delete a line already in EXTENSIONS. Add yours below the existing ones.',
        '* Write British spellings in a submission: the OEIS uses US English (color,',
        '  relabeling). The comments below are already US-spelled.',
        '* Let a comment grow. The editors asked for brevity and for every technical term',
        '  to be defined before use, since the entry itself never mentions partitions or',
        '  arithmetic progressions. If in doubt, submit DATA and EXTENSIONS with no comment',
        '  at all — an editor explicitly offered that.',
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
