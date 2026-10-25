#!/usr/bin/env python3
"""Fetch one ras-hdf-test-corpus profile from a release tag and verify it.

Standard library only. Downloads SHA256SUMS, manifest.json and the profile
archive(s) from https://github.com/<repo>/releases/download/<tag>/ (no API
calls), checks each archive against SHA256SUMS, extracts it into DEST, and checks
every extracted file's size and SHA-256 against manifest.json. Exits non-zero on
any mismatch.

Usage:
  python fetch_corpus.py --tag v1.0.0 --profile smoke --dest .corpus [--expected] [--repo gpt-cmdr/ras-hdf-test-corpus]
"""
import argparse
import hashlib
import json
import os
import shutil
import tarfile
import time
import urllib.request

PROFILES = ("smoke", "core", "extended", "legacy")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def download(url, dst, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ras-hdf-test-corpus-fetch/1"})
            with urllib.request.urlopen(req, timeout=120) as r, open(dst + ".part", "wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            os.replace(dst + ".part", dst)
            return
        except Exception as e:  # network hiccups and 5xx: retry with backoff
            if i == tries - 1:
                raise SystemExit(f"download failed: {url}: {e}")
            time.sleep(2 ** i * 3)


def safe_extract(tar_path, dest):
    with tarfile.open(tar_path, "r:gz") as t:
        root = os.path.realpath(dest)
        for m in t.getmembers():
            target = os.path.realpath(os.path.join(dest, m.name))
            if not (target == root or target.startswith(root + os.sep)) or not (m.isfile() or m.isdir()):
                raise SystemExit(f"unsafe archive member: {m.name}")
        if hasattr(tarfile, "data_filter"):
            t.extractall(dest, filter="data")
        else:
            t.extractall(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--profile", required=True, choices=PROFILES)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--repo", default="gpt-cmdr/ras-hdf-test-corpus")
    ap.add_argument("--expected", action="store_true", help="also fetch expected.tar.gz")
    ap.add_argument("--base-url", help="override the release download URL (mirrors, testing)")
    a = ap.parse_args()
    base = a.base_url.rstrip("/") + "/" if a.base_url else f"https://github.com/{a.repo}/releases/download/{a.tag}/"
    dl = os.path.join(a.dest, ".download", a.tag)
    os.makedirs(dl, exist_ok=True)
    for name in ("SHA256SUMS", "manifest.json"):
        download(base + name, os.path.join(dl, name))
    sums = {}
    for line in open(os.path.join(dl, "SHA256SUMS"), encoding="utf-8"):
        if line.strip():
            h, n = line.split(None, 1)
            sums[n.strip().lstrip("*")] = h
    if sums.get("manifest.json") != sha256_file(os.path.join(dl, "manifest.json")):
        raise SystemExit("manifest.json does not match SHA256SUMS")
    wanted = sorted(n for n in sums if n == f"{a.profile}.tar.gz" or n.startswith(f"{a.profile}.part"))
    if a.expected:
        wanted.append("expected.tar.gz")
    if not wanted:
        raise SystemExit(f"no archive for profile {a.profile} in SHA256SUMS")
    for name in wanted:
        p = os.path.join(dl, name)
        if not (os.path.exists(p) and sha256_file(p) == sums[name]):
            download(base + name, p)
        got = sha256_file(p)
        if got != sums[name]:
            raise SystemExit(f"{name}: sha256 {got} != SHA256SUMS {sums[name]}")
        print(f"verified {name}")
        safe_extract(p, a.dest)
    man = json.load(open(os.path.join(dl, "manifest.json"), encoding="utf-8"))
    bad, n = [], 0
    for e in man["entries"]:
        if a.profile not in e["profiles"]:
            continue
        n += 1
        p = os.path.join(a.dest, *e["path"].split("/"))
        if not os.path.exists(p) or os.path.getsize(p) != e["bytes"] or sha256_file(p) != e["sha256"]:
            bad.append(e["path"])
    if bad:
        raise SystemExit(f"{len(bad)} files failed verification, e.g. {bad[:5]}")
    shutil.copyfile(os.path.join(dl, "manifest.json"), os.path.join(a.dest, "manifest.json"))
    print(f"{a.profile}@{a.tag}: {n} files verified in {os.path.abspath(a.dest)}")


if __name__ == "__main__":
    main()
