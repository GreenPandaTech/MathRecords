"""Keep the per-cube certification run alive until it finishes, unattended.

The run this guards is hours long and the machine it runs on has already shown
two ways to lose it: a harness task-kill that took the whole process tree, and
a reboot. `cube_certify.py` is resumable, so a death costs wall-clock and
nothing else -- but only if something notices and restarts it. That is this.

It is deliberately dumb and fail-safe:

  * it only ever STARTS the certifier, never kills anything (there are other
    long-lived python processes on this box that must not be touched);
  * it relaunches through WMI, so the child is parented to the WMI service and
    survives whatever happens to this watchdog's own tree;
  * it decides "alive" by inspecting processes, never by reading a status file
    -- a status file saying `running` is a claim written by something that may
    since have died, which is exactly how the first run was lost;
  * a SAT verdict stops everything immediately and loudly. SAT would mean the
    published term is FALSE, which is the single most important thing this
    machinery could ever discover, so it must never be retried past.

On success it runs the exhaustiveness check and writes a one-file verdict the
operator can read at a glance without reconstructing any of this.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RUN_DIR = os.path.join(HERE, 'cube_run_n57_j12_k8')
STATUS = os.path.join(RUN_DIR, 'status.json')
RESULTS = os.path.join(RUN_DIR, 'results.jsonl')
LOG = os.path.join(HERE, 'cube_watchdog.log')
VERDICT = os.path.join(REPO, 'HEADLINE_CERTIFICATION_RESULT.txt')

N, J, K = 57, 12, 8
TARGETS = ['3', '4']
WORKERS = '3'
# Read from the environment like every other tool script here. This repository
# is public and one machine's directory layout is no use to a reader; the
# launcher (gitignored, machine-local) supplies the real paths.
KISSAT = os.environ.get('KISSAT', 'kissat')
DRAT_TRIM = os.environ.get('DRAT_TRIM', 'drat-trim')
POLL_S = 120
MAX_HOURS = 12.0
# A relaunch storm means the certifier is dying instantly for a reason a
# restart cannot fix (missing binary, bad args). Stop and say so rather than
# spin for hours pretending to work.
MAX_RESTARTS = 200


def log(msg):
    line = f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8', newline='\n') as fh:
        fh.write(line + '\n')


def ps(script):
    """Run PowerShell and return stdout, or '' if it fails. The watchdog must
    never die because a probe hiccuped."""
    try:
        r = subprocess.run(['powershell.exe', '-NoProfile', '-Command', script],
                           capture_output=True, text=True, timeout=60)
        return (r.stdout or '').strip()
    except Exception as exc:                      # noqa: BLE001
        log(f'probe failed (treated as unknown): {exc}')
        return ''


def certifier_alive():
    """True only if a PYTHON process is running the certifier.

    The name filter is load-bearing, not tidiness: the PowerShell process that
    runs this very query has 'cube_certify' inside its own command line, so a
    match on CommandLine alone matches the probe itself and reports 'alive'
    forever -- a watchdog that can never fire, failing exactly when needed.
    Interpreter is python3.13.exe here, so match python* rather than an exact
    name."""
    out = ps("(Get-CimInstance Win32_Process | Where-Object { "
             "$_.Name -like 'python*' -and "
             "$_.CommandLine -like '*cube_certify*' } | Measure-Object).Count")
    try:
        return int(out) > 0
    except ValueError:
        return False                              # unknown -> assume dead, restart is safe


BAT = os.path.join(HERE, 'run_certify.bat')


def launch():
    """Start the certifier parented to the WMI service, outside every tree.

    The command is a .bat rather than an inline string on purpose: an inline
    command has to survive PowerShell -> WMI -> cmd quoting, and when it does
    not, WMI still reports success while cmd dies with "The system cannot find
    the path specified" -- a silent no-op inside the very thing meant to
    guarantee the run. One file, one level of quoting, nothing to escape."""
    out = ps(f"$r = ([wmiclass]'Win32_Process').Create('cmd.exe /c \"{BAT}\"'); "
             f"Write-Output \"$($r.ReturnValue) $($r.ProcessId)\"")
    log(f'launch -> {out or "no response"}')


def read_status():
    try:
        with open(STATUS, encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:                             # noqa: BLE001
        return {}


def count_results():
    """Verdict census straight from the append-only record -- the status file
    is a summary written by a process that may have died mid-update."""
    counts, seen = {}, {}
    try:
        with open(RESULTS, encoding='ascii') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue                      # torn final line of a killed run
                if 'cube' in rec:
                    seen[tuple(rec['cube'])] = rec.get('verdict')
    except FileNotFoundError:
        return {}, 0
    for v in seen.values():
        counts[v] = counts.get(v, 0) + 1
    return counts, len(seen)


def finish(total):
    """Run the exhaustiveness check and write the operator-facing verdict."""
    log('all cubes verified; running the exhaustiveness composition')
    env = dict(os.environ, KISSAT=KISSAT, DRAT_TRIM=DRAT_TRIM)
    cmd = [sys.executable, os.path.join(HERE, 'cube_exhaustive.py'),
           '--n', str(N), '--j', str(J), '--targets', *TARGETS, '--k', str(K),
           '--cubes', RESULTS]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO,
                           env=env, timeout=3600)
        out, rc = (r.stdout or '') + (r.stderr or ''), r.returncode
    except Exception as exc:                      # noqa: BLE001
        out, rc = f'exhaustiveness check failed to run: {exc}', 99
    log(f'exhaustiveness rc={rc}')

    ok = rc == 0
    with open(VERDICT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('HEADLINE CERTIFICATION -- a(12) = 57 of A217058\n')
        fh.write('=' * 52 + '\n\n')
        fh.write(f'finished: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
        fh.write(f'instance: n={N}, j={J}, targets={TARGETS}, cube depth k={K}\n')
        fh.write(f'cubes:    {total}, every one refuted and DRAT-checked\n\n')
        if ok:
            fh.write('RESULT: CERTIFIED.\n\n'
                     'Every cube of the search space carries a DRAT refutation\n'
                     'replayed by drat-trim, and the composition proof shows the\n'
                     'cube set is exhaustive -- so the upper bound a(12) <= 57 is\n'
                     'machine-checked, not solver-asserted. With the checkable\n'
                     'n=56 colouring for the lower bound, a(12) = 57.\n\n'
                     'PAPER.md section 7 may now be rewritten -- and ONLY now.\n')
        else:
            fh.write('RESULT: NOT CERTIFIED. Do not change PAPER.md.\n\n'
                     'The per-cube proofs completed but the composition check\n'
                     'did not pass. Read the output below before believing any\n'
                     'part of this.\n')
        fh.write('\n--- exhaustiveness output ---\n')
        fh.write(out[-4000:])
    log(f'verdict written: {VERDICT}')


def main():
    t0 = time.time()
    restarts = 0
    log(f'watchdog up (poll {POLL_S}s, max {MAX_HOURS}h, max {MAX_RESTARTS} restarts)')

    while True:
        if time.time() - t0 > MAX_HOURS * 3600:
            log('max hours reached; stopping (the run itself is untouched)')
            return 0

        counts, done = count_results()
        # Distinguish a failed PROOF from a failed PROCESS. NOT_VERIFIED means
        # drat-trim rejected a refutation -- a real mathematical problem, stop
        # and let a human look. SOLVER_ERROR and TIMEOUT mean a worker died or
        # ran long (a kill, an OOM, a reboot); those cubes simply have no
        # verdict yet and cube_certify re-runs anything not VERIFIED, so
        # halting on them would strand the run on an operational hiccup.
        fatal = {k: v for k, v in counts.items()
                 if k not in ('VERIFIED', 'SOLVER_ERROR', 'TIMEOUT', None)}
        retryable = sum(v for k, v in counts.items()
                        if k in ('SOLVER_ERROR', 'TIMEOUT'))
        total = read_status().get('total_cubes')

        if counts.get('SAT'):
            log('*** SAT CUBE -- THE PUBLISHED TERM WOULD BE FALSE. STOPPING. ***')
            with open(VERDICT, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write('*** STOP: a cube came back SAT ***\n\n'
                         'A satisfying assignment inside the search space means\n'
                         'the upper bound is NOT valid and the published term\n'
                         f'a(12)=57 would be wrong. Inspect {RESULTS} for the\n'
                         'SAT record before doing anything else. Nothing was\n'
                         'certified and PAPER.md must not be touched.\n')
            return 2

        if fatal:
            log(f'FAILED PROOF verdict present: {fatal} -- stopping; a '
                f'rejected refutation is not something a restart can fix')
            return 1

        if total and counts.get('VERIFIED', 0) >= total:
            finish(total)
            return 0

        if not certifier_alive():
            restarts += 1
            if restarts > MAX_RESTARTS:
                log(f'{restarts} restarts without finishing; giving up so this '
                    f'does not spin silently')
                return 1
            log(f'certifier not running ({done}/{total or "?"} recorded) '
                f'-- relaunch #{restarts}')
            launch()
            time.sleep(30)
        else:
            extra = f' ({retryable} to retry)' if retryable else ''
            log(f'alive: {counts.get("VERIFIED", 0)}/{total or "?"} '
                f'verified{extra}')

        time.sleep(POLL_S)


if __name__ == '__main__':
    sys.exit(main())
