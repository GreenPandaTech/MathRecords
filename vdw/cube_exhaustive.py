"""Machine-check that a cube set is EXHAUSTIVE: the composition argument.

`cube_certify.py` proves, cube by cube, that F + units(C) is unsatisfiable --
so F entails neg(C) for every cube C in the set. That is a pile of proofs, not
a proof: nothing yet says the cubes cover every branch of the search. This
module supplies the missing half, twice over, in two independent forms:

1. AN INDEPENDENT ENUMERATION (pure Python, trusts nothing from make_cubes).
   Walk the FULL (r+1)-ary tree of class-assignment prefixes of length <= k.
   Every node is classified: it is IN the supplied cube set, or it is DROPPED
   because a specific clause already present in build()'s output is falsified
   outright by the prefix's unit assumptions (the clause is located by fresh
   AP-search code and then literally looked up in the clause list), or -- as a
   sound fallback that cannot fire for targets [3,4] at k <= j -- generic unit
   propagation over F reaches a conflict. A full-depth prefix that is none of
   these is a COUNTEREXAMPLE and is named; the check fails.

2. A DRAT COMPOSITION TAIL, replayed by drat-trim. Let F' = F plus the clause
   neg(C) for every cube C (prepending the byte-identical DIMACS body used for
   the per-cube runs -- both artifacts record its SHA256). Since each per-cube
   proof shows F entails neg(C), F and F' have the same models. The tail is a
   post-order collapse of the pruned tree, every lemma RUP: at a dropped node
   p, neg(p) is RUP w.r.t. F alone (the drop clause conflicts under units(p));
   at an internal node, the three child clauses -- cube inputs of F' or earlier
   lemmas -- each unit-propagate NOT v(|p|+1, c) under units(p) and the ALO
   clause for position |p|+1 conflicts; the root lemma is the empty clause.
   drat-trim saying `s VERIFIED` on F' + tail is the machine-checked statement
   that every branch of the assignment tree is killed by a cube clause or by a
   drop refutation, i.e. F' -- hence F -- is UNSAT.

The construction is FAIL-CLOSED against a wrong cube set: a prefix wrongly
dropped yields a tail lemma that is not RUP (drat-trim rejects) and a named
counterexample in the enumeration; a missing cube leaves an internal lemma
non-RUP; a wrongly KEPT cube is merely an extra per-cube obligation.

    python vdw/cube_exhaustive.py --n 45 --j 8 --targets 3 4 --k 6 \
        --cubes vdw/cube_run_n45_j8_k6/results.jsonl

Exit codes: 0 the check passed; 1 it failed (a counterexample is named);
3 drat-trim is not installed (the enumeration alone is not the full check,
so callers SKIP, exactly as with drat_certify.py). `--no-tail` runs just the
enumeration and never returns 3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vdw4 import build, make_cubes                    # noqa: E402
from drat_certify import find_tools, TOOLS_MISSING    # noqa: E402
from cube_certify import dimacs_body, parse_cube      # noqa: E402


# ------------------------------------------------- independent refutation ----

def refuting_ap(prefix, targets):
    """A monochromatic target-length AP lying wholly inside the fixed prefix,
    or None. Fresh code on purpose: this must not call vdw4._has_mono_ap,
    because the point is to check make_cubes' pruning, not repeat it."""
    L = len(prefix)
    for c, t in enumerate(targets, start=1):
        if L < t:
            continue
        for d in range(1, (L - 1) // (t - 1) + 1):
            for a in range(1, L - (t - 1) * d + 1):
                pos = [a + m * d for m in range(t)]
                if all(prefix[i - 1] == c for i in pos):
                    return c, pos
    return None


def unit_propagate(cnf, assumps):
    """Generic UP to fixpoint. Returns ('conflict', clause_index) or
    ('stable', None). Sound: a conflict proves F + assumps unsatisfiable.
    Naive O(rounds * clauses) -- F here is a few thousand clauses and this is
    only a fallback for drop reasons that are not a single falsified clause."""
    assign = {}
    for lit in assumps:
        var, val = abs(lit), lit > 0
        if assign.get(var, val) != val:
            return 'conflict', None
        assign[var] = val
    changed = True
    while changed:
        changed = False
        for idx, cl in enumerate(cnf):
            unit, unassigned, sat = None, 0, False
            for lit in cl:
                val = assign.get(abs(lit))
                if val is None:
                    unassigned += 1
                    unit = lit
                    if unassigned > 1:
                        break
                elif (lit > 0) == val:
                    sat = True
                    break
            if sat or unassigned > 1:
                continue
            if unassigned == 0:
                return 'conflict', idx
            assign[abs(unit)] = unit > 0
            changed = True
    return 'stable', None


# --------------------------------------------------------------- the walk ----

def compose(n, j, targets, k, cube_set, cnf, v):
    """Classify every prefix of the full tree; build the post-order tail.

    Returns (report, lemmas). report['counterexamples'] non-empty means the
    cube set does NOT cover the space and the named prefixes prove it.
    """
    r = len(targets)
    clause_index = {}
    for i, cl in enumerate(cnf):
        clause_index.setdefault(frozenset(cl), i)

    dropped, counterexamples, lemmas = [], [], []
    stats = {'cube': 0, 'dropped_mono_ap': 0, 'dropped_up': 0, 'internal': 0}
    matched = set()

    def neg(p):
        return [-v(i + 1, c) for i, c in enumerate(p)]

    def drop_by_up(p, why_direct_failed):
        units = [v(i + 1, c) for i, c in enumerate(p)]
        st, ci = unit_propagate(cnf, units)
        if st == 'conflict':
            dropped.append({'prefix': list(p), 'reason': 'unit-propagation',
                            'clause': list(cnf[ci]) if ci is not None else None,
                            'clause_index': ci})
            lemmas.append(neg(p))
            stats['dropped_up'] += 1
            return True
        counterexamples.append({'prefix': list(p), 'why': why_direct_failed})
        return False

    def visit(p):
        if p in cube_set:
            stats['cube'] += 1
            matched.add(p)
            return
        ap = refuting_ap(p, targets)
        if ap:
            colour, pos = ap
            clause = [-v(i, colour) for i in pos]
            ci = clause_index.get(frozenset(clause))
            if ci is None:
                counterexamples.append(
                    {'prefix': list(p), 'why': 'refuting AP clause absent from '
                     'build() output', 'clause': clause})
                return
            units = {v(i + 1, c) for i, c in enumerate(p)}
            if not all(-lit in units for lit in clause):
                counterexamples.append(
                    {'prefix': list(p), 'why': 'AP clause not falsified outright '
                     'by the prefix units', 'clause': clause})
                return
            dropped.append({'prefix': list(p), 'reason': 'mono-AP',
                            'colour': colour, 'positions': pos,
                            'clause': clause, 'clause_index': ci})
            lemmas.append(neg(p))
            stats['dropped_mono_ap'] += 1
            return
        if p.count(0) > j:
            # Not a single falsified clause: the totalizer refutes it through
            # propagation. Cannot fire at k <= j; handled soundly anyway.
            drop_by_up(p, 'wildcard budget exceeded but unit propagation '
                          'does not conflict')
            return
        if len(p) == k:
            # Full depth, not a cube, no direct refuting clause. Last chance:
            # a sound UP refutation. Otherwise this prefix is uncovered and
            # the "exhaustive" cube set provably is not.
            drop_by_up(p, 'full-depth prefix neither in the cube set nor '
                          'refuted by the formula')
            return
        for c in range(r + 1):
            visit(p + (c,))
        stats['internal'] += 1
        lemmas.append(neg(p))       # post-order; the root contributes []

    visit(())
    report = {'stats': stats, 'dropped': dropped,
              'counterexamples': counterexamples,
              'unmatched_cubes': [list(c) for c in sorted(cube_set - matched)],
              'tail_lemmas': len(lemmas)}
    return report, lemmas


# --------------------------------------------------------------- the tail ----

def check_tail(body, nvars, nclauses, cube_set, lemmas, v, drat_trim,
               workdir, timeout=None):
    """Write F' (the SAME formula bytes plus one neg(C) clause per cube) and
    the tail proof; have drat-trim replay it. Only its literal 's VERIFIED'
    line counts."""
    cube_clauses = [[-v(i + 1, c) for i, c in enumerate(cb)]
                    for cb in sorted(cube_set)]
    fprime = os.path.join(workdir, 'fprime.cnf')
    tail = os.path.join(workdir, 'tail.drat')
    with open(fprime, 'w', encoding='ascii', newline='\n') as fh:
        fh.write(f'p cnf {nvars} {nclauses + len(cube_clauses)}\n')
        fh.write(body)
        fh.write('\n')
        fh.write('\n'.join(' '.join(map(str, c)) + ' 0' for c in cube_clauses))
        fh.write('\n')
    with open(tail, 'w', encoding='ascii', newline='\n') as fh:
        fh.write('\n'.join(' '.join(map(str, lem)) + ' 0' if lem else '0'
                           for lem in lemmas))
        fh.write('\n')

    t0 = time.time()
    chk = subprocess.run([drat_trim, fprime, tail],
                         capture_output=True, text=True, timeout=timeout)
    secs = round(time.time() - t0, 2)
    out = chk.stdout or ''
    if 's VERIFIED' in out:
        verdict = 'VERIFIED'
    elif 's NOT VERIFIED' in out:
        verdict = 'NOT_VERIFIED'
    else:
        verdict = 'CHECKER_ERROR'
    return {'verdict': verdict, 'check_s': secs,
            'fprime_clauses': nclauses + len(cube_clauses),
            'tail_lemmas': len(lemmas),
            'detail': None if verdict == 'VERIFIED' else out.strip()[-400:]}


# ------------------------------------------------------------------ driver ----

def load_cubes(path, k, expect_sha=None):
    """A JSON list of cubes, or a results.jsonl from cube_certify. Returns
    (cubes, nonverified_count_or_None, foreign_count_or_None).

    A record is only evidence for THIS formula if it was proved against it, so
    the caller passes the formula hash and a record carrying a different
    `formula_sha256` is counted foreign and treated as not discharged. Without
    that check the composition would happily compose refutations of a
    different problem."""
    with open(path, encoding='ascii') as fh:
        text = fh.read()
    if path.endswith('.jsonl'):
        cubes = {}
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if 'cube' in rec:
                cubes[tuple(rec['cube'])] = rec
        foreign = None
        if expect_sha is not None:
            foreign = sum(1 for r in cubes.values()
                          if r.get('formula_sha256') != expect_sha)
        nonverified = sum(
            1 for r in cubes.values()
            if r.get('verdict') != 'VERIFIED'
            or (expect_sha is not None
                and r.get('formula_sha256') != expect_sha))
        return list(cubes), nonverified, foreign
    data = json.loads(text)
    return [tuple(c) for c in data], None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--n', type=int, required=True)
    ap.add_argument('--j', type=int, required=True)
    ap.add_argument('--targets', type=int, nargs='+', required=True)
    ap.add_argument('--k', type=int, required=True)
    ap.add_argument('--cubes', metavar='FILE',
                    help='cube set to check: JSON list or cube_certify '
                         'results.jsonl (default: the make_cubes claim -- fine, '
                         'the walk does not trust it either way)')
    ap.add_argument('--drop-cube', metavar='CUBE',
                    help='NEGATIVE CONTROL: delete this cube from the set '
                         'first; the check must then FAIL naming it')
    ap.add_argument('--out', metavar='FILE',
                    help='certificate JSON (default '
                         'vdw/cube_run_n{n}_j{j}_k{k}/exhaustive_cert.json)')
    ap.add_argument('--no-tail', action='store_true',
                    help='skip the drat-trim composition tail (enumeration only)')
    ap.add_argument('--timeout', type=float)
    ap.add_argument('--kissat')            # accepted for symmetry; unused
    ap.add_argument('--drat-trim', dest='drat_trim')
    args = ap.parse_args()

    # One build; the body string is byte-for-byte what cube_certify writes as
    # the F part of every per-cube file (both record its SHA256, so the claim
    # "same formula" is checkable, not asserted).
    cnf, pool, v = build(args.n, args.j, args.targets,
                         symbreak=False, revsym=False)
    body, nvars, nclauses = dimacs_body(cnf), pool.top, len(cnf)
    sha = hashlib.sha256(body.encode('ascii')).hexdigest()

    r = len(args.targets)
    foreign = None
    if args.cubes:
        cubes, nonverified, foreign = load_cubes(args.cubes, args.k, sha)
        source = args.cubes
        if foreign:
            print(f'warning: {foreign} record(s) in {args.cubes} were proved '
                  f'against a DIFFERENT formula and do not count as '
                  f'discharged', file=sys.stderr)
    else:
        cubes, nonverified = make_cubes(args.n, args.j, args.targets, args.k), None
        source = 'make_cubes (claimed set; the walk below does not trust it)'
    for c in cubes:
        if len(c) != args.k or not all(0 <= x <= r for x in c):
            raise SystemExit(f'malformed cube {c}: expected {args.k} classes in 0..{r}')
    cube_set = set(map(tuple, cubes))

    if args.drop_cube:
        victim = parse_cube(args.drop_cube, args.k)
        if victim not in cube_set:
            raise SystemExit(f'--drop-cube {victim}: not in the cube set')
        cube_set.discard(victim)
        print(f'NEGATIVE CONTROL: removed cube {list(victim)} -- this check '
              f'must now FAIL')

    drat_trim = None
    if not args.no_tail:
        tools, missing = find_tools(args.kissat, args.drat_trim)
        if 'drat_trim' not in tools:
            print('drat-trim not installed; the composition tail cannot be '
                  'checked. Nothing was verified. See vdw/DRAT.md '
                  '(or pass --no-tail for the enumeration alone).',
                  file=sys.stderr)
            return TOOLS_MISSING
        drat_trim = tools['drat_trim']

    t0 = time.time()
    report, lemmas = compose(args.n, args.j, args.targets, args.k,
                             cube_set, cnf, v)
    walk_s = round(time.time() - t0, 2)

    cube_sha = hashlib.sha256(
        json.dumps(sorted(map(list, cube_set))).encode('ascii')).hexdigest()
    cert = {'n': args.n, 'j': args.j, 'targets': args.targets, 'k': args.k,
            'symbreak': False, 'revsym': False,
            'formula': {'vars': nvars, 'clauses': nclauses,
                        'body_sha256': sha},
            'cube_source': source, 'cube_count': len(cube_set),
            'cube_set_sha256': cube_sha,
            'cube_results_nonverified': nonverified,
            'cube_results_foreign_formula': foreign,
            'walk_s': walk_s, **report,
            'meaning': 'exhaustiveness/composition ONLY: every branch of the '
                       'full assignment tree is a cube or refuted by the '
                       'formula. The per-cube UNSAT obligations are separate '
                       '(cube_certify.py results with matching '
                       'formula_sha256).',
            'generated_utc': datetime.now(timezone.utc).isoformat(timespec='seconds')}

    failed = bool(report['counterexamples'])
    if failed:
        first = report['counterexamples'][0]
        print(f'EXHAUSTIVENESS FAILED: {len(report["counterexamples"])} '
              f'uncovered prefix(es); first counterexample '
              f'{first["prefix"]}: {first["why"]}')
        cert['verdict'] = 'FAIL'
        cert['tail'] = {'verdict': 'SKIPPED',
                        'detail': 'enumeration already failed'}
    else:
        s = report['stats']
        print(f'walk: {s["cube"]} cubes matched, '
              f'{s["dropped_mono_ap"]} mono-AP drops, '
              f'{s["dropped_up"]} UP drops, {s["internal"]} internal nodes, '
              f'{report["tail_lemmas"]} tail lemmas ({walk_s}s)')
        if report['unmatched_cubes']:
            print(f'note: {len(report["unmatched_cubes"])} supplied cube(s) '
                  f'sit under dropped nodes (harmless: extra obligations)')
        if args.no_tail:
            cert['verdict'] = 'PASS_ENUMERATION_ONLY'
            cert['tail'] = {'verdict': 'SKIPPED', 'detail': '--no-tail'}
        else:
            with tempfile.TemporaryDirectory(prefix='cube_tail_') as wd:
                tail = check_tail(body, nvars, nclauses, cube_set, lemmas, v,
                                  drat_trim, wd, args.timeout)
            cert['tail'] = tail
            print(f'composition tail: {tail["verdict"]} '
                  f'({tail["tail_lemmas"]} lemmas over '
                  f'{tail["fprime_clauses"]} F\' clauses, {tail["check_s"]}s)')
            failed = tail['verdict'] != 'VERIFIED'
            # PASS means the theorem is composed, which needs BOTH halves: the
            # tree is exhaustive AND every cube's UNSAT obligation is
            # discharged against this same formula. Reporting PASS while cubes
            # are outstanding would let a caller read "composed" as "proved".
            if failed:
                cert['verdict'] = 'FAIL'
            elif nonverified:
                cert['verdict'] = 'PASS_COMPOSITION_ONLY'
            else:
                cert['verdict'] = 'PASS'

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f'cube_run_n{args.n}_j{args.j}_k{args.k}', 'exhaustive_cert.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='ascii', newline='\n') as fh:
        json.dump(cert, fh, indent=1)
    print(f'certificate: {out_path} (verdict {cert["verdict"]})')
    if nonverified:
        print(f'warning: {nonverified} cube(s) in {source} are not VERIFIED '
              f'against this formula -- exhaustiveness holds for the SET, but '
              f'the per-cube obligations are not all discharged, so this is '
              f'NOT yet a proof')
    return 1 if (failed or nonverified) else 0


if __name__ == '__main__':
    sys.exit(main())
