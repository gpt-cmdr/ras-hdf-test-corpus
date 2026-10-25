"""Generic deny-list check for published artefacts.

The tokens live in a local, git-ignored file (CORPUS_DENYLIST, or .denylist.local.txt
next to this module), so excluded material is never named in the repository. Matches
that are HEC-RAS timestamps (for example "15MAR2021 09:03:32") are not hits.

Usage as a script: python -I denylist_check.py PATH [PATH ...]   (files or directories;
text and binary files are scanned; exits 1 on any hit)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def tokens():
    p = os.environ.get("CORPUS_DENYLIST") or os.path.join(HERE, ".denylist.local.txt")
    if not os.path.exists(p):
        raise SystemExit(f"deny list not found: {p} (set CORPUS_DENYLIST)")
    return [t.strip() for t in open(p, encoding="utf-8") if t.strip()]


def hits(data, toks=None):
    """Return the deny-list hits in bytes or str, ignoring HEC-RAS timestamps."""
    if isinstance(data, str):
        data = data.encode("utf-8", "replace")
    out = []
    for t in toks or tokens():
        for m in re.finditer(re.escape(t.encode()), data, re.IGNORECASE):
            ctx = data[max(0, m.start() - 2):m.end() + 9]
            if re.fullmatch(rb"\d\d" + re.escape(t.encode()) + rb" \d\d:\d\d:\d\d", ctx, re.IGNORECASE):
                continue  # a timestamp such as 15MAR2021 09:03:32
            out.append((t, data[max(0, m.start() - 30):m.end() + 30]))
    return out


def scan(paths):
    toks, bad = tokens(), []
    for root in paths:
        files = [root] if os.path.isfile(root) else [os.path.join(dp, f) for dp, _, fs in os.walk(root)
                                                      if ".git" not in dp.split(os.sep) for f in fs]
        for f in files:
            if os.path.basename(f) == ".denylist.local.txt":
                continue
            h = hits(open(f, "rb").read(), toks)
            if h:
                bad.append((f, len(h)))
    return bad


if __name__ == "__main__":
    bad = scan(sys.argv[1:])
    for f, n in bad:
        print(f"HIT {n} {f}")
    print(f"{len(bad)} files with deny-list hits")
    sys.exit(1 if bad else 0)
