"""Scan a list of local eBFE HDFs (size<TAB>path per line) for refinement regions and layer types.

Read-only. Writes TSV: bytes, file_version, lc_type, n_refinement_regions, n_2d_areas, path.
Usage: python -I scan_ebfe_features.py LIST_TSV OUT_TSV
"""
import sys

import h5py


def main(list_tsv, out_tsv):
    rows = []
    for line in open(list_tsv, encoding="utf-8", errors="replace"):
        if "\t" not in line:
            continue
        size, path = line.rstrip("\n").split("\t", 1)
        if len(path) > 3 and path[0] == "/" and path[2] == "/":  # Git Bash /h/... -> H:/...
            path = path[1].upper() + ":/" + path[3:]
        try:
            with h5py.File(path, "r") as h:
                g = lambda k: (h.attrs[k].decode("latin-1") if isinstance(h.attrs[k], bytes) else str(h.attrs[k])) if k in h.attrs else ""
                rr = h.get("Geometry/2D Flow Area Refinement Regions/Attributes")
                fa = h.get("Geometry/2D Flow Areas/Attributes")
                rows.append((int(size), g("File Version"), g("LC Type"), rr.shape[0] if rr is not None else 0,
                             fa.shape[0] if fa is not None else 0, path))
        except Exception as e:
            rows.append((int(size), "ERR " + type(e).__name__, "", 0, 0, path))
    with open(out_tsv, "w", encoding="utf-8") as f:
        for r in rows:
            f.write("\t".join(map(str, r)) + "\n")
    rr = [r for r in rows if r[3]]
    lc = [r for r in rows if r[2]]
    print(f"{len(rows)} files; {len(rr)} with refinement regions; {len(lc)} layers")
    for r in sorted(rr)[:25]:
        print("RR", round(r[0] / 1e6, 2), r[1][:24], r[3], r[4], r[5])
    for r in sorted(lc, key=lambda r: (r[2], r[0]))[:40]:
        print("LC", round(r[0] / 1e6, 3), r[2], r[5])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
