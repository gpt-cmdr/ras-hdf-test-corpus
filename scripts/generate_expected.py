"""Prototype: precompute expected values for corpus fixtures with ras-commander (h5py).

Writes, per fixture, ``expected/<fixture-id>/oracle.json``: a self-describing list
of cases. Each case records the ras-commander call, a canonical SHA-256 digest of
the result, shape/dtype, summary statistics and head/tail samples. A Rust (or any)
consumer recomputes the same canonical digest from its own result. It needs only
a JSON parser and SHA-256: no Python, HDF5 bindings or GIS stack.

Optional ``--parquet`` also writes ``<case>.parquet`` with full tabular values for
debugging. These are published as a separate asset, not needed by CI.

Canonical encoding (schema "ras-oracle/1"), hashed with SHA-256:
  numeric arrays   C order, little-endian, dtype as returned by ras-commander;
                   every NaN rewritten to the canonical quiet NaN of its width.
  bool             uint8 0/1.
  strings          UTF-8, trailing NUL/space stripped, each value prefixed by its
                   byte length as uint32 LE.
  datetimes        int64 milliseconds since 1970-01-01T00:00:00, as stored (no tz).
  tables           columns in sorted name order; per column: name (string rule),
                   then the column bytes. The table digest hashes the concatenation.
  geometry         ISO WKB, little-endian, 2D, one per row, each prefixed by its
                   uint32 LE length. A second digest "geom_normalized" uses
                   shapely.normalize() first, so ring start and orientation
                   differences can be diagnosed separately.

Usage:
  python -B generate_expected.py RAS_COMMANDER_SRC OUTDIR FIXTURE_ID=PATH[::EXPECTED_KIND] [...] [--parquet]
  python -B generate_expected.py --manifest manifest.json --stage STAGE OUTDIR [--parquet-out DIR]
RAS_COMMANDER_SRC "-" uses the installed ras-commander. In manifest mode the fixture
list, paths, expected kinds and test groups come from manifest.json, and a case runs
only if its group is one of the fixture's test groups ("geometry_features" admits the
face-free geometry cases: BC lines and refinement regions).
"""
import hashlib
import json
import os
import struct
import sys
import warnings

import numpy as np

SCHEMA = "ras-oracle/1"


def _u32(n):
    return struct.pack("<I", n)


def canon_array(a):
    a = np.asarray(a)
    if a.dtype.kind == "M":
        return a.astype("datetime64[ms]").astype("<i8").tobytes(), "datetime64[ms]"
    if a.dtype.kind in "SUO":
        out = bytearray()
        for x in a.ravel():
            if isinstance(x, bytes):
                x = x.decode("latin-1")
            x = "" if x is None else str(x)
            b = x.rstrip("\x00 ").encode("utf-8")
            out += _u32(len(b)) + b
        return bytes(out), "str"
    if a.dtype.kind == "b":
        return a.astype("u1").tobytes(), "bool"
    if a.dtype.kind == "f":
        a = np.ascontiguousarray(a.astype(a.dtype.newbyteorder("<")))
        a = a.copy()
        a[np.isnan(a)] = np.nan  # canonical quiet NaN
        return a.tobytes(), a.dtype.str
    if a.dtype.kind in "iu":
        return np.ascontiguousarray(a.astype(a.dtype.newbyteorder("<"))).tobytes(), a.dtype.str
    if a.dtype.names:
        out = bytearray()
        for n in sorted(a.dtype.names):
            b, _ = canon_array(a[n])
            out += canon_array(np.array([n]))[0] + b
        return bytes(out), "compound"
    raise TypeError(f"unsupported dtype {a.dtype}")


def stats(a):
    a = np.asarray(a)
    if a.dtype.kind in "fiu" and a.size:
        f = a.astype("f8")
        fin = f[np.isfinite(f)]
        return {"min": float(fin.min()) if fin.size else None, "max": float(fin.max()) if fin.size else None,
                "nan_count": int(np.isnan(f).sum()), "sum": float(fin.sum()) if fin.size else 0.0}
    return {}


def sample(a, n=3):
    a = np.asarray(a)
    if a.ndim == 0 or a.size == 0:
        return {}
    def j(x):
        x = np.asarray(x)
        if x.dtype.kind == "M":
            return x.astype("datetime64[ms]").astype(str).tolist()
        if x.dtype.kind == "S":
            return [v.decode("latin-1") for v in x.ravel()]
        if x.dtype.kind == "f":
            return [None if not np.isfinite(v) else float(v) for v in x.ravel()[:50]]
        return x.ravel()[:50].tolist()
    return {"head": j(a[:n]), "tail": j(a[-n:])}


def digest_value(v):
    """Return a JSON-able record for any ras-commander return value."""
    import pandas as pd
    rec = {}
    if v is None:
        return {"kind": "none"}
    if isinstance(v, (str, int, float, bool)):
        return {"kind": "scalar", "value": v}
    if isinstance(v, dict):
        return {"kind": "mapping", "keys": sorted(map(str, v)),
                "items": {str(k): digest_value(x) for k, x in list(v.items())[:200]}}
    if isinstance(v, (list, tuple)) and not (v and isinstance(v[0], (int, float))):
        return {"kind": "sequence", "len": len(v), "items": [digest_value(x) for x in list(v)[:50]]}
    if hasattr(v, "dims") and hasattr(v, "values") and not isinstance(v, pd.DataFrame):  # xarray
        rec = digest_value(np.asarray(v.values))
        rec.update(kind="xarray", dims=list(v.dims),
                   coords={str(k): digest_value(np.asarray(c.values)) for k, c in v.coords.items()})
        return rec
    if isinstance(v, pd.DataFrame):
        geom_col = getattr(v, "_geometry_column_name", None) if hasattr(v, "geometry") else None
        h = hashlib.sha256()
        cols = {}
        for c in sorted(map(str, v.columns)):
            col = v[c] if c in v.columns else v[[x for x in v.columns if str(x) == c][0]]
            if c == geom_col:
                continue
            arr = np.asarray(col.to_numpy())
            if arr.dtype == object:
                try:
                    arr = arr.astype("U")
                except Exception:
                    arr = np.array([repr(x) for x in arr])
            b, dt = canon_array(arr)
            h.update(canon_array(np.array([c]))[0] + b)
            cols[c] = {"dtype": dt, "sha256": hashlib.sha256(b).hexdigest(), **stats(arr), **sample(arr)}
        rec = {"kind": "table", "rows": int(len(v)), "columns": sorted(map(str, v.columns)),
               "sha256": h.hexdigest(), "column_digests": cols,
               "index": digest_value(np.asarray(v.index))}
        if geom_col:
            import shapely
            g = v.geometry.values
            wkb = shapely.to_wkb(np.asarray(g), output_dimension=2, byte_order=1, flavor="iso")
            nwkb = shapely.to_wkb(shapely.normalize(np.asarray(g)), output_dimension=2, byte_order=1, flavor="iso")
            hb = hashlib.sha256(b"".join(_u32(len(x)) + x for x in wkb)).hexdigest()
            hn = hashlib.sha256(b"".join(_u32(len(x)) + x for x in nwkb)).hexdigest()
            rec["geometry"] = {"column": geom_col, "wkb_sha256": hb, "geom_normalized_sha256": hn,
                               "types": sorted(set(shapely.get_type_id(np.asarray(g)).tolist())),
                               "total_coordinates": int(shapely.get_num_coordinates(np.asarray(g)).sum()),
                               "bounds": [float(x) for x in np.asarray(v.total_bounds)],
                               "crs": str(v.crs) if v.crs is not None else None,
                               "head_wkt": [x.wkt[:300] for x in g[:2]]}
        return rec
    if isinstance(v, pd.Series):
        return digest_value(v.to_frame(name=str(v.name)))
    a = np.asarray(v)
    b, dt = canon_array(a)
    return {"kind": "array", "dtype": dt, "shape": list(a.shape),
            "sha256": hashlib.sha256(b).hexdigest(), **stats(a), **sample(a)}


# Oracle groups: (group, Class, method, args builder, extra deps beyond h5py/numpy/pandas)
# args builder receives (fixture_path, h5py.File) and returns a list of arg lists.
def _areas(h):
    if "Geometry/2D Flow Areas/Attributes" not in h:
        return []
    return [n.decode().strip() for n in h["Geometry/2D Flow Areas/Attributes"]["Name"]]


# (group, Class, method, args builder, extra deps beyond h5py/numpy/pandas).
# Extra deps reflect probe_oracle_deps.py on ras-commander 0.97.0 (2026-10-24).
# Groups: detection, metadata, tables -> core deps only; timeseries -> +xarray;
# geometry -> +geopandas/shapely/pyproj.
def _plan(h):
    return "Plan Data" in h


def _has(h, g):
    return g in h


TS = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/"
CASES = [
    ("metadata", "HdfBase", "get_simulation_start_time", lambda p, h: [[p]] if _plan(h) else [], []),
    ("metadata", "HdfBase", "get_2d_flow_area_names_and_counts", lambda p, h: [[p]] if _areas(h) else [], []),
    ("metadata", "HdfBase", "get_projection", lambda p, h: [[p]] if "Geometry" in h or "Plan Data" in h else [], []),
    ("metadata", "HdfPlan", "get_plan_information", lambda p, h: [[p]] if _plan(h) else [], []),
    ("metadata", "HdfResultsPlan", "get_unsteady_info", lambda p, h: [[p]] if _has(h, "Results/Unsteady") else [], []),
    ("metadata", "HdfResultsPlan", "get_volume_accounting", lambda p, h: [[p]] if _has(h, "Results/Unsteady/Summary/Volume Accounting") else [], []),
    ("tables", "HdfResultsPlan", "get_steady_wse", lambda p, h: [[p]] if _has(h, "Results/Steady") else [], []),
    ("tables", "HdfHydraulicTables", "get_all_xs_htabs", lambda p, h: [[p]] if _has(h, "Geometry/Cross Sections") else [], []),
    ("tables", "HdfMesh", "get_mesh_area_attributes", lambda p, h: [[p]] if _areas(h) else [], []),
    ("tables", "HdfStruc1D", "list_1d_structures", lambda p, h: [[p]] if _has(h, "Geometry/Structures") and _has(h, "Results") else [], []),
    ("tables", "HdfResultsSediment", "is_sediment_plan", lambda p, h: [[p]] if _has(h, "Results/Unsteady") else [], []),
    ("tables", "HdfInfiltration", "get_infiltration_layer_data",
     lambda p, h: [[p]] if h.attrs.get("LC Type", b"").startswith(b"Infiltration") else [], []),
    ("tables", "HdfLandCover", "get_landcover_raster_map",
     lambda p, h: [[p]] if h.attrs.get("LC Type", b"") in (b"LandCover", b"Soils") else [], []),
    ("timeseries", "HdfResultsMesh", "get_mesh_timeseries",
     lambda p, h: [[p, a, "Water Surface"] for a in _areas(h) if _has(h, TS + "2D Flow Areas/" + a + "/Water Surface")], ["xarray"]),
    ("timeseries", "HdfResultsXsec", "get_xsec_timeseries", lambda p, h: [[p]] if _has(h, TS + "Cross Sections") else [], ["xarray"]),
    ("timeseries", "HdfResultsXsec", "get_ref_lines_timeseries", lambda p, h: [[p]] if _has(h, TS + "Reference Lines") else [], ["xarray"]),
    ("geometry", "HdfResultsMesh", "get_mesh_max_ws", lambda p, h: [[p]] if _has(h, "Results/Unsteady") and _areas(h) else [], ["geopandas", "shapely", "pyproj"]),
    ("geometry", "HdfMesh", "get_mesh_cell_points", lambda p, h: [[p]] if _areas(h) and _has(h, "Geometry/2D Flow Areas/" + _areas(h)[0] + "/Cells Center Coordinate") else [], ["geopandas", "shapely", "pyproj"]),
    ("geometry", "HdfMesh", "get_mesh_cell_polygons", lambda p, h: [[p]] if _areas(h) and _has(h, "Geometry/2D Flow Areas/" + _areas(h)[0] + "/FacePoints Coordinate") else [], ["geopandas", "shapely", "pyproj"]),
    ("geometry", "HdfBndry", "get_bc_lines", lambda p, h: [[p]] if _has(h, "Geometry/Boundary Condition Lines") else [], ["geopandas", "shapely", "pyproj"]),
    ("geometry", "HdfBndry", "get_refinement_regions", lambda p, h: [[p]] if _has(h, "Geometry/2D Flow Area Refinement Regions") else [], ["geopandas", "shapely", "pyproj"]),
    ("geometry", "HdfXsec", "get_cross_sections", lambda p, h: [[p]] if _has(h, "Geometry/Cross Sections") else [], ["geopandas", "shapely", "pyproj"]),
]


def detection_case(path, expected_kind):
    """Root attributes and top-level groups read with h5py; expected_kind is the
    human-reviewed classification from the corpus manifest."""
    import h5py
    with h5py.File(path, "r") as h:
        attrs = {}
        for k in ("File Type", "File Version", "LC Type", "Version", "Units System"):
            if k in h.attrs:
                v = h.attrs[k]
                attrs[k] = v.decode("latin-1") if isinstance(v, bytes) else str(v)
        top = sorted(h.keys())
    return {"id": "detection.root", "group": "detection", "call": "h5py root attributes",
            "generator_extra_deps": [], "result": {"kind": "detection", "root_attributes": attrs,
                                                   "top_level_groups": top, "expected_kind": expected_kind}}


FEATURE_CASES = {"HdfBndry.get_bc_lines", "HdfBndry.get_refinement_regions"}


def allowed(group, call, groups):
    if groups is None or group == "detection":
        return True
    return group in groups or ("geometry_features" in groups and call in FEATURE_CASES)


def generate(src, fid, path, outdir, parquet, expected_kind=None, groups=None, parquet_dir=None):
    if src and src != "-":
        sys.path.insert(0, src)
    import h5py
    import ras_commander
    import ras_commander.hdf as H
    warnings.filterwarnings("ignore")
    import logging
    logging.disable(logging.CRITICAL)
    with h5py.File(path, "r") as h:
        plans = [(g, c, m, args, deps) for g, c, m, b, deps in CASES if allowed(g, f"{c}.{m}", groups)
                 for args in b(path, h)]
    cases = [detection_case(path, expected_kind)]
    for i, (g, c, m, args, deps) in enumerate(plans):
        cid = f"{g}.{c}.{m}.{i}"
        rec = {"id": cid, "group": g, "call": f"{c}.{m}", "args": [os.path.basename(str(a)) if str(a) == path else a for a in args],
               "generator_extra_deps": deps}
        try:
            v = getattr(getattr(H, c), m)(*args)
            rec["result"] = digest_value(v)
            if parquet and hasattr(v, "to_parquet"):
                pdir = os.path.join(parquet_dir or outdir, fid)
                os.makedirs(pdir, exist_ok=True)
                try:
                    v.to_parquet(os.path.join(pdir, cid + ".parquet"))
                except Exception as e:
                    rec["parquet_error"] = str(e)[:200]
        except Exception as e:
            rec["error"] = (type(e).__name__ + ": " + str(e))[:300]
        cases.append(rec)
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    doc = {"schema": SCHEMA, "fixture_id": fid, "fixture_sha256": sha,
           "test_groups": sorted(groups) if groups is not None else None,
           "generator": {"ras_commander": getattr(ras_commander, "__version__", None),
                         "ras_commander_fast_hdf": _engine_version(),
                         "h5py": h5py.__version__, "numpy": np.__version__,
                         "pandas": __import__("pandas").__version__},
           "cases": cases}
    os.makedirs(os.path.join(outdir, fid), exist_ok=True)
    out = os.path.join(outdir, fid, "oracle.json")
    with open(out, "w") as f:
        json.dump(doc, f, indent=1, sort_keys=True, allow_nan=False, default=str)
    return out, cases


def _engine_version():
    try:
        import importlib.metadata as md
        return md.version("ras-commander-fast-hdf")
    except Exception:
        return None


def from_manifest(manifest, stage, outdir, parquet_dir=None):
    man = json.load(open(manifest, encoding="utf-8"))
    index = {}
    for e in man["entries"]:
        path = os.path.join(stage, *e["path"].split("/"))
        if not e["path"].lower().endswith((".hdf", ".h5")):
            continue
        out, cases = generate("-", e["id"], path, outdir, parquet_dir is not None,
                              e["detection"]["expected_kind"], set(e["test_groups"]), parquet_dir)
        index[e["id"]] = {"oracle": os.path.relpath(out, os.path.dirname(outdir)).replace(os.sep, "/"),
                          "sha256": hashlib.sha256(open(out, "rb").read()).hexdigest(),
                          "fixture_sha256": e["sha256"], "cases": len(cases),
                          "results": sum("result" in c for c in cases), "errors": sum("error" in c for c in cases)}
        print(f"{e['id']}: {index[e['id']]['results']}/{len(cases)}", flush=True)
    json.dump({"schema": SCHEMA, "manifest_version": man["version"], "fixtures": index},
              open(os.path.join(outdir, "INDEX.json"), "w"), indent=1, sort_keys=True)


if __name__ == "__main__" and "--manifest" in sys.argv:
    a = sys.argv
    pq = a[a.index("--parquet-out") + 1] if "--parquet-out" in a else None
    from_manifest(a[a.index("--manifest") + 1], a[a.index("--stage") + 1],
                  [x for i, x in enumerate(a[1:], 1) if not x.startswith("--") and a[i - 1] not in
                   ("--manifest", "--stage", "--parquet-out")][0], pq)
elif __name__ == "__main__":
    src, outdir = sys.argv[1], sys.argv[2]
    parquet = "--parquet" in sys.argv
    for spec in [a for a in sys.argv[3:] if "=" in a]:
        fid, rest = spec.split("=", 1)
        path, _, kind = rest.partition("::")
        out, cases = generate(src, fid, path, outdir, parquet, kind or None)
        ok = sum("result" in c for c in cases)
        print(f"{fid}: {ok}/{len(cases)} cases -> {out} ({os.path.getsize(out)} bytes)")
        for c in cases:
            if "error" in c:
                print("   ERR", c["call"], c["error"][:120])
