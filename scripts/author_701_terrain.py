"""Author a small HEC-RAS 7.0.1 terrain (HDF + GeoTIFF + VRT) from public HEC data.

Input: the HEC BaldEagleCrkMulti2D example terrain tile Terrain/Terrain50.dtm_20ft.tif
(Example_Projects_6_6.zip) and its Terrain/Projection.prj. The tile is clipped by a
rasterio windowed copy (same CRS, pixels and values) to the 6,000 ft extent used by
author_701_layers.py. HEC-RAS 7.0.1 RasProcess.exe CreateTerrain, called through
ras_commander RasTerrain.create_terrain_hdf, then writes the terrain HDF and its
own TIFF, so the published terrain is 7.0.1-written, TIFFs included.

Usage: python -B author_701_terrain.py RAS_COMMANDER_SRC PROJECT_DIR OUT_DIR
"""
import hashlib
import json
import os
import sys


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main(src, project, out):
    sys.path.insert(0, src)
    import h5py
    import rasterio
    from rasterio.windows import from_bounds
    from ras_commander import RasTerrain

    os.makedirs(out, exist_ok=True)
    with h5py.File(os.path.join(project, "BaldEagleDamBrk.g09.hdf"), "r") as g:
        pts = g["Geometry/2D Flow Areas/BaldEagleCr/FacePoints Coordinate"][()]
    xmin, ymin = (float(v) for v in pts.min(axis=0))
    extent = (xmin, ymin, xmin + 6000.0, ymin + 6000.0)

    src_tif = os.path.join(project, "Terrain", "Terrain50.dtm_20ft.tif")
    clip = os.path.join(out, "_src", "dtm_20ft_clip.tif")
    os.makedirs(os.path.dirname(clip), exist_ok=True)
    with rasterio.open(src_tif) as r:
        w = from_bounds(*extent, transform=r.transform).round_offsets().round_lengths()
        prof = r.profile.copy()
        prof.update(width=int(w.width), height=int(w.height), transform=r.window_transform(w), tiled=False)
        prof.pop("blockxsize", None)
        prof.pop("blockysize", None)
        with rasterio.open(clip, "w", **prof) as d:
            d.write(r.read(window=w))

    hdf = os.path.join(out, "Terrain701.hdf")
    RasTerrain.create_terrain_hdf([clip], hdf, os.path.join(project, "Terrain", "Projection.prj"),
                                  units="Feet", stitch=True, hecras_version="7.0.1")
    rec = {"hecras_version": "7.0.1", "method": "RasTerrain.create_terrain_hdf (RasProcess.exe CreateTerrain)",
           "source": "Example_Projects_6_6.zip: 2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D/Terrain/Terrain50.dtm_20ft.tif",
           "extent": extent, "files": {}}
    for f in sorted(os.listdir(out)):
        p = os.path.join(out, f)
        if os.path.isfile(p):
            rec["files"][f] = {"bytes": os.path.getsize(p), "sha256": sha(p)}
    with h5py.File(hdf, "r") as h:
        rec["root_attrs"] = {k: (v.decode() if isinstance(v, bytes) else str(v)) for k, v in h.attrs.items()}
        rec["top"] = sorted(h.keys())
    json.dump(rec, open(os.path.join(out, "author_701_terrain.json"), "w"), indent=1, default=str)
    print(json.dumps(rec, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:4])
