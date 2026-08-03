# Design Brief — the console and the generated paste

**Date:** 2026-08-03 · **PRD:** [PRD.md](PRD.md) · **App Flow:** [APP_FLOW.md](APP_FLOW.md)

The designed surface here is not a screen. It is three text artefacts an operator
reads under pressure: the `go.cmd` menu, the line-by-line output of
`verify_all.py`, and the generated `SUBMIT.md`. They share one job — making the
right action obvious and the wrong action awkward at the moment a permanent
public record is about to be written.

Sections of the standard template that have no meaning in `cmd.exe` — type
family, colour palette, breakpoints, touch targets — are cut rather than padded.

## Intent

**Procedural and undramatic.** The operator should feel they are following a
checklist someone else wrote, not making a judgement call. Every screen ends by
naming the next thing to do, and the one irreversible action asks for a typed
word.

It must never feel **reassuring by default**. This surface exists because the
failure it guards against — pasting a wrong term into the OEIS — is quiet, and
anything that reads as "all fine" without having checked is worse than silence.
`verify_all.py` prints its verdict sentence only after every check has passed;
`make_submit_pack.py` prints `blocked:` in the same breath as `ready:`.

## Who is looking at it

The author, weeks after the mathematics, at whatever hour an OEIS approval email
lands. They are not doing research at that moment; they are executing a
procedure with four near-identical certificate strings on screen, any one of
which would be catastrophic to paste under the wrong sequence. They may not have
opened this project in a month.

Design for that person: no recall required, no context to reconstruct, and a
single sentence that decides whether to proceed.

## Precedents

- **`git status`.** Every state it can be in ends with the literal command that
  moves you out of it. The console copies that: option 2 prints the rail *"the
  last line must say EVERY CLAIM … If it says anything else, DO NOT SUBMIT"*
  immediately under the output, so the reading instruction and the thing being
  read are on the same screen.
- **The OEIS edit form itself.** Fixed field order, ASCII, no styling. `SUBMIT.md`
  numbers its blocks `1. DATA`, `2. b-file`, `3. EXTENSIONS`, `4. COMMENT`,
  `5. Verify it yourself` in the order the form asks for them, so the eye moves
  down the page and down the form together and a skipped field is visible as a
  skipped number.
- **Aviation checklists.** One action per line, and the destructive item called
  out differently from the rest. Option 7 is the only place in the console that
  demands a typed `YES`, which is what keeps that gesture meaningful.

## Anti-patterns for this project

- **Spinners and progress bars.** A refutation runs for hours with nothing to
  say, and an animation cannot distinguish working from hung. The status screen
  prints accumulated **CPU seconds per process** instead — climbing means
  computing. The probe logs a heartbeat every five minutes for the same reason.
- **Colour as status.** No colour anywhere. Verdicts are words, so they survive a
  screen reader, a redirect to a file, and a paste into a message.
- **Generic failure text.** `verify_all.py` names the failed check, then lists
  every failure again at the end. An earlier version passed the failure
  explanation as the general detail field, so `[PASS]` lines cheerfully printed
  *"quoted certificate differs from the computed one"* underneath the word PASS.
  The two fields are now separate — context always, explanation only on failure.
- **Anything that submits.** No console option, and no script, writes to
  oeis.org. The watcher is read-only and holds no credential. An interface that
  could paste for you would be the fastest possible route to an unreviewed
  retraction.
- **Prose the operator has to interpret.** Numbers in `SUBMIT.md` are read from
  the evidence JSON; the operator is asked to copy, never to transcribe, and the
  `Never` list says so as its second bullet.

## Constraints of the medium

- **`cmd.exe`, default window, no configuration.** Assume 80 columns and the
  local code page. Rules are rows of `=`; there are no box-drawing characters and
  no glyph that renders differently between machines.
- **Plain ASCII in everything that is pasted.** The OEIS b-file convention is
  ASCII, LF, trailing newline, and `tools/sync_from_submit.py` writes exactly
  that. The comment blocks are US-spelled, because the OEIS style sheet requires
  it and an editor corrected `colour` and `relabelling` by hand on the first
  submission — the repository's own prose stays British and simply must not reach
  the record.
- **Every screen ends in `pause`.** Nothing scrolls away before it is read.

## States

| State | How it reads |
|---|---|
| Idle / nothing running | headings with nothing under them. Honest, but indistinguishable from a broken query — the weakest state in the design |
| Working | one line per process, CPU seconds climbing; a heartbeat line every 5 minutes in long solves |
| Passed | `[PASS]` per check, a count, then one verdict sentence and nothing else |
| Failed | `[FAIL]` with its explanation inline, then the failed names repeated as a list |
| Refused | `NOT ready — do not submit these`, with the specific missing evidence named per term |
| Landed | a banner above the menu, and a file named to sort first in the folder |
| Destructive | the only prompt that requires typing a word |

## Accessibility floor

- Keyboard only; one digit and Enter for every action.
- Colour is never the sole signal, because there is no colour.
- No timed state, no auto-refresh, no animation — `prefers-reduced-motion` is
  satisfied by there being no motion.
- Output is linear plain text, so a screen reader reads it in the order it was
  written, and it survives being piped or pasted.
- Line lengths stay inside 80 columns so nothing depends on the window being
  resized.

## Done means

- [x] Every screen names the next action.
- [x] The verdict the operator must find is quoted on screen next to the output
      it applies to.
- [x] Nothing pasteable is hand-typed; the pack is generated from evidence.
- [x] A term without complete evidence is visibly refused, with the reason.
- [x] The only irreversible action requires a typed confirmation.
- [ ] **Idle is distinguishable from broken.** It is not, today: a status screen
      with nothing running prints empty headings.
- [ ] **No screen can reach a raw stack trace.** It can — see *Dead ends* in the
      App Flow, where the submission sub-menu offers a withdrawn sequence and
      raises a .NET exception.
