# ras-hdf-test-corpus

Versioned, hashed HEC-RAS HDF test fixtures with precomputed expected values. They are for:

- the Rust HEC-RAS HDF engine, [`gpt-cmdr/ras-commander-fast-hdf`](https://github.com/gpt-cmdr/ras-commander-fast-hdf);
- [`ras-commander`](https://github.com/gpt-cmdr/ras-commander);
- third-party readers such as [terrio](https://github.com/opengeos/terrio).

The fixtures are real HEC-RAS files: HEC example projects run by CLB in HEC-RAS 7.0.1, public FEMA eBFE and Texas GLO RBFS models (some computed by CLB in HEC-RAS 7.0.1), and two CLB models used with permission. Some are excerpts that keep HEC-RAS's exact stored layouts, and a few are small synthetic files. **The HDF files are not in git.** They ship only as assets of immutable GitHub Releases. This repository holds the manifest, the scripts that build and verify the release, and the fetch script for CI.

## Support policy

- **CI tests HEC-RAS 7.0.1.** The `smoke` and `core` profiles contain only 7.0.1 fixtures: files written by HEC-RAS 7.0.1 (plans, geometries, RAS Mapper layers, terrain, stored maps), input layers used by a recorded HEC-RAS 7.0.1 `compute_plan` run, and synthetic files. Every per-PR coverage requirement is met by them.
- **Older versions (HEC-RAS 5.0.x–7.0) are best effort.** Their files are in `legacy`, which only the engine's own best-effort suites use.
- **Unsupported layouts must be refusals, never wrong data.** A reader that does not recognise a layout should raise a clear error rather than return guessed values. The expected values record such refusals as `error` cases.
- When HEC releases a new HEC-RAS version, its fixtures replace the 7.0.1 set in a new major version, and the 7.0.1 files move to `legacy`.

## Profiles

| Profile | Who downloads it | v1.0.1 | Caps |
|---|---|---|---|
| `smoke` | terrio and other third-party CI | 23 files, 34.9 MB | ≤ 10 MB per file, about 50 MB total; 7.0.1 only |
| `core` | engine / ras-commander per-PR CI (includes `smoke`) | 77 files, 199.1 MB | ≤ 25 MB per file; 7.0.1 only |
| `extended` | nightly / manual | 10 files, 313.1 MB | 7.0.1 files above the core cap |
| `legacy` | engine best-effort suites only | 60 files, 82.5 MB | ≤ 25 MB per file, about 100 MB total; HEC-RAS 5.0.5–7.0 |
| `archive` | not republished | 13 files | older files above the legacy cap; listed in `manifest.json` → `not_published` |
| `external` | upstream | 1 file | LWI Lower Calcasieu (CC BY 4.0); fetch from the URL in its provenance |

Each release asset `<profile>.tar.gz` contains `fixtures/<path>` for every file in that profile. `core.tar.gz` already includes the `smoke` files.

## Download and verify

The fetch script uses only the Python standard library:

```bash
python scripts/fetch_corpus.py --tag v1.0.1 --profile smoke --dest .corpus
```

It downloads `SHA256SUMS`, `manifest.json` and the profile archive(s) from the release; checks each archive against `SHA256SUMS`; extracts it; and checks every extracted file's size and SHA-256 against `manifest.json`. It exits non-zero on any mismatch. Add `--expected` to also fetch `expected.tar.gz`.

The equivalent manual steps:

```bash
TAG=v1.0.1; BASE=https://github.com/gpt-cmdr/ras-hdf-test-corpus/releases/download/$TAG
curl -fsSLO $BASE/SHA256SUMS -O $BASE/manifest.json -O $BASE/smoke.tar.gz
grep ' smoke.tar.gz$' SHA256SUMS | sha256sum -c -
tar -xzf smoke.tar.gz
```

In GitHub Actions, cache the destination with `actions/cache`, keyed on the tag.

## Expected values (no Python needed by consumers)

`expected.tar.gz` holds:
- `expected/<fixture-id>/oracle.json` for every HDF fixture;
- `expected/INDEX.json`, which lists each oracle's SHA-256 and the fixture SHA-256 it was computed from.

Each case records the ras-commander call, its arguments and a canonical SHA-256 digest of the result, plus shape, dtype, statistics and samples. Expected refusals are recorded as `error`. The canonical encoding is specified at the top of `scripts/generate_expected.py` (schema `ras-oracle/1`), so a consumer needs only a JSON parser and SHA-256.

A case runs only if its group is one of the fixture's `test_groups` in `manifest.json`. `expected-parquet.tar.gz` has full tabular values for debugging and is not needed in CI.

## Manifest

`manifest.json` lists, per file:
- `id`, release `path`, `sha256`, `bytes`, `profiles`;
- `writer` (the HEC-RAS version that wrote it, or how it qualifies as 7.0.1);
- root attributes and detection truth (`detection.expected_kind`);
- `features`, `property_tables` and `test_groups`;
- any `known_issue`;
- a `provenance` block: source program, public download location, zip and in-zip path, source SHA-256, attribution, licence and, for CLB runs, the HEC-RAS version, method and plan changes.

Run receipts are in `provenance/`. `coverage_701` records which file satisfies each 7.0.1 coverage requirement.

## Versioning

Tags follow semantic versioning, and releases are immutable:
- **patch:** fixtures added;
- **minor:** profile membership changed;
- **major:** bytes removed or replaced, or a new HEC-RAS version.

Expected values are regenerated only when the corpus version changes. Releases are published only by the tag workflow (`.github/workflows/release.yml`).

## Licence and attribution

CLB Engineering Corporation's contribution is dedicated to the public domain under CC0 1.0 (`LICENSE`). That covers the excerpts, synthetic files, manifest, expected values and scripts. Upstream sources keep their own status and attribution; see `NOTICE`.

## Citation

Each release is intended to be archived on Zenodo with a version DOI. That will be added once the repository owner enables the integration.
