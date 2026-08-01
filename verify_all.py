#!/usr/bin/env python3
"""Re-check every claim this project makes, from scratch, in one command.

The point is to be able to say "it is complete" and mean something checkable
rather than remembered.  Nothing here trusts a previous run: every certificate
on disk is re-verified by the standalone checker, every audit is re-executed,
and every number quoted in the prose is compared against the JSON the
computation actually wrote.

Exit code 0 means every claim in the repository is currently supported by
evidence on disk.  Anything else means a claim has drifted from its evidence and
the write-up is wrong until it is fixed.

Usage:
    python verify_all.py            # everything
    python verify_all.py --fast     # skip the two slow audits
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
VDW = os.path.join(ROOT, 'vdw')
EC = os.path.join(ROOT, 'ec')
PY = sys.executable

# Claimed results: sequence -> (targets, published terms, new index, new value,
#                               witness json, refutation json)
CLAIMS = {
    'A217058': ([3, 4],
                [18, 21, 25, 29, 33, 36, 40, 42, 45, 48, 52, 55],
                12, 57, 'probe_n56.json', 'probe_n57.json'),
    'A217005': ([3, 3],
                [9, 14, 17, 20, 21, 24, 25, 28, 31, 33, 35, 37, 39, 42, 44, 46,
                 48, 50, 51],
                19, 52, 'probe_A217005_n51_witness.json',
                'probe_A217005_n52.json'),
    'A217007': ([4, 4],
                [35, 40, 53, 54, 56, 66, 67],
                7, 68, 'probe_A217007_a7_n67_witness.json',
                'probe_A217007_a7_n68.json'),
    'A217059': ([3, 5],
                [22, 32, 43, 44, 50, 55, 61, 65, 70],
                9, 74, 'probe_A217059_a9_n73.json',
                'probe_A217059_a9_n74.json'),
    'A217236': ([4, 5],
                [55, 71, 75, 79],
                4, 84, 'probe_A217236_a4_n83.json',
                'probe_A217236_a4_n84.json'),
}

_fail = []
_pass = []


def check(name, ok, detail='', fail_detail=''):
    """`detail` is context shown either way; `fail_detail` only on failure.

    An earlier version passed the failure explanation as `detail`, so a PASS
    line cheerfully printed 'quoted certificate differs from the computed one'
    underneath the word PASS.
    """
    (_pass if ok else _fail).append(name)
    extra = detail if ok else (fail_detail or detail)
    print(f'  [{"PASS" if ok else "FAIL"}] {name}{("  " + extra) if extra else ""}',
          flush=True)
    return ok


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def section(t):
    print(f'\n=== {t} ===', flush=True)


def main():
    fast = '--fast' in sys.argv

    section('standalone checkers self-test')
    rc, out = run([PY, 'verify_certificate.py', '--selftest'], VDW)
    check('vdw verify_certificate --selftest', rc == 0 and 'SELFTEST PASSED' in out)
    rc, out = run([PY, 'verify_rank.py', '--selftest'], EC)
    check('ec verify_rank --selftest', rc == 0 and 'SELFTEST PASSED' in out)

    section('each claimed term, re-derived from its own evidence files')
    for seq, (targets, published, jnew, value, wf, rf) in CLAIMS.items():
        wp, rp = os.path.join(VDW, wf), os.path.join(VDW, rf)
        if not (os.path.exists(wp) and os.path.exists(rp)):
            check(f'{seq}: evidence files present', False, f'missing {wf} or {rf}')
            continue
        wit, ref = json.load(open(wp)), json.load(open(rp))

        check(f'{seq}: a({jnew}) is the next unpublished index',
              jnew == len(published))
        check(f'{seq}: refutation is UNSAT at n={value}',
              ref['sat'] is False and ref['n'] == value and ref['j'] == jnew
              and ref['targets'] == targets)
        check(f'{seq}: refutation had every cube report',
              'all' in str(ref.get('via', '')) or ref.get('via') == 'probe',
              str(ref.get('via')))
        check(f'{seq}: witness is SAT at n={value-1}',
              wit['sat'] is True and wit['n'] == value - 1 and wit['j'] == jnew
              and wit['targets'] == targets)

        cert = wit.get('certificate', '')
        check(f'{seq}: certificate length is a({jnew})-1 = {value-1}',
              len(cert) == value - 1, f'len={len(cert)}')
        check(f'{seq}: certificate wildcard count within budget',
              cert.count('.') <= jnew, f'{cert.count(".")}/{jnew}')

        rc, out = run([PY, 'verify_certificate.py', cert, str(jnew)]
                      + [str(t) for t in targets], VDW)
        check(f'{seq}: certificate ACCEPTED by standalone verifier',
              rc == 0 and 'ACCEPTED' in out)

        # a wrong value here is the whole risk, so state the deduction explicitly
        check(f'{seq}: SAT at {value-1} and UNSAT at {value} give a({jnew})={value}',
              wit['sat'] is True and ref['sat'] is False
              and ref['n'] == wit['n'] + 1)

    section('elliptic curve rank certificate')
    best = os.path.join(EC, 'ec_search_best.json')
    if os.path.exists(best):
        rc, out = run([PY, 'verify_rank.py', best], EC)
        m = re.search(r'rank E\(Q\) >= (\d+)', out)
        check('ec certificate ACCEPTED by standalone checker',
              rc == 0 and 'ACCEPTED' in out, m.group(0) if m else '')
        d = json.load(open(best))
        b = d.get('best', d)
        v = b.get('verification', {})
        check('ec reported rank equals the verified rank',
              b['rank_lower_bound'] == v.get('rank_verified', -1),
              f"reported {b['rank_lower_bound']}, verified {v.get('rank_verified')}")
    else:
        check('ec certificate present', False)

    # Which terms the evidence actually supports. Computed HERE, above the prose
    # section, because the prose section used to iterate CLAIMS -- every claimed
    # term -- and demand that each be written up as established, certificate and
    # full extended sequence included. That did not merely fail to catch an
    # overstatement in the public write-up: it REQUIRED one. A217059 was blocked
    # from SUBMIT.md for having no completed family gate, while this gate went on
    # insisting PAPER.md and README.md present it as an established result.
    sys.path.insert(0, ROOT)
    import importlib

    import make_submit_pack
    importlib.reload(make_submit_pack)

    ready, blocked = [], []
    for seq, (targets, published, j, value, wf, rf) in CLAIMS.items():
        wit, ref = make_submit_pack.load(wf), make_submit_pack.load(rf)
        xc, _why = make_submit_pack.crosscheck(seq, targets, j, value)
        gate = make_submit_pack.family_gate(seq, targets, published, j)
        entry = (seq, j, value)
        (ready if (wit and ref and xc and xc.get('AGREES') and gate) else blocked).append(entry)
    blocked_seqs = {seq for seq, _j, _v in blocked}

    section('prose matches evidence')
    # A result that is computed but never written up is not "complete", and an
    # earlier version of this harness skipped any sequence absent from the prose
    # -- so an undocumented result passed silently by not being mentioned.
    # Presence is now required, not assumed.
    for doc in ('PAPER.md', 'README.md'):
        p = os.path.join(ROOT, doc)
        if not os.path.exists(p):
            check(f'{doc} present', False)
            continue
        text = open(p, encoding='utf-8').read()
        for seq, (targets, published, jnew, value, wf, rf) in CLAIMS.items():
            if seq in blocked_seqs:
                continue  # handled by the withheld-term checks below
            if not check(f'{doc}: documents {seq}', seq in text):
                continue
            wit = json.load(open(os.path.join(VDW, wf)))
            cert = wit.get('certificate', '')
            check(f'{doc}: {seq} certificate string matches the JSON',
                  bool(cert) and cert in text, '',
                  'quoted certificate differs from the computed one')
            # Require the whole extended sequence, not a loose mention of the
            # value: that catches a stale published list as well as a wrong new
            # term, and does not depend on how the prose happens to phrase it.
            full = ', '.join(str(t) for t in published + [value])
            check(f'{doc}: {seq} shows the full extended sequence ending {value}',
                  full in text, '', 'extended data line missing or stale')

        # A withheld term must NOT be presented as an established result. The
        # extended data line ending in the new value is the specific thing that
        # asserts it, so either the prose omits that line or it carries an
        # explicit marker beside the sequence saying the term is not established.
        for seq, _j, value in blocked:
            published = CLAIMS[seq][1]
            full = ', '.join(str(t) for t in published + [value])
            marked = any(
                w in text for w in ('withheld', 'withdrawn', 'not established', 'NOT established')
            )
            check(f'{doc}: does not present withheld {seq} as established',
                  (full not in text) or marked, '',
                  f'{seq} is blocked (its evidence is incomplete) but this document '
                  f'states its extended sequence as a result with no withheld marker')


    # SUBMIT.md is the file whose contents are actually pasted into OEIS, and
    # until now nothing here opened it. The gate could therefore print "EVERY
    # CLAIM IN THIS REPOSITORY IS SUPPORTED BY EVIDENCE ON DISK" while SUBMIT.md
    # presented a term as ready whose family gate had never finished -- which is
    # exactly what happened to A217059, through 76 consecutive passes. A gate
    # that does not read the artifact cannot vouch for it.
    section('SUBMIT.md agrees with the evidence')
    submit_path = os.path.join(ROOT, 'SUBMIT.md')
    if not os.path.exists(submit_path):
        check('SUBMIT.md exists', False, fail_detail='run make_submit_pack.py')
    else:
        submit_text = open(submit_path, encoding='utf-8').read()

        # Every section heading offering a term to paste must be a term the
        # evidence actually supports.
        offered = set(re.findall(r'^## (A\d+) — a\(\d+\) = \d+', submit_text, re.M))
        unsupported = sorted(offered - {s for s, _, _ in ready})
        check('SUBMIT.md offers no term the evidence does not support',
              not unsupported,
              f'{len(offered)} term(s) offered',
              fail_detail=f'offered without support: {", ".join(unsupported)} — '
                          f'regenerate with make_submit_pack.py')

        for seq, j, value in blocked:
            check(f'SUBMIT.md does not present blocked {seq} a({j})={value} as ready',
                  f'## {seq} — a({j}) = {value}' not in submit_text,
                  'listed as blocked',
                  fail_detail='it is offered for pasting despite missing evidence')

        for seq, j, value in ready:
            check(f'SUBMIT.md carries the section for {seq} a({j})={value}',
                  f'## {seq} — a({j}) = {value}' in submit_text,
                  fail_detail='evidence supports it but the pack is stale — '
                              'run make_submit_pack.py')

    # The b-file is the DATA that is uploaded to OEIS. The gate checked
    # certificates, prose and SUBMIT.md and never opened one, so the only
    # artifact whose contents literally become the public record was the one
    # thing unverified. Same shape as the SUBMIT.md gap: a chain of checks that
    # stops one link short of the thing that ships.
    #
    # Both directions, because one is not a gate: a READY term's file must exist
    # and match its claim exactly, and a BLOCKED term's file must NOT be sitting
    # there pasteable. The staging folder lives outside the repo, so a clean
    # clone skips this section rather than failing it.
    staging = os.path.join(os.path.expanduser('~'), 'OEIS-upload')
    if not os.path.isdir(staging):
        section('staged b-files (skipped: no staging folder on this machine)')
    else:
        section('staged b-files match the claims')
        ready_seqs = {seq for seq, _j, _v in ready}
        for seq, (targets, published, jnew, value, wf, rf) in CLAIMS.items():
            bpath = os.path.join(staging, f'b{seq[1:]}.txt')
            staged_here = os.path.exists(bpath)

            if seq not in ready_seqs:
                check(f'{seq}: withheld term is NOT staged for upload',
                      not staged_here, 'not staged',
                      fail_detail=f'{bpath} exists but {seq} is blocked - it would be '
                                  f'pasted from a folder that looks ready')
                continue

            if not check(f'{seq}: b-file is staged', staged_here,
                         fail_detail=f'missing {bpath}'):
                continue

            rows = [r.split() for r in
                    open(bpath, encoding='ascii').read().split('\n') if r.strip()]
            got = [(int(a), int(b)) for a, b in rows]
            want = list(enumerate(published + [value], start=jnew - len(published)))
            check(f'{seq}: b-file rows equal the claimed sequence',
                  got == want, f'{len(got)} rows, last a({got[-1][0]})={got[-1][1]}'
                  if got else 'empty',
                  fail_detail=f'b-file disagrees with CLAIMS: got {got[:3]}...{got[-1:]} '
                              f'want {want[:3]}...{want[-1:]}')
            check(f'{seq}: b-file final row is the claimed new term a({jnew})={value}',
                  bool(got) and got[-1] == (jnew, value), '',
                  fail_detail='the uploaded file would not carry the term being claimed')

        # The approval watcher is the one thing that speaks to the operator
        # unprompted, and it does so at the single moment they are most likely to
        # act without re-checking: the instant a term is approved. Its target list
        # is therefore a second place where "what to submit next" is written down,
        # and it drifted -- A217059 was withdrawn from the staging folder and the
        # pack while the watcher kept watching it. Nothing read the two together.
        targets_path = os.path.join(staging, 'watch_targets.json')
        if not os.path.exists(targets_path):
            section('approval watcher targets (skipped: no watch_targets.json)')
        else:
            section('approval watcher targets agree with SUBMIT.md')
            try:
                watch = json.load(open(targets_path, encoding='utf-8'))
            except (ValueError, OSError) as exc:
                watch = None
                check('watch_targets.json parses', False, fail_detail=str(exc))
            if watch is not None:
                blocked_seqs = {seq for seq, _j, _v in blocked}
                watched = {t.get('seq') for t in watch}
                offending = sorted(watched & blocked_seqs)
                check('the watcher tracks no term the pack refuses',
                      not offending, f'{len(watched)} target(s)',
                      fail_detail=f'{", ".join(offending)} is blocked but still in '
                                  f'watch_targets.json - on approval the watcher '
                                  f'would name it as the next thing to submit')
                for t in watch:
                    seq = t.get('seq')
                    claim = CLAIMS.get(seq)
                    check(f'{seq}: watcher target matches the claimed term',
                          claim is not None
                          and (t.get('idx'), t.get('val')) == (claim[2], claim[3]),
                          f"a({t.get('idx')})={t.get('val')}",
                          fail_detail='the watcher would announce approval of a term '
                                      'this repository does not claim')

    # The upper bounds are the half of every result with no self-checking
    # artifact: a colouring proves a lower bound to anyone in milliseconds, but
    # "no colouring exists" is an absence, and until now it rested on a solver
    # saying UNSAT with nothing to replay. drat_certify.py emits a DRAT proof and
    # has drat-trim check it, which shrinks what is trusted to drat-trim plus the
    # encoding audit below -- and the encoding half is audited exhaustively.
    #
    # Symmetry breaking is OFF in those proofs, so the reversal lex-leader
    # argument is not assumed by the thing meant to check it.
    section('DRAT certificate table agrees with the claims')
    sys.path.insert(0, VDW)
    import drat_certify
    importlib.reload(drat_certify)
    for seq, fam in sorted(drat_certify.FAMILIES.items()):
        claim = CLAIMS.get(seq)
        check(f'{seq}: drat_certify published terms match CLAIMS',
              claim is not None and fam['published'] == claim[1]
              and fam['targets'] == claim[0],
              f"{len(fam['published'])} published, targets {fam['targets']}",
              fail_detail='the certifier would certify a different sequence from '
                          'the one this repository claims')

    # Two binaries this repository does not ship. A clean clone and a CI runner
    # both lack them, and neither is a failure: the section skips, loudly.
    ladder = {'A217058': '0-3' if fast else '0-6',
              'A217005': '0-1', 'A217007': '0-1', 'A217236': '0-1'}
    started = False
    for seq, spec in ladder.items():
        rc, out = run([PY, 'drat_certify.py', '--seq', seq, '--ladder', spec,
                       '--json'], VDW)
        if rc == drat_certify.TOOLS_MISSING:
            section('DRAT refutations (skipped: kissat/drat-trim not installed '
                    '- see vdw/DRAT.md)')
            break
        if not started:
            section('DRAT refutations replayed under drat-trim')
            started = True
        try:
            recs = json.loads(out)
        except ValueError:
            recs = None
        if not check(f'{seq}: certifier returned results', bool(recs),
                     fail_detail=out.strip()[-300:]):
            continue
        for r in recs:
            # Anything other than the checker's own VERIFIED line fails. A
            # satisfiable instance reports SAT and fails here too, which is the
            # point: it would mean the upper bound itself is false.
            check(f"{seq}: a({r['j']}) <= {r['n']} refutation is machine-checked",
                  r['verdict'] == 'VERIFIED',
                  f"{r['verdict']}, {r.get('proof_mb', 0)} MB proof checked in "
                  f"{r.get('check_s', 0)} s",
                  fail_detail=r.get('detail', r['verdict']))

    if not fast:
        section('audits re-executed (slow)')
        rc, out = run([PY, 'encoding_audit.py'], VDW)
        check('encoding audit: CNF equals the definition',
              # matched by pattern, not by a hardcoded count: pinning the number
              # here means adding a case to the audit fails this check instead of
              # strengthening it, which is backwards.
              rc == 0 and re.search(r'all \d+ cases pass', out) is not None,
              re.search(r'all \d+ cases pass', out).group(0) if
              re.search(r'all \d+ cases pass', out) else '')
        rc, out = run([PY, 'scale_test.py'], VDW)
        check('scale test: wildcard budget correct at n=55..58, j=12',
              rc == 0 and 'SCALE TEST PASSED' in out)

    print(f'\n{len(_pass)} passed, {len(_fail)} failed')
    if _fail:
        print('\nFAILED:')
        for f in _fail:
            print('  -', f)
        return 1
    print('\nEVERY CLAIM IN THIS REPOSITORY IS SUPPORTED BY EVIDENCE ON DISK.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
