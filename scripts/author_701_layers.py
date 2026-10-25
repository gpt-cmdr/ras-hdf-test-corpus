"""Author RAS Mapper layer files with HEC-RAS 7.0.1's own RasMapperLib (via ras-commander).

Inputs are the public HEC BaldEagleCrkMulti2D example (Example_Projects_6_6.zip):
its source rasters Land Classification/LandCover.tif and Soils Data/Hydrologic Soil
Groups.tif, and the class tables of the shipped layers. A fresh project copy is
used; outputs are 7.0.1-written land cover, soils, and SCS / Green-Ampt /
deficit-constant infiltration layers, restricted to a small extent so the
companion TIFFs stay small.

Usage: python -B author_701_layers.py RAS_COMMANDER_SRC EXAMPLE_PROJECT_DIR WORK_DIR [--resume]
(--resume keeps WORK_DIR and an already-authored LandCover701.hdf)

create_soils has no extent option, and on the full HSG raster it stalled with
almost no CPU (twice, 2026-10-24). The HSG source is therefore first clipped
to the same extent with rasterio (a windowed copy: same CRS, pixels and
values), and RasMapperLib authors the soils layer from the clip.
"""
import hashlib
import json
import os
import shutil
import sys
import traceback


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def clip_raster(src_tif, dst_tif, extent):
    import rasterio
    from rasterio.windows import from_bounds
    os.makedirs(os.path.dirname(dst_tif), exist_ok=True)
    with rasterio.open(src_tif) as r:
        w = from_bounds(*extent, transform=r.transform).round_offsets().round_lengths()
        prof = r.profile.copy()
        prof.update(width=int(w.width), height=int(w.height), transform=r.window_transform(w), compress="deflate",
                    tiled=False)
        prof.pop("blockxsize", None); prof.pop("blockysize", None)
        with rasterio.open(dst_tif, "w", **prof) as d:
            d.write(r.read(window=w))
    return dst_tif


def main(src, example, work, resume=False):
    sys.path.insert(0, src)
    import h5py
    import pandas as pd
    from ras_commander import RasMap
    from ras_commander import _landcover_native as lcn

    if not resume:
        if os.path.exists(work):
            shutil.rmtree(work)
        shutil.copytree(example, work)
    prj = os.path.join(work, "BaldEagleDamBrk.prj")
    rasmap = os.path.join(work, "BaldEagleDamBrk.rasmap")
    out = os.path.join(work, "Layers701")
    os.makedirs(out, exist_ok=True)

    # Small extent around the dam/upper 2D area (project CRS: PA North ft).
    with h5py.File(os.path.join(work, "BaldEagleDamBrk.g09.hdf"), "r") as g:
        pts = g["Geometry/2D Flow Areas/BaldEagleCr/FacePoints Coordinate"][()]
    xmin, ymin = pts.min(axis=0)
    extent = (float(xmin), float(ymin), float(xmin) + 6000.0, float(ymin) + 6000.0)

    rec = {"hecras_version": "7.0.1", "extent": extent, "outputs": {}, "errors": {}}
    with h5py.File(os.path.join(work, "Land Classification", "LandCover.hdf"), "r") as h:
        rm = h["Raster Map"][()]
        var = {r["Name"].decode(): (float(r["ManningsN"]), float(r["Percent Impervious"])) for r in h["Variables"][()]}
    rows = [{"source_value": int(i), "class_id": int(i), "class_name": n.decode(),
             "mannings_n": var.get(n.decode(), (0.06, 0.0))[0],
             "percent_impervious": var.get(n.decode(), (0.06, 0.0))[1]} for i, n in rm if int(i) != 0]
    steps = [
        ("landcover", lambda: RasMap.add_landcover_layer(
            prj, os.path.join(work, "Land Classification", "LandCover.tif"), pd.DataFrame(rows), cell_size=30.0,
            output_hdf_path=os.path.join(out, "LandCover701.hdf"), restrict_to_extent=extent, hecras_version="7.0.1")),
    ]
    with h5py.File(os.path.join(work, "Soils Data", "Hydrologic Soil Groups.hdf"), "r") as h:
        soil_rows = [(int(i), n.decode()) for i, n in h["Raster Map"][()]]  # includes 0 = NoData
    hsg_clip = clip_raster(os.path.join(work, "Soils Data", "Hydrologic Soil Groups.tif"),
                           os.path.join(work, "Layers701_src", "HSG_clip.tif"), extent)
    steps.append(("soils", lambda: lcn.create_soils(
        rasmap_path=rasmap, source_raster_path=hsg_clip,
        raster_map_rows=soil_rows, cell_size=30.0, output_hdf_path=os.path.join(out, "Soils701.hdf"),
        hecras_version="7.0.1")))
    for method in ("scs_curve_number", "green_ampt", "deficit_constant"):
        steps.append((f"infiltration_{method}", lambda m=method: RasMap.add_infiltration_layer(
            prj, infiltration_method=m, landcover_hdf_path=os.path.join(out, "LandCover701.hdf"),
            soil_layer_path=os.path.join(out, "Soils701.hdf"),
            output_hdf_path=os.path.join(out, f"Infiltration701_{m}.hdf"), hecras_version="7.0.1")))
    if resume and os.path.exists(os.path.join(out, "LandCover701.hdf")):
        steps = [s_ for s_ in steps if s_[0] != "landcover"]
        rec["outputs"]["landcover"] = os.path.join(out, "LandCover701.hdf")
    for name, fn in steps:
        try:
            p = str(fn())
            rec["outputs"][name] = p
        except Exception:
            rec["errors"][name] = traceback.format_exc()[-1500:]
        print(name, "ok" if name in rec["outputs"] else "FAILED", flush=True)
    files = {}
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        files[f] = {"bytes": os.path.getsize(p), "sha256": sha(p)}
        if f.endswith(".hdf"):
            with h5py.File(p, "r") as h:
                files[f]["attrs"] = {k: (v.decode() if isinstance(v, bytes) else str(v)) for k, v in h.attrs.items()
                                     if k in ("File Type", "LC Type", "Version")}
                files[f]["top"] = sorted(h.keys())
    rec["files"] = files
    json.dump(rec, open(os.path.join(work, "author_701_layers.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main(*sys.argv[1:4], resume="--resume" in sys.argv)
