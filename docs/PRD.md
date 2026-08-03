# MathRecords — what the deliverable actually is

Written after the work. Everything below is reconstructed from the code and the
evidence files in this repository; where the original intention cannot be
recovered from an artefact, it is left out rather than invented.

[TDD](TDD.md) · [App Flow](APP_FLOW.md) · [Design Brief](DESIGN_BRIEF.md) ·
`PAPER.md` in the repository root

## The interesting half of the result is an absence

Five OEIS sequences of *mixed van der Waerden numbers* — A217005, A217007,
A217058, A217059 and A217236 — carry short published lists that had not moved
since 2012, and each is flagged `hard`. Extending one by a single term is within
reach of a desktop machine and a modern SAT solver. That is not the problem.

The problem is that a new term `a(j) = w` is two claims. A colouring of
`[1, w-1]` exists, which is easy to state and trivial to check. And no colouring
of `[1, w]` exists, which is expensive to establish and impossible to hand anyone
as an object.

"No colouring exists" is also what a mis-transcribed encoding reports, what a
solver bug reports, and what a worker killed by the operating system reports if
its silence is counted as an empty branch. Three runs in this project were lost
to exactly that last failure before it was made to raise.

## So the deliverable is not a number

It is a number *plus enough independently checkable structure that an OEIS editor
never has to trust the program that produced it*.

Every lower bound is checkable by a standard-library-only program sharing no code
with any solver — `vdw/verify_certificate.py`, milliseconds. Every upper bound is
re-derived along a path that cannot share a mistake with the first: three
refutation paths per term, and one engine imposes no reversal-symmetry constraint
at all.

## The paste is the dangerous moment

There is a second problem, sharper than the first, at the other end.

The person pasting the result into a permanent public record is the same person
who wrote the code, possibly weeks later, at the end of a long run, with five
sequences in flight and four near-identical certificate strings on screen.

One wrong character in a pasted certificate is a retraction under their own name.

Which is why nothing pasted into the OEIS is typed by a human. `SUBMIT.md` is
generated from the evidence JSON, and the generator re-runs the verifier first. A
term whose evidence is incomplete cannot be pasted by accident: A217059 is
blocked by `make_submit_pack.py`, and the gate fails if any artefact still offers
it.

## Requirements

**Must**

- Both halves of every claimed term backed by an artefact on disk, written by the
  computation and never transcribed.
- A refutation reported only when every cube in the search has returned an
  explicit verdict. A dead worker raises.
- A standalone verifier for the lower bound that imports nothing from the solver.
- The encoding proven equal to the definition, not argued to be.
- A single source of truth for what this repository claims, with every other file
  deriving from it or checked against it.
- Fail closed: any missing or mismatched piece of evidence blocks the term.

**Should**

- Machine-checked (DRAT) refutations wherever the cost is bearable.
- An interactive console, so routine operation needs no code and no AI.
- CI that runs the same gate on every push.
- Durable, resumable runs, so a closed window costs one instance rather than a
  night.

**Won't, this time**

- Automate the OEIS submission itself. The watcher polls read-only, holds no
  credential and submits nothing; approval and pasting are human acts.
- Package the engine as a reusable library.
- Chase further terms once four are established and one is under review.

## What is not claimed

**No new mathematics.** This extends tracked lists by computation. It proves
nothing structural about the growth of these families and introduces no proof
technique. `PAPER.md` §7 says so first, before it says anything else.

**No formal proof of the headline upper bound.** DRAT certification exists and is
gated, but only for the *published* rungs `a(0)`–`a(6)` of A217058 and the first
rungs of three other families. The headline rung `n=57, j=12` is order 6–17 hours
of solving and a 30–150 GB proof; it wants a per-cube proof plus a composition
argument, and that work has not been done. The write-up must not soften this. It
is also the one live technical question in the project — whether the headline
rung can be certified by composing per-cube DRAT proofs — and the shape of that
argument is recorded in `SESSION_HANDOFF.md` and in the TDD. Nothing depends on
the answer.

**No competition on elliptic-curve rank.** `ec/` is a side thread producing a
genuine, independently verifiable `rank E(Q) >= 7`. The record is `>= 29`. That
gap is stated in `ec/README.md` and is not a target.

**No general-purpose van der Waerden tool.** The engine is shaped by the five
families it was pointed at.

**No link from the OEIS entry back to this repository.** Deliberate; the reason is
below.

## Checked, not asserted

Each of these is verified by `verify_all.py` rather than claimed.

- [x] At least one previously uncomputed term established in a tracked sequence.
      *Four are: A217058(12)=57, A217236(4)=84, A217005(19)=52, A217007(7)=68.*
- [x] Every lower bound checkable by a standard-library-only program that shares
      no code with any solver.
- [x] Every upper bound re-derived along a path that cannot share a mistake with
      the first.
- [x] One command re-checks every claim in the repository against the evidence on
      disk and exits non-zero if any has drifted. *`python verify_all.py`.*
- [x] Nothing pasted into the OEIS is typed by a human.
- [x] A term whose evidence is incomplete cannot be pasted by accident.
- [x] No machine-local path and no personal detail reaches a public repository,
      beyond the one attribution line the LICENCE carries.
      *`scrub_paths.py --check`, first step in CI.*

Not met, and stated as not met: the headline upper bound has no formally checked
proof object.

## Three readers, in the order their needs win

**The OEIS editor reviewing the submission.** A volunteer, careful, with no access
to this machine and no reason to install a SAT solver. They need the lower bound
checkable in seconds and a comment that defines its own terms — the sequence
entries themselves never mention partitions or arithmetic progressions, and the
first submission was corrected on exactly that point.

**The author, acting as operator.** Not doing mathematics at that moment;
following a procedure. They need one command that says whether anything has
drifted, and copy-paste blocks they never have to retype.

**A third party checking the claim later**, with only a clone and a Python
install.

## A public repository with an anonymous owner

That combination sets the rules.

Exactly one item of personal data is in play: the author's legal name, which OEIS
attribution requires on a permanent record. It is written in `LICENSE` and
nowhere else, and `make_submit_pack.py` parses it out of the licence header
rather than hardcoding it, so no source file carries it and no copied snippet
travels with it. No email, no location, no affiliation, anywhere.

Solver logs record absolute paths, so every committed file is scrubbed to
portable placeholders. `scrub_paths.py --check` is the *first* CI step, because a
path leak in a public repository is the one failure a later commit cannot undo.

No link to this repository is placed in a submission or in editor discussion,
deliberately. An OEIS entry is permanent, and a link would tie the name on it to
a code account for good, while the term itself does not need one. An editor who
wants to check the lower bound gets the verifier command, plus the offer to
attach `verify_certificate.py` to the entry as a file hosted on oeis.org — more
durable than a link, because it cannot rot.

There is no login here, but there is an exact analogue of revocation: a claim
being *withdrawn*. When A217059 was pulled for having no completed family gate,
every downstream surface had to stop offering it — the submission pack, the
prose, the staged upload folder, and the approval watcher that speaks to the
operator unprompted at the single moment they are most likely to act without
re-checking. Each of those is now a gate check, because each of them had drifted
at least once.

The worst outcome is a false term in a permanent public mathematical record,
corrected by a retraction under the author's own name, in a venue maintained by
volunteers. That is the whole reason the design front-loads verification: the
only cheap moment to be wrong is before the paste.

## Rejected

| Considered | Rejected because |
|---|---|
| Climbing `n` upward one step at a time from the previous term | 1000–3500 s per step and no upper bound ever produced. Replaced by bracketing: refute a generous `n` to cap the answer, lift the floor with witnesses, close the single remaining gap. Valid because satisfiability is monotone in `n`. |
| `Kissat404` through pysat | Hard-crashes the interpreter on this platform — a native abort with no Python exception. Excluded rather than worked around. Kissat is still used, as a *standalone binary*, for DRAT proofs. |
| Sixteen concurrent solvers on eight physical cores | Each CaDiCaL grows an unbounded learned-clause database; this exhausted RAM, orphaned 39 workers and froze the desktop. Workers are capped well below core count and retired after each cube. |
| Finer cube splits (`k = 6`) | Measured slower: 65.1 s against 34.1 s at `k = 4` on `n=45, j=8`. |
| Session-managed background tasks for the long watchers | Killed twice within minutes by ordinary session changes, silently. A watcher that dies without saying so is worse than none. Everything long-running is a detached OS process. |
| Hashing the whole OEIS draft page to detect editor activity | oeis.org embeds a per-request Cloudflare token, so the digest changes on every poll and reports edits that never happened. The draft's version number is used instead. |
| Hand-maintained copies of the paste text in the staging folder | They drifted within an hour and silently lost a word from a definition sentence. Generated from `SUBMIT.md` now, and checked for drift. |
| Treating a cube whose worker died as "no solutions in this branch" | This is precisely how a false new term gets published. It raises. |
| Submitting all five terms at once | One round-trip with an editor teaches more than five simultaneous guesses, and a question about the strongest result is better answered once. One at a time, strongest first, ranked from the evidence rather than from memory. |
