"""Strip machine-local absolute paths out of the committed record.

The solvers log wherever they happen to run, so raw logs carry the operator's
home directory. That is noise in a public repository: the mathematics does not
depend on which machine produced it, and a reader cannot check a path anyway.
This rewrites those paths to portable placeholders.

Idempotent: running it twice changes nothing the second time. It only touches
text files that git already tracks, and it never edits a file another process
currently holds open for writing (pass --all to override that guard).

    python scrub_paths.py            # report and fix
    python scrub_paths.py --check    # report only, non-zero exit if dirty
"""

import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser('~')

# Order matters: longest, most specific path first, so the generic
# home-directory rule never eats a prefix a narrower rule wanted.
RULES = [
    # This repository, however it was cloned -> plain relative path.
    (re.compile(re.escape(HERE + os.sep), re.I), ''),
    (re.compile(re.escape(HERE), re.I), '.'),
    # Agent scratch directories, including the per-session identifiers.
    (re.compile(r'[A-Za-z]:\\Users\\[^\\\r\n]+\\AppData\\Local\\Temp\\claude\\'
                r'[^\\\r\n]*\\[0-9a-f-]{8,}\\scratchpad\\?', re.I), '<scratch>\\\\'),
    (re.compile(r'C--Users-[A-Za-z0-9_.-]+'), '<session>'),
    # Interpreter locations. Both WindowsApps roots must be covered: the
    # per-user shim under AppData, and the machine-wide Store install under
    # Program Files, which tracebacks report. Only the first was here, so
    # --check called four tracked files clean while they carried the second.
    (re.compile(r'[A-Za-z]:\\Users\\[^\\\r\n]+\\AppData\\Local\\Microsoft\\'
                r'WindowsApps\\', re.I), '<python>\\\\'),
    (re.compile(r'[A-Za-z]:\\Program Files\\WindowsApps\\'
                r'PythonSoftwareFoundation\.Python\.[^\\\r\n]*\\', re.I),
     '<python>\\\\'),
    # Anything else under any user profile.
    (re.compile(re.escape(HOME + os.sep), re.I), '%USERPROFILE%\\\\'),
    (re.compile(r'[A-Za-z]:\\Users\\[^\\\r\n]+\\', re.I), '%USERPROFILE%\\\\'),
    (re.compile(r'/home/[^/\r\n]+/'), '$HOME/'),
]

SKIP_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip', '.gz', '.exe',
            '.dll', '.pyc', '.o', '.so'}

# This file spells the patterns out in full, so scrubbing it would rewrite the
# rules themselves -- a rule matches its own source. Never touch it.
SELF = os.path.basename(os.path.abspath(__file__))


def tracked_files():
    out = subprocess.run(['git', 'ls-files', '-z'], cwd=HERE,
                         capture_output=True, text=True, check=True).stdout
    return [f for f in out.split('\0') if f]


def open_by_another_process(path):
    """True if some live process holds this file open for writing.

    Rewriting such a file would race that writer. Detected by trying to open
    it exclusively; on Windows that fails while a writer holds the handle.
    """
    try:
        fh = os.open(path, os.O_RDWR)
    except OSError:
        return True
    os.close(fh)
    return False


def scrub(text):
    for pattern, repl in RULES:
        text = pattern.sub(repl, text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='report only; exit 1 if anything still needs scrubbing')
    ap.add_argument('--all', action='store_true',
                    help='also rewrite files a running process holds open')
    a = ap.parse_args()

    dirty, skipped, fixed = [], [], []
    for rel in tracked_files():
        if os.path.splitext(rel)[1].lower() in SKIP_EXT:
            continue
        if os.path.basename(rel) == SELF:
            continue
        path = os.path.join(HERE, rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8', errors='surrogateescape') as fh:
                text = fh.read()
        except (OSError, UnicodeDecodeError):
            continue

        cleaned = scrub(text)
        if cleaned == text:
            continue
        dirty.append(rel)

        if a.check:
            continue
        if not a.all and open_by_another_process(path):
            skipped.append(rel)
            continue
        with open(path, 'w', encoding='utf-8', errors='surrogateescape',
                  newline='') as fh:
            fh.write(cleaned)
        fixed.append(rel)

    if a.check:
        for rel in dirty:
            print(f'needs scrubbing: {rel}')
        print(f'{len(dirty)} file(s) carry machine-local paths')
        return 1 if dirty else 0

    for rel in fixed:
        print(f'scrubbed  {rel}')
    for rel in skipped:
        print(f'SKIPPED (in use, re-run later)  {rel}')
    print(f'{len(fixed)} scrubbed, {len(skipped)} skipped, '
          f'{len(dirty)} carried local paths')
    return 0


if __name__ == '__main__':
    sys.exit(main())
