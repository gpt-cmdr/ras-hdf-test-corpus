"""Convert proposed_manifest.json into the published manifest.json plus a private sources map.

Published manifest: every entry gets a release `path` (under fixtures/), the published
`sha256` and `bytes`, and its profiles. Local filesystem paths are removed
(`local_source`, `run_copy`) or mapped to stable labels. Receipts referenced by
provenance are copied, with local paths sanitised, to OUT/provenance/.
Private map (not published): entry id -> local source path, mode and excerpt args.

Usage: python -I make_release_manifest.py OUT_REPO_DIR SOURCES_JSON VERSION
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from denylist_check import hits  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISHED_PROFILES = ("smoke", "core", "extended", "legacy")

PREFIX_MAP = [
    ("D:/CLB-Dev/ras701-corpus/", "provenance/ras701-corpus/"),
    ("D:/CLB-Dev/ras507-corpus/", "provenance/ras507-corpus/"),
    ("D:\\CLB-Dev/ras701-corpus/", "provenance/ras701-corpus/"),
    ("H:/eBFE_Audit_Recovery_20261008/backfill_recovery_20261009/", "clb-local:ebfe-extraction/"),
    ("H:/Jacob/", "clb-local:jacob-beatty/"),
    ("D:/CLB-Dev/ras-native-release/fixtures/", "clb-local:fixtures/"),
    ("D:/CLB-Dev/release-020/rc-rel", "ras-commander 0.108.0 source"),
    ("D:\\CLB-Dev/release-020/rc-rel", "ras-commander 0.108.0 source"),
]
DROP_KEYS = {"local_source", "run_copy"}
RECEIPTS = [
    "D:/CLB-Dev/ras701-corpus/runs/run_7.0.1_results.json",
    "D:/CLB-Dev/ras507-corpus/runs/run_507_results.json",
    "D:/CLB-Dev/ras701-corpus/layers/BaldEagleCrkMulti2D/author_701_layers.json",
    "D:/CLB-Dev/ras701-corpus/terrain701/author_701_terrain.json",
    "D:/CLB-Dev/ras701-corpus/storedmap/Muncie_p03/author_701_storedmap.json",
    "D:/CLB-Dev/ras701-corpus/reflines/RECEIPT.md",
    "D:/CLB-Dev/ras701-corpus/reflines/author_701_reflines.json",
    "D:/CLB-Dev/ras701-corpus/ebfe-stream248/RECEIPT.json",
]
DRIVE = re.compile(r"(?:(?<![A-Za-z])[A-Za-z]:[\\/]|/mnt/)[^\"'\n;,]*")


def sanitize_str(s):
    for a, b in PREFIX_MAP:
        s = s.replace(a, b)
    # anything still drive-rooted: keep only the last two components
    return DRIVE.sub(lambda m: "clb-local:" + "/".join(re.split(r"[\\/]+", m.group(0).rstrip(" )"))[-2:]), s)


def sanitize(v):
    if isinstance(v, dict):
        return {k: sanitize(x) for k, x in v.items() if k not in DROP_KEYS}
    if isinstance(v, list):
        return [sanitize(x) for x in v]
    if isinstance(v, str):
        return sanitize_str(v)
    return v


def release_path(e, by_id):
    src = e["local_source"]
    base = os.path.basename(src[6:] if src.startswith("zip66!") else src)
    ext = os.path.splitext(base)[1].lower()
    group = e.get("companion_of")
    if group is None and any(x.get("companion_of") == e["id"] for x in by_id.values()):
        group = e["id"]
    if e["id"].startswith("storedmap701/"):
        group = e["id"].rsplit(".", 1)[0]
    if group:
        return f"fixtures/{group}/{base}"
    return f"fixtures/{e['id']}" + ("" if e["id"].lower().endswith(ext) else ext)


def main(out, sources_json, version):
    d = json.load(open(os.path.join(HERE, "proposed_manifest.json")))
    by_id = {e["id"]: e for e in d["entries"]}
    entries, sources = [], {}
    for e in d["entries"]:
        if not set(e["profiles"]) & set(PUBLISHED_PROFILES):
            continue
        p = release_path(e, by_id)
        sha = e.get("excerpt_sha256_measured") or e["source_sha256"]
        sources[e["id"]] = {"source": e["local_source"], "mode": e["mode"], "excerpt_args": e.get("excerpt_args"),
                            "path": p, "sha256": sha, "bytes": e["published_bytes"]}
        pub = {"id": e["id"], "path": p, "sha256": sha, "bytes": e["published_bytes"], **sanitize(e)}
        entries.append(pub)
    paths = [x["path"] for x in entries]
    assert len(paths) == len(set(paths)), "duplicate release paths"
    not_published = [{"id": e["id"], "profile": e["profile"], "bytes": e["published_bytes"],
                      "reason": "archive: not republished in this release" if e["profile"] == "archive"
                      else "external: fetch from the upstream URL in provenance",
                      "provenance": sanitize(e["provenance"])}
                     for e in d["entries"] if not set(e["profiles"]) & set(PUBLISHED_PROFILES)]
    man = {"schema": "ras-hdf-test-corpus/manifest/1", "version": version,
           "repository": "gpt-cmdr/ras-hdf-test-corpus",
           "support_policy": d["support_policy"], "licence": d["licence"], "caps": d["caps"],
           "profiles": {p: {"files": sum(p in x["profiles"] for x in entries),
                            "bytes": sum(x["bytes"] for x in entries if p in x["profiles"])} for p in PUBLISHED_PROFILES},
           "excerpt_default": d["excerpt_default"], "property_table_rule": d["property_table_rule"],
           "property_table_coverage": sanitize(d["property_table_coverage"]),
           "coverage_701": d["coverage_701"], "entries": entries, "not_published": not_published,
           "dropped": d["dropped"]}
    blob = json.dumps(man, indent=1, sort_keys=False)
    leftovers = sorted(set(re.findall(r"(?<![A-Za-z])[A-Za-z]:[\\/][^\"]{0,40}", blob)))
    assert not leftovers, leftovers[:10]
    assert "Data Library" not in blob and not hits(blob), "deny-list hit in the published manifest"
    open(os.path.join(out, "manifest.json"), "w", encoding="utf-8").write(blob + "\n")
    json.dump(sources, open(sources_json, "w"), indent=1)
    pd = os.path.join(out, "provenance")
    for r in RECEIPTS:
        rel = sanitize_str(r)
        dst = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "w", encoding="utf-8").write(sanitize_str(open(r, encoding="utf-8", errors="replace").read()))
    ex = json.load(open(os.path.join(HERE, "excerpt_measurements.json")))
    used = {e.get("excerpt_recipe") for e in d["entries"] if e.get("excerpt_recipe")}
    json.dump(sanitize({k: v for k, v in ex.items() if k in used}),
              open(os.path.join(pd, "excerpt_measurements.json"), "w"), indent=1)
    print(len(entries), "published entries;", len(not_published), "not published;", man["profiles"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
