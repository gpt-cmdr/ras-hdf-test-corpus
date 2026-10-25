"""Generate a large synthetic 2D-results HDF for performance runs (never shipped).

Takes the group/attribute skeleton of a small native HEC-RAS 7.0.1 plan HDF and
writes one 2D flow area with N cells / ~2N faces and T time rows, using the
native dataset names, dtypes, chunk shape (1, columns) and gzip level, filled
with deterministic pseudo-random values. Intended for CI jobs that need a
multi-GB file: generate in-job, do not download.

Usage: python -I make_perf_fixture.py TEMPLATE_701_PLAN_HDF OUT_HDF --cells 2000000 --times 200 [--seed 0]
Approximate size ~ times * cells * 4 B * (2 cell vars + 2 face vars * 2) / gzip ratio.
"""
import argparse

import h5py
import numpy as np

TS = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("out")
    ap.add_argument("--cells", type=int, default=2_000_000)
    ap.add_argument("--times", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    nc, nf, nt = a.cells, 2 * a.cells, a.times
    with h5py.File(a.template, "r") as t, h5py.File(a.out, "w", libver="earliest") as o:
        for k, v in t.attrs.items():
            o.attrs[k] = v
        o.attrs["File Version"] = np.bytes_(t.attrs["File Version"].decode() + " (synthetic perf)")
        area = "PerfArea"
        g = o.create_group(f"Geometry/2D Flow Areas/{area}")
        g.create_dataset("Cells Center Coordinate", data=rng.random((nc, 2)) * 1e5, chunks=(min(nc, 65536), 2), compression="gzip", compression_opts=1)
        ts = o.create_group(f"{TS}/2D Flow Areas/{area}")
        o[TS].create_dataset("Time", data=np.arange(nt, dtype="f8") / 24.0)
        for name, cols, unit in (("Water Surface", nc, "ft"), ("Depth", nc, "ft"),
                                 ("Face Velocity", nf, "ft/s"), ("Face Flow", nf, "cfs")):
            d = ts.create_dataset(name, shape=(nt, cols), dtype="f4", chunks=(1, cols),
                                  compression="gzip", compression_opts=1)
            base = rng.random(cols, dtype="f4") * 10
            for i in range(nt):
                d[i] = base + np.float32(i * 0.01)
            d.attrs["Units"] = np.bytes_(unit)
            d.attrs["Rows"] = np.bytes_("Times")
            d.attrs["Columns"] = np.bytes_("Faces" if name.startswith("Face") else "Cells")


if __name__ == "__main__":
    main()
