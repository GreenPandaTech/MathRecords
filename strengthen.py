#!/usr/bin/env python3
"""Bring every established term to the same standard of evidence.

Why this exists. A217058 was the first result, and its extra refutations were run
by hand before cross_check.py existed. So the harness holds no crosscheck_a12.json
for it, while A217005, A217007 and A217059 each have three confirmed refutation
paths recorded (the original, vdw2 with no symmetry breaking, and vdw4 with
reversal symmetry disabled). PAPER.md section 5.4 shows A217058's third path was
attempted with Cadical300 at k=5 and STOPPED AFTER 7.4 HOURS WITHOUT FINISHING.

The consequence is uncomfortable and worth stating plainly: the term that has been
described as the strongest is, by recorded paths, the weakest of the four. It has
two complete refutations where the others have three, and no machine-checkable
verdict file at all. That is an artefact of the order things were built in, not of
the mathematics -- but "we did it carefully at the time" is exactly the kind of
claim this project refuses to accept elsewhere, so it should not be accepted here.

This runs the missing cross-check with the settings that actually terminate
(Cadical195, k=4 -- the defaults now), and waits for the machine to be free first
so it cannot oversubscribe the box while the overnight programme is still working.

Usage:  python strengthen.py
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
VDW = os.path.join(HERE, 'vdw')
LOGS = os.path.join(HERE, 'logs')
PY = sys.executable
STATUS = os.path.join(HERE, 'STRENGTHEN_STATUS.md')

# (label, n_unsat, n_witness, j, targets)
QUEUE = [
    ('A217058 a(12)=57', 57, 56, 12, [3, 4]),
]

_lines = []


def say(msg):
    line = f'[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}'
    print(line, flush=True)
    _lines.append(line)
    with open(STATUS, 'w', encoding='utf-8') as f:
        f.write('# Evidence-parity run\n\nLast update: **'
                f'{datetime.now():%Y-%m-%d %H:%M:%S}**\n\n```\n'
                + '\n'.join(_lines[-200:]) + '\n```\n')


def solvers_busy():
    ps = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "(Get-CimInstance Win32_Process -Filter \"Name='python3.13.exe' OR "
         "Name='python.exe'\" | Where-Object { $_.CommandLine -match "
         "'cross_check|vdw_probe|multiprocessing|spawn_main' }).Count"],
        capture_output=True, text=True)
    try:
        return int((ps.stdout or '0').strip() or 0)
    except ValueError:
        return 0


def wait_free(label):
    warned = False
    while True:
        n = solvers_busy()
        if n == 0:
            if warned:
                say(f'  machine free; starting {label}')
            return
        if not warned:
            say(f'  queued behind {n} running solver process(es); waiting rather than '
                f'oversubscribing (this box has frozen twice from exactly that)')
            warned = True
        time.sleep(180)


def git(*a):
    return subprocess.run(['git'] + list(a), cwd=HERE, capture_output=True, text=True)


def bank(msg):
    git('add', '-A')
    git('commit', '-q', '-m', msg)
    p = git('push')
    say('  banked and pushed' if p.returncode == 0 else '  push failed (committed locally)')


def main():
    say('Evidence-parity run: giving A217058 the same three-path cross-check the '
        'other three terms already have.')
    for label, n_unsat, n_wit, j, targets in QUEUE:
        out = os.path.join(VDW, f'crosscheck_a{j}.json')
        if os.path.exists(out):
            d = json.load(open(out))
            say(f'{label}: already has a verdict, AGREES={d.get("AGREES")}')
            continue
        wait_free(label)
        say(f'{label}: running vdw2 (no symmetry breaking) + vdw4 no-revsym + witness, '
            f'Cadical195 k=4')
        cmd = [PY, 'cross_check.py', str(n_unsat), str(n_wit), str(j)] \
            + [str(t) for t in targets] + ['--workers', '4']
        logp = os.path.join(LOGS, f'xcheck_{label.split()[0]}.log')
        with open(logp, 'a', encoding='utf-8') as fh:
            fh.write(f'\n===== {datetime.now():%Y-%m-%d %H:%M:%S} :: parity run\n')
            fh.flush()
            rc = subprocess.run(cmd, cwd=VDW, stdout=fh,
                                stderr=subprocess.STDOUT).returncode
        if not os.path.exists(out):
            say(f'{label}: produced no verdict file (exit {rc}). Its existing two '
                f'complete refutations from PAPER.md still stand; this term simply '
                f'does not gain the third. Not a reason to withhold it.')
            bank(f'parity: {label} cross-check produced no verdict, existing evidence stands')
            continue
        d = json.load(open(out))
        if d.get('AGREES'):
            say(f'{label}: AGREES -- now at the same standard as the other three')
            bank(f'parity: A217058 a(12)=57 cross-check AGREES, all four terms now '
                 f'carry three confirmed refutation paths')
        else:
            say(f'*** {label}: DISAGREES. This is the first result and the one most '
                f'relied upon. DO NOT SUBMIT IT. Evidence: vdw/crosscheck_a{j}.json')
            bank(f'parity: *** A217058 CROSS-CHECK DISAGREES -- DO NOT SUBMIT ***')
            return 2
    say('Parity run complete.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
