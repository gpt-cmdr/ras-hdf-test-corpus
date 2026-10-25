# scripts

**For consumers**
- `fetch_corpus.py` downloads one profile from a release tag, checks `SHA256SUMS`, extracts it, and checks every file against `manifest.json`. Standard library only.

**Release build** (run by CLB, plus `.github/workflows/release.yml`)
- `build_release.py` has three subcommands:
  - `stage` materialises the fixtures from CLB's private sources map. It copies full files, reads members from the HEC example zip, and rebuilds excerpts.
  - `verify` checks the staged files byte-exact against the manifest.
  - `package` builds the deterministic per-profile `.tar.gz` archives, the expected-value archives and `SHA256SUMS`.
- `generate_expected.py` writes the precomputed expected values (`expected/<id>/oracle.json`, schema `ras-oracle/1`, plus optional Parquet). In `--manifest` mode, a case runs only when its group is in the fixture's `test_groups`. Pinned environment: `requirements-oracle-generator.lock.txt`.
- `excerpt_hdf.py` and `verify_excerpt.py` create and check excerpts. Excerpts copy objects with H5Ocopy, so dtypes, chunking, filters and attributes are preserved, and time axes are truncated (default `--rows 8 --keep-last`). `verify_excerpt.py` byte-compares every attribute and dataset with the source. Excerpts are byte-reproducible with h5py 3.15.1 / HDF5 1.14.6, the environment used for v1.0.0.

**Manifest**
- `build_proposed_manifest.py` assembles the manifest from CLB's local inputs and enforces the rules:
  - the size caps;
  - the 7.0.1-only `smoke`/`core` rule;
  - the property-table drop rule;
  - 7.0.1 coverage, and that fixtures with a known issue get no test group needing faces or tables.
- Supporting modules: `property_table_census.py` and `coverage_701.py`.
- `make_release_manifest.py` turns that into the published `manifest.json`. It assigns release paths and removes local filesystem paths.
- `excerpt_plan.py` is the excerpt recipe table.

**How fixtures were made** (receipts in `../provenance/`)
- `run_6x_examples.py` runs HEC example plans in an installed HEC-RAS through ras-commander (`RasCmdr.compute_plan`) on fresh copies, with recorded plan-line changes.
- `run_507_examples.py`: HEC-RAS 5.0.7 runs through `RasControl` (legacy profile).
- `run_ebfe_rr_701.py` re-preprocesses public eBFE models in HEC-RAS 7.0.1.
- `author_701_layers.py`, `author_701_terrain.py`, `author_701_storedmap.py` and `author_701_reflines.py` author 7.0.1 RAS Mapper layers, terrain, a stored map and reference lines/points.
- `make_synthetic_fixtures.py` builds the synthetic fixtures (Albers CRS, `Infiltration Parameters`, legacy structures layout).
- `make_perf_fixture.py` generates large performance files in-job. Never shipped.
- `scan_ebfe_features.py` was used to search local eBFE files for refinement regions and layers.

These scripts record what was run. Most of them need HEC-RAS on Windows and CLB's local inputs, so they are not expected to run in CI.
