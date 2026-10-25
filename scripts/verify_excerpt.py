"""Check an excerpt against its source (read-only).

For every dataset in the excerpt: same dtype, filters, chunk shape (rows may be
clipped), attribute names, values and attribute dtypes; values equal the source
(for truncated datasets, equal to the recorded source rows). Every source
object must be present unless the provenance says it was excluded.

Usage: python -I verify_excerpt.py SRC EXCERPT   (reads EXCERPT.provenance.json)
"""
import json
import sys

import h5py
import numpy as np


def attrs_equal(a, b):
    if set(a.attrs) != set(b.attrs):
        return False
    for k in a.attrs:
        if a.attrs.get_id(k).dtype != b.attrs.get_id(k).dtype:
            return False
        # byte comparison: NaN-safe and exact for compound/string attributes
        if np.asarray(a.attrs[k]).tobytes() != np.asarray(b.attrs[k]).tobytes():
            return False
    return True


def main(src, exc):
    prov = json.load(open(exc + ".provenance.json"))
    trunc = {t["path"]: t["rows"] for t in prov["truncated"]}
    excluded = prov["excluded"]
    bad = []
    with h5py.File(src, "r") as s, h5py.File(exc, "r") as e:
        if not attrs_equal(s, e):
            bad.append("/ attrs")

        def visit(name, so):
            if any(name == x or name.startswith(x + "/") for x in excluded):
                return
            if name not in e:
                bad.append("missing " + name)
                return
            eo = e[name]
            if not attrs_equal(so, eo):
                bad.append("attrs " + name)
            if isinstance(so, h5py.Dataset):
                same = (so.dtype == eo.dtype and so.compression == eo.compression
                        and so.compression_opts == eo.compression_opts
                        and so.shuffle == eo.shuffle and so.fletcher32 == eo.fletcher32
                        and (so.chunks is None) == (eo.chunks is None)
                        and (so.chunks is None or so.chunks[1:] == eo.chunks[1:]))
                if not same:
                    bad.append("layout " + name)
                sv = so[()] if name not in trunc else so[trunc[name]]
                if np.asarray(sv).tobytes() != np.asarray(eo[()]).tobytes():
                    bad.append("values " + name)
        s.visititems(visit)
    print("OK" if not bad else f"{len(bad)} problems: {bad[:20]}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
