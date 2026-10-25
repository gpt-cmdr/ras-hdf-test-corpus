"""Census of property-table families in each corpus entry as published (read-only).

For a full file the family must be present and non-empty in the source. For an
excerpt it must also survive the recipe (not removed by --exclude-basename and,
with --include-only, inside an included prefix). Excerpts copy these datasets
verbatim with H5Ocopy, so their bytes are native but their container is h5py.

Used by build_proposed_manifest.py; runnable alone for inspection:
  python -I property_table_census.py
"""
import io
import re
import zipfile

import h5py

FAMILIES = {
    # family: (dataset regexes that must all be present, readers that consume it)
    "face_area_elevation": ([r"^Geometry/2D Flow Areas/[^/]+/Faces Area Elevation Info$",
                             r"^Geometry/2D Flow Areas/[^/]+/Faces Area Elevation Values$"]),
    "cell_volume_elevation": ([r"^Geometry/2D Flow Areas/[^/]+/Cells Volume Elevation Info$",
                               r"^Geometry/2D Flow Areas/[^/]+/Cells Volume Elevation Values$"]),
    "xs_property_tables": ([r"^Geometry/Cross Sections/Property Tables/XSEC Info$",
                            r"^Geometry/Cross Sections/Property Tables/XSEC Value$"]),
    "xs_property_cells": ([r"^Geometry/Cross Sections/Property Tables/Cell Info$",
                           r"^Geometry/Cross Sections/Property Tables/Cell Value$"]),
    "storage_area_volume_elevation": ([r"^Geometry/Storage Areas/.*Volume Elevation Info$",
                                       r"^Geometry/Storage Areas/.*Volume Elevation Values$"]),
    "structure_property_tables": ([r"^Geometry/Structures/.*Property Tables/.+"]),
    "pipe_property_tables": ([r"^Geometry/Pipe Networks/[^/]+/(Cell|Face) Property Table$"]),
}


def _open(path, zip66):
    if path.startswith("zip66!"):
        return h5py.File(io.BytesIO(zipfile.ZipFile(zip66).read(path[6:])), "r")
    return h5py.File(path, "r")


def _args(args, flag):
    if flag not in args:
        return []
    out = []
    for a in args[args.index(flag) + 1:]:
        if a.startswith("--"):
            break
        out.append(a)
    return out


def census(path, zip66, excerpt_args=None):
    """Return {family: {"present": bool, "rows": int, "versions_written": ...}}."""
    excl = set(_args(excerpt_args or [], "--exclude-basename"))
    incl = _args(excerpt_args or [], "--include-only")
    names = []
    with _open(path, zip66) as h:
        def visit(n, o):
            if isinstance(o, h5py.Dataset) and o.size:
                names.append((n, int(o.shape[0])))
        h.visititems(visit)

    def survives(n):
        if any(part in excl for part in n.split("/")):
            return False
        if incl and not any(n == p or n.startswith(p + "/") for p in incl):
            return False
        return True

    out = {}
    for fam, rxs in FAMILIES.items():
        source = all(any(re.search(rx, n) for n, _ in names) for rx in rxs)
        published = all(any(re.search(rx, n) and survives(n) for n, _ in names) for rx in rxs)
        rows = sum(r for n, r in names if re.search(rxs[-1], n) and survives(n))
        out[fam] = {"in_source": source, "published": published, "value_rows": rows}
    return out


if __name__ == "__main__":
    import json
    m = json.load(open("proposed_manifest.json"))
    for e in m["entries"]:
        c = census(e["local_source"], "H:/CLB-Repos/ras-commander/Example_Projects_6_6.zip", e.get("excerpt_args"))
        fams = [f for f, v in c.items() if v["published"]]
        dropped = [f for f, v in c.items() if v["in_source"] and not v["published"]]
        print(f"{e['id']:45} {e['profile']:8} {e['mode']:7} {e['published_bytes']/1e6:7.2f} {(e['hec_ras_version'] or '')[8:20]:12} pub={fams} dropped={dropped}")
