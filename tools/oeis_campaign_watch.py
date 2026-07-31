"""Watch every OEIS submission in the campaign, not just the first. Read-only.

    python tools/oeis_campaign_watch.py [--interval 3600] [--max-hours 720]
                                        [--staging DIR]

What it does each cycle, for every target marked "live":

  * reads the public b-file; a last line of "<index> <value>" means that term
    is published, so the submission was approved;
  * reads the public draft page and tracks its highest version number, so an
    editor's comment or edit is noticed within one interval. A whole-page hash
    CANNOT be used here: oeis.org embeds a per-request Cloudflare token, so the
    digest changes on every single poll and reports an editor who never acted;
  * on approval writes a loud "<seq> APPROVED - READ ME.txt" in the home
    directory naming what to submit next, then KEEPS RUNNING for the rest.

It makes no edits, submits nothing, sends nothing and holds no credential.
Approval and submission are the operator's acts alone.

Targets live in watch_targets.json in the staging folder:

    [{"seq": "A217058", "idx": 12, "val": 57, "live": true, "approved": false}]

Set "live": true the moment a draft is actually proposed; queued entries are
not polled, so a sequence nobody has submitted yet costs nothing.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STAGING = Path.home() / "OEIS-upload"
UA = {"User-Agent": "Mozilla/5.0"}
VERSION = re.compile(
    r"#(\d+)</a> by <a[^>]*>([^<]+)</a> at "
    r"([A-Z][a-z]{2} [A-Z][a-z]{2} \d{1,2} [\d:]{8} E[SD]T \d{4})")
LOG: list[str] = []


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def get(url: str, timeout: int = 45) -> str | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - a failed poll must never kill the watcher
        LOG.append(f"    fetch failed {url.rsplit('/', 1)[-1]}: {exc}")
        return None


def write_status(targets: list[dict], status_file: Path) -> None:
    live = [t for t in targets if t.get("live") and not t.get("approved")]
    done = [t for t in targets if t.get("approved")]
    queued = [t for t in targets if not t.get("live") and not t.get("approved")]
    watching = ", ".join("{} (a({})={})".format(t["seq"], t["idx"], t["val"])
                         for t in live) or "(none)"
    head = [
        "OEIS campaign approval watch",
        f"Last update: {stamp()}",
        "",
        f"WATCHING : {watching}",
        f"APPROVED : {', '.join(t['seq'] for t in done) or '(none yet)'}",
        f"QUEUED   : {', '.join(t['seq'] for t in queued) or '(none)'}",
        "",
    ]
    status_file.write_text("\n".join(head) + "\n".join(LOG[-400:]) + "\n",
                           encoding="utf-8")


def announce(t: dict, targets: list[dict], staging: Path) -> None:
    queued = [q for q in targets if not q.get("approved") and q["seq"] != t["seq"]]
    nxt = "\n".join(f"  {q['seq']}  a({q['idx']}) = {q['val']}"
                    f"{'   <- already submitted, under review' if q.get('live') else ''}"
                    for q in queued) or "  (nothing left - the campaign is complete)"
    (Path.home() / f"{t['seq']} APPROVED - READ ME.txt").write_text(
        f"{t['seq']} a({t['idx']}) = {t['val']} HAS BEEN APPROVED AND PUBLISHED.\n\n"
        f"Detected {stamp()} by oeis_campaign_watch.py from the public b-file.\n\n"
        "STILL TO GO:\n" + nxt + "\n\n"
        "Before pasting anything, from the MathRecords checkout:\n"
        "  1. python verify_all.py                  (must exit 0)\n"
        "  2. python tools/sync_from_submit.py      (staged files match SUBMIT.md)\n"
        "  3. paste DATA, then the COMMENT with the wrapper dated TODAY, then the\n"
        "     new EXTENSIONS line BELOW the existing ones - never alter those.\n"
        "  4. Save changes, add the discussion note, then press\n"
        "     'These changes are ready for review by an OEIS Editor.'\n\n"
        "Text to paste: SUBMIT.md in the MathRecords checkout - the one source of\n"
        f"truth. Staged copies: {staging}\n"
        "No b-file upload is needed - none of these entries has one, so the OEIS\n"
        "regenerates it from DATA.\n",
        encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=3600, help="seconds between polls")
    ap.add_argument("--max-hours", type=float, default=720.0, help="stop after this long")
    ap.add_argument("--staging", type=Path, default=DEFAULT_STAGING)
    args = ap.parse_args()

    targets_file = args.staging / "watch_targets.json"
    status_file = args.staging / "APPROVAL_STATUS.txt"
    targets = json.loads(targets_file.read_text(encoding="utf-8"))
    deadline = time.time() + args.max_hours * 3600.0
    versions: dict[str, tuple] = {}
    LOG.append(f"[{stamp()}] campaign watch started, every {args.interval}s for "
               f"{args.max_hours:.0f}h. Read-only; submits nothing.")
    write_status(targets, status_file)

    while time.time() < deadline:
        for t in targets:
            if not t.get("live") or t.get("approved"):
                continue
            seq = t["seq"]
            body = get(f"https://oeis.org/{seq}/b{seq[1:]}.txt")
            if body:
                rows = [ln.strip() for ln in body.strip().splitlines() if ln.strip()]
                last = rows[-1] if rows else ""
                LOG.append(f"[{stamp()}] {seq} b-file last line: {last!r}")
                if last.split()[:2] == [str(t["idx"]), str(t["val"])]:
                    LOG.append(f"[{stamp()}] *** {seq} APPROVED: "
                               f"a({t['idx']}) = {t['val']} ***")
                    t["approved"] = True
                    announce(t, targets, args.staging)
                    targets_file.write_text(json.dumps(targets, indent=1), encoding="utf-8")
                    continue
            draft = get(f"https://oeis.org/draft/{seq}")
            if draft:
                vers = VERSION.findall(draft)
                if vers:
                    top = max(vers, key=lambda v: int(v[0]))
                    seen = versions.get(seq)
                    if seen is not None and int(top[0]) > int(seen[0]):
                        LOG.append(f"[{stamp()}] {seq} EDITOR ACTED: new version "
                                   f"#{top[0]} by {top[1]} at {top[2]} -- read "
                                   f"https://oeis.org/draft/{seq} and reply TODAY")
                    versions[seq] = top

        write_status(targets, status_file)
        if all(t.get("approved") for t in targets):
            LOG.append(f"[{stamp()}] every target approved - campaign complete")
            write_status(targets, status_file)
            return 0
        time.sleep(args.interval)

    LOG.append(f"[{stamp()}] watch window elapsed; restart if wanted")
    write_status(targets, status_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
