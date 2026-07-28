"""First pass: give every N in the 1994 table an equal slice of basin hopping,
then report where we match, where we fall short, and where we BEAT it."""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from mv_core import REF, basin_hop

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'mv_scan_results.json')


def job(args):
    N, seconds, seed0 = args
    t0 = time.time()
    v, x, it = basin_hop(N, seconds, seed0)
    return N, v, x.tolist(), it, time.time() - t0


if __name__ == '__main__':
    lo, hi, secs = int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3])
    Ns = [n for n in sorted(REF) if lo <= n <= hi]
    tasks = [(N, secs, 20260728 + 977 * N) for N in Ns]
    res = {}
    if os.path.exists(OUT):
        res = json.load(open(OUT))
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=16) as ex:
        for N, v, x, it, dt in ex.map(job, tasks):
            ref = REF[N]
            d = v - ref
            tag = 'BEAT' if d > 1e-10 else ('match' if d > -1e-9 else 'short')
            prev = res.get(str(N))
            if prev is None or v > prev['v']:
                res[str(N)] = {'v': v, 'ref': ref, 'delta': d, 'x': x, 'iters': it}
            print(f'N={N:4d} ref={ref:.12f} ours={v:.12f} delta={d:+.3e} it={it:5d} '
                  f'{dt:5.1f}s  {tag}', flush=True)
            json.dump(res, open(OUT, 'w'))
    print(f'\ntotal {time.time() - t0:.0f}s')
    beat = sorted(int(k) for k, r in res.items() if r['delta'] > 1e-10)
    short = sorted(int(k) for k, r in res.items() if r['delta'] < -1e-9)
    print(f'BEAT ({len(beat)}): {beat}')
    print(f'short({len(short)}): {short}')
