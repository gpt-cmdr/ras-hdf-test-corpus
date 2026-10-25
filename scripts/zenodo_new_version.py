"""Create a new Zenodo version of the corpus record and upload a release's files.

Standard library only. The token comes from the ZENODO_TOKEN environment variable
and is never printed. The latest published version is resolved from the concept
record, so nothing needs updating after a version is published.

The new version is left as a DRAFT for the maintainer to review and publish on
zenodo.org, unless --publish is given. Zenodo versions are permanent once published.

    python scripts/zenodo_new_version.py --concept 23641995 --tag v1.0.2 --dir zenodo
    python scripts/zenodo_new_version.py ... --discard   # self-test: delete the draft afterwards
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://zenodo.org/api"


def call(method, url, token, data=None, content_type=None):
    headers = {"Authorization": f"Bearer {token}"}
    if content_type:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=3600) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"{method} {url} failed: HTTP {exc.code} {exc.read()[:500]!r}")
    return json.loads(body) if body else {}


def md5(path):
    digest = hashlib.md5()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--concept", required=True, help="Zenodo concept record id")
    parser.add_argument("--tag", required=True, help="release tag, for example v1.0.2")
    parser.add_argument("--dir", required=True, help="folder holding exactly the files to upload")
    parser.add_argument("--repo", default="gpt-cmdr/ras-hdf-test-corpus")
    parser.add_argument("--publish", action="store_true", help="publish the new version (permanent)")
    parser.add_argument("--discard", action="store_true", help="self-test: delete the draft at the end")
    args = parser.parse_args()
    token = os.environ.get("ZENODO_TOKEN", "").strip()
    if not token:
        raise SystemExit("ZENODO_TOKEN is not set")
    files = sorted(n for n in os.listdir(args.dir) if os.path.isfile(os.path.join(args.dir, n)))
    if not files:
        raise SystemExit(f"no files in {args.dir}")

    latest = call("GET", f"{API}/records/{args.concept}", token)
    latest_id = latest["id"]
    old_version = latest["metadata"].get("version", "")
    print(f"latest published version: record {latest_id} (version {old_version})")

    created = call("POST", f"{API}/deposit/depositions/{latest_id}/actions/newversion", token)
    draft_url = created["links"]["latest_draft"]
    draft = call("GET", draft_url, token)
    print(f"new-version draft: {draft['id']}")

    for entry in draft.get("files", []):
        call("DELETE", entry["links"]["self"], token)

    version = args.tag.lstrip("v")
    metadata = draft["metadata"]
    old_tag = f"v{old_version}" if old_version else None
    if old_tag:
        metadata["description"] = metadata.get("description", "").replace(old_tag, args.tag)
    metadata["version"] = version
    metadata["publication_date"] = datetime.date.today().isoformat()
    metadata["related_identifiers"] = [
        {"identifier": f"https://github.com/{args.repo}/tree/{args.tag}",
         "relation": "isSupplementTo", "resource_type": "software"},
        {"identifier": f"https://github.com/{args.repo}/releases/tag/{args.tag}",
         "relation": "isIdenticalTo", "resource_type": "dataset"},
    ]
    metadata.pop("doi", None)
    call("PUT", draft["links"]["self"], token, json.dumps({"metadata": metadata}).encode(), "application/json")

    bucket = draft["links"]["bucket"]
    local = {}
    for name in files:
        path = os.path.join(args.dir, name)
        local[name] = md5(path)
        with open(path, "rb") as stream:
            call("PUT", f"{bucket}/{name}", token, stream.read(), "application/octet-stream")
        print(f"uploaded {name} ({os.path.getsize(path)} bytes)")

    remote = call("GET", draft["links"]["self"], token)
    got = {entry["filename"]: entry["checksum"].split(":")[-1] for entry in remote["files"]}
    bad = sorted(set(local) ^ set(got)) + [n for n in files if got.get(n) != local[n]]
    if bad:
        raise SystemExit(f"checksum or file-list mismatch: {sorted(set(bad))}")
    print(f"verified {len(files)} files against Zenodo checksums")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if args.discard:
        call("DELETE", draft["links"]["self"], token)
        print("self-test: draft discarded")
        return
    if args.publish:
        published = call("POST", draft["links"]["publish"], token)
        line = f"Zenodo version published: https://doi.org/{published['doi']}"
    else:
        line = (f"Zenodo draft for {args.tag} is ready to review and publish: "
                f"https://zenodo.org/deposit/{draft['id']}")
    print(line)
    if summary:
        with open(summary, "a", encoding="utf-8") as stream:
            stream.write(line + "\n")


if __name__ == "__main__":
    sys.exit(main())
