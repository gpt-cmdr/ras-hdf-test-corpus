"""Prototype: build a small HEC-RAS HDF excerpt that keeps stored layouts.

Everything is copied with H5Ocopy (h5py Group.copy), which preserves dtype,
chunk shape, filter pipeline, fill value and the compressed chunk bytes, and
attribute types. The only change is that time-series datasets under a Results
group that owns a ``Time`` dataset are truncated to the first ``--rows`` rows
(plus, with ``--keep-last``, the final row); the same applies to Event
Conditions meteorology groups that own a ``Timestamp`` dataset. The default of
8 rows plus the last covers every row pattern the oracles read: head 3, a
5-row window, a 7-row stride-2 slab, the middle row and the last 2 rows.
``--exclude-basename`` drops a named dataset family everywhere (recorded). Truncated datasets are recreated
with the source's dtype, chunk shape (rows clipped), filters, fill value and
maxshape, and their attributes are copied verbatim. Stale "Maximum/Minimum Value
of Data Set" attributes are deliberately kept and recorded so that the excerpt
still matches the source's attribute set.

Not preserved: container-level encoding (superblock version, object-header
versions, B-tree/heap layout, byte offsets, shared-message tables). Excerpts
therefore test RAS semantics, not the generic HDF reader's handling of
HEC-RAS's own writer. Use full native files for that.

Usage:
  python -I excerpt_hdf.py SRC DST [--rows 24] [--keep-last]
         [--exclude PREFIX ...] [--include-only PREFIX ...]
Writes DST and DST.provenance.json. Never modifies SRC.
"""
import argparse
import hashlib
import json
import os

import h5py
import numpy as np


def sha256(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            d.update(b)
    return d.hexdigest()


def copy_attrs(src, dst):
    for k in src.attrs:
        aid = src.attrs.get_id(k)
        dst.attrs.create(k, src.attrs[k], dtype=aid.dtype)


def time_axes(h):
    """Map Results group path -> number of time rows, for groups owning Time."""
    axes = {}

    def visit(name, obj):
        if not isinstance(obj, h5py.Group):
            return
        # Results output blocks own "Time"; meteorology in Event Conditions
        # owns "Timestamp" (e.g. gridded precipitation Values).
        for root, key in (("Results/", "Time"), ("Event Conditions/", "Timestamp")):
            if (name.startswith(root) and key in obj and isinstance(obj[key], h5py.Dataset)
                    and obj[key].ndim == 1):
                axes[name] = obj[key].shape[0]
    h.visititems(visit)
    return axes


def governing_axis(path, axes):
    best = None
    for g, n in axes.items():
        if path.startswith(g + "/") and (best is None or len(g) > len(best[0])):
            best = (g, n)
    return best


def rows_to_keep(n, rows, keep_last):
    idx = list(range(min(rows, n)))
    if keep_last and n - 1 not in idx:
        idx.append(n - 1)
    return np.asarray(idx)


def truncated_copy(sds, dparent, name, idx):
    shape = (len(idx),) + sds.shape[1:]
    chunks = None
    if sds.chunks:
        chunks = (min(sds.chunks[0], shape[0]),) + tuple(sds.chunks[1:])
    maxshape = sds.maxshape
    kw = dict(shape=shape, dtype=sds.dtype, chunks=chunks, maxshape=maxshape if chunks else None,
              compression=sds.compression, compression_opts=sds.compression_opts,
              shuffle=sds.shuffle, fletcher32=sds.fletcher32, scaleoffset=sds.scaleoffset)
    if sds.fillvalue is not None:
        kw["fillvalue"] = sds.fillvalue
    if not chunks:
        for k in ("compression", "compression_opts", "shuffle", "fletcher32", "scaleoffset", "maxshape"):
            kw.pop(k)
    dds = dparent.create_dataset(name, **kw)
    if len(idx) and int(idx[-1]) == len(idx) - 1:
        dds[...] = sds[: len(idx)]
    else:
        dds[...] = sds[idx.tolist()] if len(idx) else dds[...]
    copy_attrs(sds, dds)
    return dds


def build(src, dst, rows, keep_last, exclude, include_only, exclude_basename=()):
    report = {"truncated": [], "excluded": [], "copied_verbatim": []}
    with h5py.File(src, "r") as s, h5py.File(dst, "w", libver="earliest") as d:
        copy_attrs(s, d)
        axes = time_axes(s)
        report["time_axes"] = axes

        def wanted(path):
            if any(path == e or path.startswith(e + "/") for e in exclude):
                return False
            if path.rsplit("/", 1)[-1] in exclude_basename:
                return False
            if include_only:
                return any(path == p or path.startswith(p + "/") or p.startswith(path + "/")
                           for p in include_only)
            return True

        def needs_walk(path):
            # A group must be walked (not block-copied) if anything below it is
            # truncated, excluded or filtered by include_only.
            if any(e.startswith(path + "/") for e in exclude):
                return True
            if exclude_basename and path.startswith("Geometry"):
                return True
            if include_only and not any(path == p or path.startswith(p + "/") for p in include_only):
                return True
            return any(g == path or g.startswith(path + "/") or path.startswith(g + "/")
                       for g in axes)

        def walk(sg, dg):
            for name, obj in sg.items():
                path = obj.name.lstrip("/")
                if not wanted(path):
                    report["excluded"].append(path)
                    continue
                if isinstance(obj, h5py.Group):
                    if needs_walk(path):
                        ng = dg.create_group(name)
                        copy_attrs(obj, ng)
                        walk(obj, ng)
                    else:
                        sg.copy(obj, dg, name=name)
                        report["copied_verbatim"].append(path + "/")
                    continue
                gov = governing_axis(path, axes)
                if gov and obj.ndim >= 1 and obj.shape[0] == gov[1] and gov[1] > rows:
                    idx = rows_to_keep(gov[1], rows, keep_last)
                    truncated_copy(obj, dg, name, idx)
                    report["truncated"].append({"path": path, "from": list(obj.shape),
                                                "rows": idx.tolist()})
                else:
                    sg.copy(obj, dg, name=name)
                    report["copied_verbatim"].append(path)

        walk(s, d)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--rows", type=int, default=8)
    ap.add_argument("--keep-last", action="store_true")
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--include-only", nargs="*", default=[])
    ap.add_argument("--exclude-basename", nargs="*", default=[],
                    help="drop datasets/groups with this name anywhere (e.g. a whole "
                         "property-table family: Values and the Info tables indexing them)")
    a = ap.parse_args()
    if os.path.abspath(a.src) == os.path.abspath(a.dst):
        raise SystemExit("refusing to overwrite source")
    rep = build(a.src, a.dst, a.rows, a.keep_last, a.exclude, a.include_only, a.exclude_basename)
    prov = {
        "generator": "excerpt_hdf.py (prototype)",
        "h5py": h5py.__version__, "hdf5": h5py.version.hdf5_version, "numpy": np.__version__,
        "source_name": os.path.basename(a.src), "source_bytes": os.path.getsize(a.src),
        "source_sha256": sha256(a.src),
        "params": {"rows": a.rows, "keep_last": a.keep_last, "exclude": a.exclude,
                   "include_only": a.include_only, "exclude_basename": a.exclude_basename},
        "excerpt_bytes": os.path.getsize(a.dst), "excerpt_sha256": sha256(a.dst),
        "stale_attributes_note": "Maximum/Minimum Value of Data Set attributes on truncated "
                                 "datasets describe the full source series.",
        **rep,
    }
    with open(a.dst + ".provenance.json", "w") as f:
        json.dump(prov, f, indent=1, default=str)
    print(f"{prov['source_bytes']/1e6:.1f} MB -> {prov['excerpt_bytes']/1e6:.2f} MB; "
          f"truncated {len(rep['truncated'])} datasets")


if __name__ == "__main__":
    main()
