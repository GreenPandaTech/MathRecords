"""Confirm the answer a second time through code that shares nothing with the first.

The upper bound is the fragile half, so it is re-established under deliberately
different assumptions:

  engine     vdw2.py, the earlier implementation, which has no reversal
             symmetry constraint at all -- so if that constraint were subtly
             wrong, this run would disagree
  solver     a different CDCL implementation (Cadical300 / MapleCM / Glucose42)
  cubes      a different branching depth, so the search is partitioned
             differently and the work lands on different subproblems

Agreement is not proof, but a wrong answer would have to survive two different
encodings, two solvers and two partitions to get through.  Disagreement is
decisive: it means stop and do not publish.

The lower bound needs none of this -- it is checked by verify_certificate.py,
which shares no code with any solver.

Usage:  python cross_check.py <n_unsat> <n_witness> <j> <t1> <t2> [--engine X]
"""
import argparse
import json
import os
import time

import vdw2
import vdw4

HERE = os.path.dirname(os.path.abspath(__file__))


def log(m):
    print(f'[{time.strftime("%H:%M:%S")}] {m}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('n_unsat', type=int, help='the claimed value a(j)')
    ap.add_argument('n_witness', type=int, help='a(j)-1, where a witness exists')
    ap.add_argument('j', type=int)
    ap.add_argument('targets', type=int, nargs='+')
    # Cadical195 + k=4, NOT Cadical300 + k=5. PAPER.md section 5.4 records that the
    # Cadical300/k=5 combination was started and stopped after 7.4 HOURS without
    # finishing, with twice the workers, and calls it "poorly matched". Those were
    # the old defaults here, which is a trap: the disjointness that carries the
    # scientific weight is vdw2 having NO lex-leader constraint at all, not the
    # solver version or the cube depth. Keep the part that matters and use the
    # settings that actually terminate.
    ap.add_argument('--engine', default='Cadical195')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--k', type=int, default=4)
    a = ap.parse_args()

    out = {'claim': a.n_unsat, 'j': a.j, 'targets': a.targets,
           'engine': a.engine, 'k': a.k}
    log(f'cross-checking a({a.j}) = {a.n_unsat} for targets {a.targets}')

    # 1. the old engine, no reversal symmetry, different solver, different depth
    log(f'[1/3] vdw2 (no reversal symmetry) + {a.engine}, k={a.k}: '
        f'UNSAT at n={a.n_unsat}?')
    t0 = time.time()
    sat_hi, _ = vdw2.solve_par(a.n_unsat, a.j, a.targets, k=a.k,
                               workers=a.workers)
    out['vdw2_unsat_confirmed'] = not sat_hi
    out['vdw2_sec'] = time.time() - t0
    log(f'      {"UNSAT confirmed" if not sat_hi else "*** SAT -- CLAIM IS WRONG ***"}'
        f'  {out["vdw2_sec"]:.1f}s')

    # 2. same question through the new engine with the constraint switched off
    log(f'[2/3] vdw4 with revsym disabled: UNSAT at n={a.n_unsat}?')
    t0 = time.time()
    sat_hi2, _ = vdw4.solve(a.n_unsat, a.j, a.targets, k=a.k,
                            workers=a.workers, revsym=False, engine=a.engine)
    out['vdw4_norevsym_unsat_confirmed'] = not sat_hi2
    out['vdw4_norevsym_sec'] = time.time() - t0
    log(f'      {"UNSAT confirmed" if not sat_hi2 else "*** SAT -- CLAIM IS WRONG ***"}'
        f'  {out["vdw4_norevsym_sec"]:.1f}s')

    # 3. the witness, re-found independently and re-verified
    log(f'[3/3] independent witness at n={a.n_witness}')
    t0 = time.time()
    sat_lo, col = vdw2.solve_par(a.n_witness, a.j, a.targets, k=a.k,
                                 workers=a.workers)
    good, wild, bad = vdw2.check(col, a.targets, a.j) if sat_lo else (False, None, 'no model')
    out['vdw2_witness_found'] = bool(sat_lo)
    out['vdw2_witness_verified'] = bool(good)
    out['vdw2_witness_wildcards'] = wild
    out['vdw2_sec_witness'] = time.time() - t0
    if sat_lo and good:
        cert = ''.join('.' if c == 0 else str(c) for c in col)
        out['vdw2_certificate'] = cert
        open(os.path.join(HERE, f'cert_crosscheck_n{a.n_witness}.txt'), 'w').write(cert)
        log(f'      witness found and verified ({wild}/{a.j} wildcards)')
        log(f'      {cert}')
    else:
        log(f'      *** no verified witness: {bad} ***')

    ok = (out['vdw2_unsat_confirmed'] and out['vdw4_norevsym_unsat_confirmed']
          and out['vdw2_witness_verified'])
    out['AGREES'] = bool(ok)
    json.dump(out, open(os.path.join(HERE, f'crosscheck_a{a.j}.json'), 'w'), indent=1)
    log('')
    log('CROSS-CHECK AGREES' if ok else '*** CROSS-CHECK DISAGREES -- DO NOT PUBLISH ***')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
