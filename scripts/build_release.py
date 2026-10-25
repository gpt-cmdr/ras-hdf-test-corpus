#!/usr/bin/env python3
"""Stage, verify and package a ras-hdf-test-corpus release.

Subcommands
  stage    Materialise every published fixture into STAGE/fixtures/ from a private
           sources map (CLB only): full files are copied (or read from the HEC
           example zip), excerpts are rebuilt with excerpt_hdf.py. Every file must
           match its manifest SHA-256.
  verify   Check that STAGE/fixtures/ holds exactly the manifest's files, byte-exact.
  package  Verify, then write one deterministic .tar.gz per profile (split into
           parts below the GitHub 2 GiB asset limit), expected-values archives if
           STAGE/expected/ exists, and SHA256SUMS.

Usage
  python build_release.py stage   --manifest manifest.json --sources sources.local.json --stage STAGE [--zip66 PATH]
  python build_release.py verify  --manifest manifest.json --stage STAGE
  python build_release.py package --manifest manifest.json --stage STAGE --out DIST

Standard library only, except `stage`, which runs excerpt_hdf.py (h5py).
"""
import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

PROFILES = ("smoke", "core", "extended", "legacy")
PART_LIMIT = 1_900_000_000  # stay well below GitHub's 2 GiB per-asset limit
HERE = os.path.dirname(os.path.abspath(__file__))


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def load(manifest):
    with open(manifest, encoding="utf-8") as f:
        return json.load(f)


def stage(args):
    man, src = load(args.manifest), load(args.sources)
    bad = []
    for e in man["entries"]:
        s = src[e["id"]]
        dst = os.path.join(args.stage, *e["path"].split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and os.path.getsize(dst) == e["bytes"] and sha256_file(dst) == e["sha256"]:
            continue
        if s["mode"] == "excerpt":
            subprocess.run([sys.executable, "-I", os.path.join(HERE, "excerpt_hdf.py"), s["source"], dst] + s["excerpt_args"],
                           check=True, stdout=subprocess.DEVNULL)
            for extra in (dst + ".provenance.json",):
                if os.path.exists(extra):
                    os.remove(extra)
        elif s["source"].startswith("zip66!"):
            with zipfile.ZipFile(args.zip66) as z, open(dst, "wb") as f:
                f.write(z.read(s["source"][6:]))
        else:
            shutil.copyfile(s["source"], dst)
        got = sha256_file(dst)
        if got != e["sha256"] or os.path.getsize(dst) != e["bytes"]:
            bad.append((e["id"], got))
        print(("OK  " if got == e["sha256"] else "BAD ") + e["path"], flush=True)
    if bad:
        sys.exit(f"STOP: {len(bad)} staged files do not match the manifest: {bad[:5]}")


def verify(args):
    man = load(args.manifest)
    root = os.path.join(args.stage, "fixtures")
    want = {e["path"]: e for e in man["entries"]}
    have = set()
    for dp, _, fs in os.walk(root):
        for f in fs:
            have.add(os.path.relpath(os.path.join(dp, f), args.stage).replace(os.sep, "/"))
    extra, missing = sorted(have - set(want)), sorted(set(want) - have)
    bad = [p for p in sorted(set(want) & have)
           if os.path.getsize(os.path.join(args.stage, p)) != want[p]["bytes"]
           or sha256_file(os.path.join(args.stage, p)) != want[p]["sha256"]]
    if extra or missing or bad:
        sys.exit(f"STOP: extra={extra[:5]} missing={missing[:5]} hash_mismatch={bad[:5]}")
    print(f"verified {len(want)} fixtures byte-exact")
    return man


def _tar(members, out_path):
    """Deterministic tar.gz: sorted names, zeroed mtime/owner, gzip mtime 0."""
    with open(out_path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, compresslevel=6) as gz, \
            tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as t:
        for arc, full in sorted(members):
            ti = t.gettarinfo(full, arcname=arc)
            ti.mtime, ti.uid, ti.gid, ti.uname, ti.gname, ti.mode = 0, 0, 0, "", "", 0o644
            with open(full, "rb") as f:
                t.addfile(ti, f)


def _parts(members, limit):
    parts, cur, size = [], [], 0
    for arc, full in sorted(members):
        n = os.path.getsize(full)
        if cur and size + n > limit:
            parts.append(cur)
            cur, size = [], 0
        cur.append((arc, full))
        size += n
    if cur:
        parts.append(cur)
    return parts


def package(args):
    man = verify(args)
    os.makedirs(args.out, exist_ok=True)
    assets = []
    for prof in PROFILES:
        members = [(e["path"], os.path.join(args.stage, e["path"])) for e in man["entries"] if prof in e["profiles"]]
        parts = _parts(members, PART_LIMIT)
        for i, part in enumerate(parts):
            name = f"{prof}.tar.gz" if len(parts) == 1 else f"{prof}.part{i + 1:02d}.tar.gz"
            _tar(part, os.path.join(args.out, name))
            assets.append(name)
            print(name, os.path.getsize(os.path.join(args.out, name)), flush=True)
    for sub, name in (("expected", "expected.tar.gz"), ("expected-parquet", "expected-parquet.tar.gz")):
        root = os.path.join(args.stage, sub)
        if os.path.isdir(root):
            members = [(os.path.relpath(os.path.join(dp, f), args.stage).replace(os.sep, "/"), os.path.join(dp, f))
                       for dp, _, fs in os.walk(root) for f in fs]
            _tar(members, os.path.join(args.out, name))
            assets.append(name)
    shutil.copyfile(args.manifest, os.path.join(args.out, "manifest.json"))
    assets.append("manifest.json")
    with open(os.path.join(args.out, "SHA256SUMS"), "w", newline="\n") as f:
        for a in sorted(assets):
            f.write(f"{sha256_file(os.path.join(args.out, a))}  {a}\n")
    print("wrote SHA256SUMS for", len(assets), "assets")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["stage", "verify", "package"])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--sources")
    ap.add_argument("--zip66")
    ap.add_argument("--out")
    a = ap.parse_args()
    {"stage": stage, "verify": verify, "package": package}[a.cmd](a)


if __name__ == "__main__":
    main()
