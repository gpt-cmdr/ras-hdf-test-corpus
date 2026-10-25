"""Synthetic corpus fixtures (CC0). Deterministic; prints SHA-256 of each output.

albers_crs     Byte copy of a native HEC-RAS 7.0.1 geometry HDF with only the root
               "Projection" attribute replaced by NAD83 / CONUS Albers (EPSG:5070,
               ESRI WKT). Coordinates are untouched, so this tests CRS metadata
               handling only (no public 7.0.1 model in Albers was found).
legacy_struct  Minimal file with the legacy generic
               ".../Base Output/Unsteady Time Series/Structures" layout that
               HdfStruc1D still reads as a fallback. No HEC-RAS version observed
               (5.0.7, 6.3.1, 6.6, 7.0, 7.0.1) writes it; this exercises the
               fallback and its refusal paths only.

Usage: python -I make_synthetic_fixtures.py OUT_DIR DAVIS_701_G02_HDF
"""
import hashlib
import os
import shutil
import sys

import h5py
import numpy as np

ALBERS_WKT = (
    'PROJCS["NAD_1983_Contiguous_USA_Albers",GEOGCS["GCS_North_American_1983",'
    'DATUM["D_North_American_1983",SPHEROID["GRS_1980",6378137.0,298.257222101]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Albers"],PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],'
    'PARAMETER["Central_Meridian",-96.0],PARAMETER["Standard_Parallel_1",29.5],'
    'PARAMETER["Standard_Parallel_2",45.5],PARAMETER["Latitude_Of_Origin",23.0],UNIT["Meter",1.0]]')
TS = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def albers(out_dir, davis_g02):
    dst = os.path.join(out_dir, "synthetic_albers.DavisStormSystem.g02.hdf")
    shutil.copyfile(davis_g02, dst)
    with h5py.File(dst, "r+") as h:
        old = h.attrs["Projection"]
        h.attrs.modify("Projection", np.bytes_(ALBERS_WKT))  # keep fixed-length bytes like HEC-RAS
        assert isinstance(old, (bytes, np.bytes_))
    return dst


def legacy_struct(out_dir):
    dst = os.path.join(out_dir, "synthetic_legacy_ts_structures.h5")
    n_t, n_s = 6, 2
    with h5py.File(dst, "w", libver="earliest", track_order=False) as h:
        h.attrs["File Type"] = np.bytes_("HEC-RAS Results")
        h.attrs["File Version"] = np.bytes_("synthetic (legacy Structures layout)")
        h.attrs["Units System"] = np.bytes_("US Customary")
        ts = h.create_group(TS)
        ts.create_dataset("Time", data=np.arange(n_t, dtype="f8") / 24.0)
        stamps = np.array([f"01JAN2000 {i:02d}:00:00".encode() for i in range(n_t)], dtype="S19")
        ts.create_dataset("Time Date Stamp", data=stamps)
        g = ts.create_group("Structures")
        dt = np.dtype([("River", "S16"), ("Reach", "S16"), ("RS", "S8"), ("Type", "S8")])
        g.create_dataset("Structure Attributes", data=np.array(
            [(b"Synthetic River", b"Upper", b"100.5", b"Inline"), (b"Synthetic River", b"Upper", b"200.5", b"Bridge")], dtype=dt))
        t = np.arange(n_t, dtype="f4")[:, None]
        g.create_dataset("Headwater", data=(500.0 + t + np.array([0.0, 2.0], dtype="f4")).astype("f4"))
        g.create_dataset("Tailwater", data=(498.0 + t + np.array([0.0, 2.0], dtype="f4")).astype("f4"))
        g.create_dataset("Flow", data=(1000.0 * (1 + t) * np.array([1.0, 0.5], dtype="f4")).astype("f4"))
        for name, unit in (("Headwater", "ft"), ("Tailwater", "ft"), ("Flow", "cfs")):
            g[name].attrs["Units"] = np.bytes_(unit)
    return dst


def infiltration_parameters(out_dir):
    """Root "Infiltration Parameters" table as read by HdfInfiltration.get_infiltration_parameters
    (mukey, initial loss, constant loss rate, impervious %). Not found in any HEC-RAS/RAS Mapper
    output examined (HEC examples, ~370 LWI/eBFE/RBFS layer files), so this is code-shaped only."""
    dst = os.path.join(out_dir, "synthetic_infiltration_parameters.hdf")
    dt = np.dtype([("MUKEY", "S16"), ("Initial Loss (in)", "f4"), ("Constant Loss Rate (in/hr)", "f4"),
                   ("Impervious Area (%)", "f4")])
    rows = np.array([(b"100001", 0.5, 0.10, 5.0), (b"100002", 1.0, 0.25, 0.0), (b"100003", 0.2, 0.05, 40.0)], dtype=dt)
    with h5py.File(dst, "w", libver="earliest") as h:
        h.attrs["LC Type"] = np.bytes_("InfiltrationDeficitConstantLoss")
        h.attrs["Version"] = np.bytes_("synthetic")
        h.create_dataset("Infiltration Parameters", data=rows)
    return dst


if __name__ == "__main__":
    out, davis = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for p in (albers(out, davis), legacy_struct(out), infiltration_parameters(out)):
        print(os.path.getsize(p), sha(p), p)
