# DRAT certificates for the upper bounds

Every result here is a pair. The **lower** bound ships a colouring that anyone
can check against the definition in milliseconds with `verify_certificate.py`,
trusting none of the search code. The **upper** bound says *no* colouring exists
— an absence — and for a long time it rested on a SAT solver answering UNSAT,
with five guards around the encoding and nothing around the solver.

`drat_certify.py` closes that. The solver emits a DRAT proof of unsatisfiability
and `drat-trim` replays it against the formula. What is left to trust is
`drat-trim` and the claim that the CNF says what the definition says — and that
second half is what `encoding_audit.py` checks exhaustively, in both directions,
on instances small enough to enumerate.

**Symmetry breaking is off in these proofs** (`symbreak=False, revsym=False`).
A proof of a symmetry-broken formula does not prove the original statement, and
the reversal lex-leader constraint is the one piece of new mathematics in
`vdw4` — precisely the thing that must not be assumed by its own check.

## Running it

```sh
python vdw/drat_certify.py --rung 7            # a(7) = 42 of A217058
python vdw/drat_certify.py --ladder 0-6        # the cheap rungs
python vdw/drat_certify.py --seq A217236 --ladder 0-1
python vdw/drat_certify.py --n 42 --j 7 --targets 3 4
```

`verify_all.py` runs a short ladder across all four families. **If the binaries
are absent it skips rather than fails** — a clean clone and a CI runner both land
there, and a missing tool is not a broken claim.

Point at the binaries with `--kissat` / `--drat-trim`, the `KISSAT` /
`DRAT_TRIM` environment variables, or by putting them on `PATH`. No build
location is hardcoded: this repository is public, and one machine's directory
layout is no use to a reader.

## Measured cost (A217058, symmetry breaking off)

| rung | solve | proof | check |
|---|---:|---:|---:|
| a(4) = 33, j=4 | 0.4 s | 2.5 MB | 0.4 s |
| a(6) = 40, j=6 | 2.4 s | 15.6 MB | 2.7 s |
| a(7) = 42, j=7 | 25.1 s | 87.5 MB | 35.5 s |
| a(8) = 45, j=8 | 61.4 s | 173.0 MB | 90.8 s |

Roughly **2.4x per rung** in both time and size; checking costs about 1.4x
solving. Extrapolated to the headline `a(12) = 57 at n=57, j=12`, a single-shot
proof is order 6–17 h and 30–150 GB. That is why the ladder in the gate stops
where it does. The sane route to the headline term is a **per-cube proof plus a
composition argument**, which is unusually clean for this family: targets 3 and 4
differ, so `_symbreak_colours` emits nothing, the cube set is exactly the
prefixes surviving the budget and AP pruning, and every *dropped* prefix is
refuted by a single clause already in the formula — so exhaustiveness of the cube
set is itself certifiable by unit propagation rather than assumed.

## Building the two binaries

Neither is redistributed here; both are built from pristine upstream sources.
The recipe below was carried out on a Windows box with **no C compiler at all**,
using `zig cc` as the compiler, both toolchains installed without administrator
rights (`winget install --scope user`).

### drat-trim

Source: `https://raw.githubusercontent.com/marijnheule/drat-trim/master/drat-trim.c`
`sha256 = d834b649f437e091597f5347f259b9f681087f89ca0844d0cee250a1a1a0c2ee`
(1501 lines, upstream edit of 2024-04-21). Kept **byte-identical to upstream** so
that hash stays checkable — both portability fixes are compiler flags, not edits.

```sh
zig cc -O2 -Dgetc_unlocked=getc -include drat_win_shim.h -o drat-trim.exe drat-trim.c
```

Two Windows holes, both fatal and both silent:

1. `getc_unlocked` is POSIX-only. Supplied by `-D`.
2. **drat-trim opens the proof with `fopen(path, "r")` — text mode on Windows.**
   Byte `0x1A` reads as end-of-file, so a binary proof is silently truncated and
   the checker reports `s NOT VERIFIED` in about 0.06 s. It looks like a bad
   proof; it is a bad build. `drat_win_shim.h` forces a `b` onto every mode
   string. On Linux and macOS neither fix is needed.

### Kissat 4.0.1

Source: `https://github.com/arminbiere/kissat/archive/refs/tags/rel-4.0.1.tar.gz`
(the `test/cnf/hard.cnf` symlink fails to extract on Windows — harmless, tests
only).

```sh
CC="zigcc -mno-ms-bitfields -I<winshim> -include <winshim>/winshim_posix.h" ./configure
sed -i 's/-W -O -DNDEBUG/-W -O3 -DNDEBUG/' build/makefile   # configure only picks -O
make -C build -j4 AR=zigar
(cd build && for f in *.obj; do mv "$f" "${f%.obj}.o"; done) # zig cc writes .obj
make -C build AR=zigar                                       # second pass links
```

1. **`-mno-ms-bitfields` is mandatory.** Kissat's `watch` union mixes `bool:1`
   with `unsigned:31`; MSVC bitfield packing starts a new storage unit at the
   type change and makes the union 8 bytes where the solver requires 4. **Build
   with assertions (`configure -c`) FIRST and run one real instance before
   trusting an `-DNDEBUG` build** — with `NDEBUG` it runs happily on corrupt
   watch lists and there is no outward sign.
2. `--time=` does nothing in a Windows build (the shim supplies a no-op
   `alarm`); bound runs with an external subprocess timeout instead, which is
   what `--timeout` here does.
3. `tissat`, the `--test` binary, does not build (`sys/wait.h`). The solver is
   unaffected.

### Why not pysat

`Solver(..., with_proof=True)` returns a **truncated** proof from every solver it
ships (cadical103/153/195, glucose3/4/42, lingeling, maplechrono): drat-trim's
forward mode confirms each logged lemma is valid RUP, but the refutation never
closes — `c conflict claimed, but not detected`. A four-clause UNSAT formula
yields zero proof lines. A standalone binary is required.

Also: kissat's **binary** proof does not check under drat-trim (`RAT check failed
on all possible pivots`, at a different line for every inprocessing setting — a
format mismatch, not a technique to disable). The ASCII proof of the identical
run verifies, at roughly 2–3x the bytes. Hence `--no-binary`.

## Validate the checker before believing it

A checker that says VERIFIED on everything proves nothing. These controls were
run against the built binaries and behave correctly:

| control | expected | got |
|---|---|---|
| real proof of the formula | VERIFIED | VERIFIED |
| proof of a *different* formula | NOT VERIFIED | NOT VERIFIED |
| bare empty clause as the whole proof | NOT VERIFIED | NOT VERIFIED |
| real proof against a *satisfiable* formula | NOT VERIFIED | NOT VERIFIED |
| proof truncated to its first half | NOT VERIFIED | NOT VERIFIED |
| `n = a(j) - 1` for each of rungs 0–4 | SAT, never VERIFIED | SAT |

Dropping only the *last few* lines still verifies, correctly — the remaining
lemmas already propagate to a conflict. Use half-truncation as the control.

The last row is the one that matters most for this project: an instance one below
a published term is satisfiable, so a pipeline that reported VERIFIED there would
be certifying a false upper bound. `drat_certify.py` reports `SAT` and exits
non-zero. **Only the checker's literal `s VERIFIED` line counts as a pass** —
every other outcome, including a parse failure, fails the gate.
