# MathRecords — technical design

Derived from the code, not from the README. Where the two disagree the code wins
and this file follows the code. Requirements: [PRD.md](PRD.md).

## Two layers, and the boundary between them

The **solver layer** decides one instance `(n, j, targets)` at a time and writes
an evidence file for each decision: the verdict, the parameters, the timings,
and — for a satisfiable instance — the colouring and its verified certificate
string. It never writes prose and never decides what the repository claims.

The **claims layer** reads only those files. `verify_all.py` holds one table,
`CLAIMS`, mapping each sequence to its targets, its published terms, and the two
evidence files that establish the new one. Every number that reaches a human —
the prose, the submission pack, the staged upload files — is read out of the
evidence, so a hand-typed digit has nowhere to enter.

The consequence worth naming: this project has no database and no users, but it
does have a single mutable source of truth, artefacts derived from it, and a gate
whose only job is to detect derived artefacts drifting away from it. Those are
migration problems in a different costume, and they failed in the same ways.

## What stops the derived artefacts drifting

There are no schema migrations. This table is the equivalent, and **each arrow
broke at least once before it was gated**.

| Derived from `CLAIMS` | Mechanism | What stops the drift |
|---|---|---|
| `make_submit_pack.CLAIMS` | `exec` of the literal source slice | cannot differ by construction |
| `drat_certify.FAMILIES` | independent table | gate compares targets and published terms against `CLAIMS` |
| `vdw_run.FAM` | independent table, used only to launch runs | not authoritative; nothing downstream reads it |
| `PAPER.md`, `README.md` | hand-written prose | gate requires each unblocked sequence, its exact certificate string, and its full extended data line to appear verbatim |
| `SUBMIT.md` | generated | gate parses its headings: no unsupported term offered, no blocked term offered, every ready term present |
| staged `b<seq>.txt` | generated | gate compares every row against `CLAIMS`, both directions — a ready term must be staged and match, a blocked term must **not** be staged |
| `~/OEIS-upload/watch_targets.json` | hand-edited | gate fails if the watcher tracks a term the pack refuses |
| staged comment text | `tools/sync_from_submit.py` | regenerated from `SUBMIT.md`; refuses to write if a certificate ever differs |

`make_submit_pack.py` does not restate the claims table — it `exec`s the literal
slice of `verify_all.py`'s source, so the two cannot disagree. `drat_certify.py`
keeps its own convenience table, and the gate compares it against `CLAIMS` rather
than trusting it.

## The files are the schema

There are no tables. The persistent state is files.

| Artefact | Written by | Read by | Shape |
|---|---|---|---|
| `vdw/probe_<tag>.json` | `vdw_probe.py` | gate, pack | `n, j, targets, sat, sec, via, workers, k, engine, revsym, finished` |
| — when `sat` is true, additionally | | | `witness_verified, wildcards, colouring[], certificate` |
| `vdw/cert_<tag>.txt` | `vdw_probe.py` | humans, `verify_certificate.py` | the certificate string alone, alphabet `{., 1, 2}` |
| `vdw/crosscheck_a<j>[_t<t1>-<t2>].json` | `cross_check.py` | gate, pack | `claim, j, targets, engine, k, vdw2_unsat_confirmed, vdw4_norevsym_unsat_confirmed, vdw2_witness_*, AGREES` |
| `vdw/validate_*.json` | `vdw_validate.py` | pack (family gate) | list of `seq, targets, j, w, sat_at_w_minus_1, witness_verified, unsat_at_w, certificate, colouring[], PASS` |
| `vdw/probe_*gate*.json` | `vdw_probe.py` | pack (family gate) | a probe pair: SAT at `w-1`, UNSAT at `w` |
| `vdw/state_<seq>.json`, `result_<seq>.json` | `vdw_run.py` | itself, on restart | checkpoint: every decided `n`, its verdict, and the best colouring so far |
| `SUBMIT.md` | `make_submit_pack.py` | operator, gate, `sync_from_submit.py` | one `## <seq> — a(j) = v` section per ready term, five numbered paste blocks each |
| `b<seq>.txt` | `make_submission.py` | OEIS, gate | ASCII `index value` rows, LF, trailing newline |
| `~/OEIS-upload/` | staging | gate (if present) | b-files, `watch_targets.json`, generated comment text — **outside the repository, never committed** |

One field is null on rows predating a change, and it is a sharp one. Cross-check
verdicts were first written as `crosscheck_a<j>.json`, keyed by term index alone.
A term index is not unique across the family — `j = 7` is shared by A217007,
A217008 and A217060, and `j = 4` by A217236 and A217237 — so a file at the
expected path may belong to a different sequence entirely, and would silently
have vouched for this one.

The newer name carries the targets. `make_submit_pack.crosscheck()` tries the
qualified name first, then the legacy one, and in both cases validates the
record's own `j`, `targets` and `claim` against the claim being checked rather
than trusting it for sitting at the right path. Legacy files are read; they are
not believed.

## Interfaces

```python
vdw4.build(n, j, targets, symbreak=True, revsym=True) -> (cnf, pool, v)
```
CNF for "some legal colouring of `[1,n]` exists": exactly-one class per position,
no monochromatic AP of each target length, a totaliser at-most-`j` constraint on
the wildcard class, and two optional symmetry breakers. Class 0 is the wildcard.

```python
vdw4.solve(n, j, targets, k=None, workers=16, ...) -> (sat, colouring | None)
```
Conflict-limited whole-formula probe first; on `None`, cube-and-conquer.
**Raises `RuntimeError` unless every cube returned an explicit verdict.** This is
the contract the correctness of every upper bound rests on.

```python
vdw4.check(colouring, targets, j) -> (ok, wildcards_used, reason | None)
```
Reads only the colouring. Never sees the CNF. Every SAT answer passes through it
before anything is written.

```python
vdw_run.solve_resilient(n, j, targets, k, workers, engine, attempts=3, revsym=True)
```
Retries with progressively gentler settings — three fewer workers and one deeper
cube split each attempt — so a crash costs time rather than correctness.

```python
drat_certify.certify(n, j, targets, tools, workdir, timeout=None) -> record
```
`verdict` is one of `VERIFIED`, `NOT_VERIFIED`, `SAT`, `SOLVER_ERROR`, `TIMEOUT`.
`SAT` is reported distinctly and never folded into a generic error: it would mean
the upper bound being certified is false, which is the most important thing this
code could ever discover. Process exit codes are the interface the gate relies
on — `0` all verified, `1` a proof failed to verify, `3` the binaries are not
installed so nothing was checked and the caller should **skip**, not fail.

```
python vdw/verify_certificate.py "<cert>" <j> <t1> <t2>     # exit 0 + ACCEPTED
python vdw/verify_certificate.py --selftest                 # incl. negative controls
```
Standard library only. Imports nothing from the solver. This is the program an
editor is invited to run.

```python
make_submit_pack.crosscheck(seq, targets, j, value) -> (record | None, why)
make_submit_pack.family_gate(seq, targets, published, j) -> evidence | None
```
Both return `None` rather than raising, and `None` blocks the term.

```
python verify_all.py [--fast]     # exit 0 iff every claim matches its evidence
```

## What is enforced, in the absence of access control

No authentication, no database, no user account anywhere. Five things are
nonetheless enforced.

The repository is **public by decision**, and everything committed is intended to
be read. There is no private-by-accident content to protect.

**No credential exists.** `tools/oeis_campaign_watch.py` polls public URLs
read-only, makes no edits, sends nothing and holds no token. CI has no secrets.
Nothing in this repository can write to oeis.org.

**The staging folder is deliberately outside the repository** (`~/OEIS-upload`),
so paste-ready files are never committed and a clean clone cannot be used to
submit anything. The gate *skips* the staging sections when the folder is absent
rather than failing, because a clean clone and a CI runner both land there.

**The one enforced boundary is the public/local one.** `scrub_paths.py --check`
rewrites machine-local absolute paths to placeholders and fails CI if any remain.
It runs first in the workflow, before the mathematics, because an identity leak
in a public repository is the single failure a later commit cannot undo.

**Attribution is scoped to one file.** The author's name lives in `LICENSE` and is
parsed out of it at generation time; no source file contains it, so no copied
snippet carries it.

## Failure modes

| What breaks | Who notices | How we detect it | How we undo it |
|---|---|---|---|
| A cube's worker is killed by the OS mid-refutation | nobody, historically | `solve_checked` counts verdicts and raises if `done != len(tasks)` | rerun; the state file means only the undecided instance repeats |
| Solver defect reports a false UNSAT | nobody | DRAT proof replayed under `drat-trim` — for the published rungs only; **not** for the headline term | the term would be withdrawn; see Rollback |
| Encoding does not mean what the definition means | nobody | `encoding_audit.py` compares the CNF's solution set against a direct transcription of the definition, exhaustively and in both directions, 11 cases over 6 target shapes | fix the encoding, rerun every claim |
| Symmetry breaking discards an entire orbit, turning SAT into UNSAT | nobody | same audit checks every orbit keeps a representative; independently, one cross-check path imposes no reversal constraint at all | rerun with `--no-revsym` |
| A cross-check verdict from a different family vouches for this one | nobody | `crosscheck()` validates `j`, `targets` and `claim` inside the file | term blocks itself |
| A family gate is started and killed without a verdict | nobody — the reassuring sentence was unconditional prose | `family_gate()` looks the evidence up like everything else and returns `None` | term blocks itself; this is why A217059 is withheld |
| Prose quotes a stale published list or a wrong certificate | a reader, eventually | gate requires the full extended data line and the exact certificate string in `PAPER.md` and `README.md` | regenerate, or correct the prose |
| `SUBMIT.md` offers a term the evidence no longer supports | the operator, at the worst moment | gate parses `SUBMIT.md` headings against ready/blocked | `python make_submit_pack.py` |
| A staged b-file disagrees with the claim, or a withdrawn term is left staged | nobody | gate reads the staged files row by row | delete or regenerate the staged file |
| The approval watcher names a withdrawn term the instant a submission is approved | the operator, while acting on it | gate reads `watch_targets.json` against the pack | edit the file; the watcher re-reads it every cycle |
| RAM exhaustion, orphaned solver processes surviving their parent | the desktop freezes | worker cap below core count, `max_tasks_per_child=1`, `cleanup_stray_solvers.ps1` | kill by PID, restart; runs resume from the state file |
| A machine-local path enters the public record | nobody | `scrub_paths.py --check`, first CI step | scrub and force the history only if it has already been pushed |

## Two undos, and the asymmetry between them

The asymmetry is the reason the design front-loads everything.

**Before a submission — cheap and total.** Every artefact here is a file in git.
Regenerating the pack is one command, the gate re-derives every claim from the
evidence in seconds, and a wrong result is undone by deleting its evidence file
and rerunning the instance. Nothing is irreversible. `git revert` restores any
prose. Blocking a term is a one-line change to what the evidence supports, and it
propagates automatically to the pack, the staging folder and the watcher.

**After a submission — not a software rollback at all.** An OEIS entry is a
permanent public record maintained by volunteers. If a submitted term turned out
to be wrong, the procedure is:

1. Stop the approval watcher, so nothing announces the next submission.
2. Remove the term's evidence from the claims table, regenerate `SUBMIT.md`, and
   confirm the gate now lists it as blocked and refuses to stage its b-file.
3. Delete the staged b-file and remove the target from `watch_targets.json`.
4. Reply on the entry itself asking for the extension to be reverted, saying
   plainly what was wrong.

Steps 1–3 take minutes. Step 4 is a retraction under the author's own name, in
public, and has no time bound. **That is irreversible in the only sense that
matters**, and it is accepted for exactly one reason: the checks that would
prevent it are all cheap and all run before the paste. Which is also why a term
whose family gate never finished is withheld rather than submitted with a
plausible explanation attached.

## Test plan

The gate is `python verify_all.py`. How many checks it runs depends on what the
machine has, and every gap **skips loudly rather than failing**: the staging
sections need `~/OEIS-upload`, and the DRAT sections need `kissat` and
`drat-trim`, neither of which this repository ships.

Measured 2026-08-03 on a machine with the staging folder but without the DRAT
binaries: **100 passed, 0 failed, exit 0, 12 s** for the full run including both
slow audits. A CI runner has neither and so runs fewer still. Only the verdict
line and the exit code are stable across machines; a check count is not, and
should not be quoted as one.

**Positive — legitimate results still verify.** `vdw_validate.py` replays 29
published values across five families through the engine, requiring a verified
witness at `w-1` and a refutation at `w` for each. `verify_certificate.py
--selftest` and `ec/verify_rank.py --selftest` both pass.

**Negative — the thing being prevented is prevented.** The encoding audit runs in
both directions, so an over-permissive CNF fails as loudly as a lossy one. The
DRAT checker was validated against controls first: a proof truncated to half, a
proof of a different formula, and every instance one below a published term —
which must report `SAT`, and does. `scale_test.py` accepts 240 at-the-limit
wildcard assignments and rejects 240 over-limit ones at the exact size the
headline result uses.

**Boundary — legacy and missing rows.** The unqualified legacy cross-check
filename is read but re-validated. A missing staging folder skips. Missing
`kissat` or `drat-trim` exits 3 and skips. A blocked term is asserted absent from
four separate artefacts, not merely absent from one.

Several of these were written *because* the thing they check had already
happened. A217059 passed 76 consecutive gate runs while `SUBMIT.md` offered it,
because until then nothing in the gate had opened `SUBMIT.md`.

## Build order

Each step motivated by a failure in the one before.

1. `vdw.py`, `vdw2.py` — first encodings; colour-permutation symmetry breaking.
2. `vdw4.py` — reversal lex-leader constraint, pluggable engine, crash-honest
   parallelism.
3. `vdw_run.py`, `vdw_probe.py` — resumable, detached, durable per-instance
   evidence with its own log file.
4. `verify_certificate.py` — the standalone checker, written before any claim.
5. `encoding_audit.py`, `vdw_validate.py`, `scale_test.py` — the guards around
   the encoding.
6. `cross_check.py` — the second, disjoint derivation.
7. `make_submit_pack.py` — generate the paste, exclude anything unsupported.
8. `verify_all.py` — one command over everything.
9. `.github/workflows/ci.yml` — the same gate on every push.
10. `drat_certify.py` — a proof object where the cost allows one.

## Certifying the headline rung

A single-shot DRAT proof at `n=57, j=12` is order 6–17 hours and 30–150 GB. The
tractable route is a per-cube proof plus a composition argument, and it is
unusually clean for this family: targets 3 and 4 differ, so `_symbreak_colours`
emits no clauses, the cube set is exactly the prefixes surviving the wildcard
budget and the local AP test, and every discarded prefix is refuted by a clause
already present in the formula — which makes exhaustiveness certifiable by unit
propagation rather than assumed.

Nothing else in the repository depends on this being done.
