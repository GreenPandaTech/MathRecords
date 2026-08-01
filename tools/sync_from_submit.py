"""Regenerate the staged OEIS paste files from SUBMIT.md.

SUBMIT.md is the ONE source of truth: make_submit_pack.py writes it from the
evidence JSON and verify_all.py covers it. The COMMENT-*.txt files in the
staging folder exist only so a paste never has to scroll past markdown fences.
They are a generated artifact - never hand-edit them.

    python tools/sync_from_submit.py                 # check only, exit 1 on drift
    python tools/sync_from_submit.py --write         # rewrite the staged files
    python tools/sync_from_submit.py --staging DIR   # non-default staging folder

Writes LF-only, no BOM, trailing newline (the OEIS b-file/upload convention).
Refuses outright, without writing anything, if a CERTIFICATE ever differs -
that would mean the evidence changed, not the prose, and a human must look.

The signature wrapper is deliberately NOT stored: its date must be the real
submission date, so it is taken from SUBMIT.md at paste time.

Why this exists: on 2026-07-31 the staged A217005 and A217007 files were
written an hour before the generator was improved, and silently lost the word
"or" from the definition sentence. Hand-kept copies drift. Generate them.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBMIT = REPO / "SUBMIT.md"
DEFAULT_STAGING = Path.home() / "OEIS-upload"
BLOCK = re.compile(r"## (A\d{6}) \S+ .*?### 4\. COMMENT[^\n]*\n```\n(.*?)\n```", re.S)
CERT = re.compile(r"^[.12]{20,}$")


def bodies() -> dict[str, str]:
    out: dict[str, str] = {}
    for seq, block in BLOCK.findall(SUBMIT.read_text(encoding="utf-8")):
        lines = block.split("\n")
        if not lines[0].startswith("From _") or lines[-1].strip() != "(End)":
            sys.exit(f"{seq}: SUBMIT.md comment is not wrapped as expected")
        out[seq] = "\n".join(lines[1:-1]).strip("\n")
    if not out:
        sys.exit("no COMMENT blocks found in SUBMIT.md - has the generator changed?")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="rewrite drifted files")
    ap.add_argument("--staging", type=Path, default=DEFAULT_STAGING,
                    help=f"folder holding COMMENT-*.txt (default: {DEFAULT_STAGING})")
    args = ap.parse_args()

    if not args.staging.is_dir():
        sys.exit(f"staging folder not found: {args.staging}")

    drift: list[str] = []
    for seq, body in sorted(bodies().items()):
        target = args.staging / f"COMMENT-{seq}.txt"
        want = body.replace("\r\n", "\n") + "\n"
        have = target.read_text(encoding="utf-8") if target.exists() else None
        cert_want = [l for l in want.splitlines() if CERT.match(l.strip())]
        cert_have = [l for l in (have or "").splitlines() if CERT.match(l.strip())]
        if have == want:
            print(f"  OK    {seq}  ({len(body)} chars, certificate "
                  f"{len(cert_want[0]) if cert_want else 0})")
            continue
        if cert_have and cert_have != cert_want:
            print(f"  !!!!  {seq}  CERTIFICATE DIFFERS - stop and investigate by hand")
            return 2
        drift.append(seq)
        print(f"  DRIFT {seq}  prose differs from SUBMIT.md (certificate identical)")
        if args.write:
            target.write_bytes(want.encode("utf-8"))
            print(f"        rewritten from SUBMIT.md ({len(want)} bytes, LF)")

    # The check above is one-directional: it walks SUBMIT.md and looks for a
    # matching staged file. It never walks the staging folder, so a sequence
    # WITHDRAWN from SUBMIT.md keeps a complete, correct-looking, pasteable
    # COMMENT and b-file, and this tool reported "all staged comment files match
    # SUBMIT.md" without ever opening it.
    #
    # That is not hypothetical. A217059 was blocked in aa9f79c because its family
    # gate never finished (logs/validate_gate59.log holds two header lines and no
    # result), and its staged files were written hours earlier and stayed behind.
    # verify_all.py only asserts the term is ABSENT from SUBMIT.md, which it is,
    # so every gate the operator is told to run exited 0 while the folder they
    # paste from still offered the term.
    #
    # The operator holds none of the mathematics by design, so an orphan here is
    # indistinguishable from a live target. Enumerate the folder and refuse.
    offered = set(bodies())
    staged: set[str] = set()
    for path in args.staging.glob("COMMENT-A*.txt"):
        staged.add(path.stem.removeprefix("COMMENT-"))
    for path in args.staging.glob("b[0-9]*.txt"):
        staged.add("A" + path.stem[1:])

    orphans = sorted(staged - offered)
    if orphans:
        print()
        for seq in orphans:
            print(f"  !!!!  {seq} is STAGED but NOT OFFERED by SUBMIT.md")
        print("\nThese were withdrawn - their evidence did not hold - but their paste\n"
              "files are still here and still look ready. DO NOT PASTE THEM. Remove\n"
              "them from the staging folder, or restore the term to SUBMIT.md by\n"
              "supplying the evidence it is missing.")
        return 3

    if drift and not args.write:
        print("\nstaged files are STALE - run with --write before pasting anything")
        return 1
    print("\nstaged files resynced from SUBMIT.md" if drift
          else "\nall staged comment files match SUBMIT.md, and nothing is staged "
               "that SUBMIT.md does not offer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
