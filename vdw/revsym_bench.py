"""Does reversal symmetry breaking actually pay on the A217058 family?

vdw2 ran these instances with no symmetry breaking at all (its colour-swap rule
is vacuous when the targets differ, as they do for [3,4]).  This measures the
same UNSAT instances with the reversal lex constraint off and on, everything
else held fixed, so the number is attributable.

Also sweeps worker count, because the machine has 16 logical but ~8 physical
cores and only ~6 GB free: 16 concurrent CaDiCaLs is what was exhausting RAM
and orphaning workers.
"""
import time

from vdw4 import solve

CASES = [(45, 8, [3, 4]), (48, 9, [3, 4])]
CONFIGS = [
    ('revsym=OFF w=8  k=4', dict(revsym=False, workers=8,  k=4)),
    ('revsym=ON  w=8  k=4', dict(revsym=True,  workers=8,  k=4)),
    ('revsym=ON  w=8  k=6', dict(revsym=True,  workers=8,  k=6)),
    ('revsym=ON  w=14 k=6', dict(revsym=True,  workers=14, k=6)),
]

if __name__ == '__main__':
    for n, j, tg in CASES:
        print(f'\n=== n={n} j={j} targets={tg}  (published UNSAT) ===', flush=True)
        base = None
        for label, kw in CONFIGS:
            t0 = time.time()
            ok, _ = solve(n, j, tg, **kw)
            dt = time.time() - t0
            if base is None:
                base = dt
            print(f'  {label:22s} {"SAT" if ok else "UNSAT":6s} {dt:8.1f}s  '
                  f'speedup x{base/dt:4.2f}', flush=True)
            assert not ok, 'expected UNSAT -- published value contradicted'
