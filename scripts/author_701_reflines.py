"""Author HEC-RAS 7.0.1 fixtures with native reference lines and reference points.

For each case: copy the HEC example project (Example_Projects_6_6.zip, extracted
under D:/CLB-Dev/ras701-corpus/examples) to a fresh folder, apply the same plan
overrides as the corpus's 7.0.1 run of that plan (run_6x_examples.py), inject
reference lines and points into the plan's plain-text geometry with
ras_commander GeomReferenceFeatures (the notebook 207/314 approach), then run
the plan in HEC-RAS 7.0.1 with RasCmdr.compute_plan so 7.0.1 writes the
reference-line/point geometry and results natively.

HEC-RAS names reference-line results "<name>|<2D area>", so a line name may
repeat across 2D areas. GeomReferenceFeatures.add_reference_lines refuses a name
already in the file (any area), so the repeated-name line in the second area is
built with the same module's _build_reference_line_block and inserted directly
after the API-inserted blocks (recorded in the receipt as "direct_block").

Usage: python -B author_701_reflines.py RAS_COMMANDER_SRC OUT_ROOT [CASE ...]
Receipt: OUT_ROOT/author_701_reflines.json
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import traceback

EXAMPLES = "D:/CLB-Dev/ras701-corpus/examples/"
ZIP66 = "H:/CLB-Repos/ras-commander/Example_Projects_6_6.zip"
ZIP66_SHA = "ea239b506155a2dfeda2af80b3c2af948eef42c40218bcd65de472cfed386887"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def override(plan_file, reps):
    """Replace "Key=Value" plan lines (CRLF kept), as run_6x_examples.py does."""
    raw = open(plan_file, "rb").read().decode("latin-1")
    lines = raw.split("\r\n") if "\r\n" in raw else raw.split("\n")
    out = [f"{l.split('=', 1)[0]}={reps[l.split('=', 1)[0]]}" if "=" in l and l.split("=", 1)[0] in reps else l
           for l in lines]
    open(plan_file, "wb").write("\r\n".join(out).encode("latin-1"))
    return [l for l in out if l.startswith(("Mapping Interval=", "Output Interval=", "Computation Interval=",
                                            "Run Sediment="))]


# ----------------------------------------------------------------- cases
CASES = {
    # hec701r/Weise.p01.si-hydro (smoke): SI flume 16.5 m x 1 m, one 2D area "2DArea".
    "Weise_p01": {
        "project": "2D Sediment Transport/Weise_2D", "prj": "Weise.prj", "plan": "01", "geom": "g08",
        "overrides": {"Run Sediment": " 0", "Mapping Interval": "5MIN"},
        "corpus_parent": "hec701r/Weise.p01.si-hydro",
        "lines": {"2DArea": [
            {"name": "RL_x02", "coordinates": [(2.0, 0.05), (2.0, 0.95)]},
            {"name": "RL_x06", "coordinates": [(6.0, 0.05), (6.0, 0.25), (6.0, 0.45)]},
            {"name": "RL_x11_diag", "coordinates": [(11.2, 0.05), (12.0, 0.95)]},
            {"name": "RL_x14", "coordinates": [(14.0, 0.05), (14.0, 0.95)]},
            {"name": "RL_long_center", "coordinates": [(3.0, 0.3), (8.0, 0.3), (13.0, 0.3)]},
        ]},
        "points": [
            {"name": "RP_x01", "x": 1.0, "y": 0.5},
            {"name": "RP_x05", "x": 5.0, "y": 0.5},
            {"name": "RP_x09", "x": 9.0, "y": 0.25},
            {"name": "RP_x13", "x": 13.0, "y": 0.75},
            {"name": "RP_x16", "x": 16.0, "y": 0.5},
        ],
    },
    # BaldEagleDamBrk p18 "2D to 2D Run" (geometry g11): 2D areas BaldEagleCr and Upper 2D Area.
    "BaldEagleDamBrk_p18": {
        "project": "2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D", "prj": "BaldEagleDamBrk.prj",
        "plan": "18", "geom": "g11",
        "overrides": {"Mapping Interval": "1HOUR"},
        "corpus_parent": "hec701r/BaldEagleDamBrk.p19 / p15 (same project; p18 is the two-2D-area plan)",
        # Transverse lines generated from the channel breaklines of BaldEagleCr (notebook 314).
        "generate": {"storage_area": "BaldEagleCr", "breaklines": ["Upper", "Middle", "Lower"],
                     "spacing": 6000.0, "line_length": 2500.0,
                     "name_template": "BE_XS_{source_name}_{index:02d}"},
        "lines": {
            "BaldEagleCr": [
                {"name": "RL_Shared", "coordinates": [(2020500.0, 330500.0), (2022500.0, 335500.0)]},
            ],
            "Upper 2D Area": [
                {"name": "UP_XS_1", "coordinates": [(1978500.0, 297000.0), (1981000.0, 299000.0)]},
                {"name": "UP_XS_2", "coordinates": [(1990000.0, 306000.0), (1991000.0, 307500.0), (1992000.0, 309000.0)]},
            ],
        },
        # Same name, second area: direct block (see module docstring).
        "direct_lines": {"Upper 2D Area": [
            {"name": "RL_Shared", "coordinates": [(1998000.0, 312000.0), (2000000.0, 314500.0)]},
        ]},
        "points": [
            {"name": "RP_BE_Upper", "x": 2012000.0, "y": 327000.0},
            {"name": "RP_BE_Mid", "x": 2030250.0, "y": 335250.0},
            {"name": "RP_BE_Lower", "x": 2063500.0, "y": 352250.0},
            {"name": "RP_UP_1", "x": 1980000.0, "y": 300000.0},
            {"name": "RP_UP_2", "x": 1995000.0, "y": 310000.0},
        ],
    },
}


def clip_to_area(records, polygon):
    """Keep the longest part of each line inside ``polygon`` (notebook 314 trim)."""
    from shapely.geometry import LineString, MultiLineString
    out = []
    for r in records:
        part = LineString(r["coordinates"]).intersection(polygon.buffer(-1e-6 * max(1.0, polygon.length)))
        if isinstance(part, MultiLineString):
            part = max(part.geoms, key=lambda g: g.length)
        if part.is_empty or part.geom_type != "LineString" or part.length <= 0:
            continue
        out.append({"name": r["name"], "coordinates": [tuple(map(float, c)) for c in part.coords]})
    return out


def author(case_key, case, out_root, rc_src):
    import numpy as np
    from shapely.geometry import LineString, Point
    import ras_commander
    from ras_commander import GeomReferenceFeatures, HdfBndry, HdfMesh, RasCmdr, init_ras_project
    import importlib
    grf_mod = importlib.import_module("ras_commander.geom.GeomReferenceFeatures")  # the module, not the class

    src = os.path.join(EXAMPLES, case["project"])
    dest = os.path.join(out_root, "runs", case_key)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    stem = case["prj"][:-4]
    plan_file = os.path.join(dest, f"{stem}.p{case['plan']}")
    geom_file = os.path.join(dest, f"{stem}.{case['geom']}")
    geom_hdf = geom_file + ".hdf"
    rec = {
        "case": case_key, "project": case["project"], "plan": case["plan"], "geometry": case["geom"],
        "source": {"examples_zip": ZIP66, "examples_zip_sha256": ZIP66_SHA,
                   "extracted_copy": src.replace("\\", "/"),
                   "plan_sha256": sha(os.path.join(src, f"{stem}.p{case['plan']}")),
                   "geometry_sha256": sha(os.path.join(src, f"{stem}.{case['geom']}")),
                   "geometry_hdf_sha256": sha(os.path.join(src, f"{stem}.{case['geom']}.hdf")),
                   "corpus_parent": case["corpus_parent"]},
        "copy": dest.replace("\\", "/"),
        "ras_commander": {"file": ras_commander.__file__, "version": ras_commander.__version__,
                          "git": subprocess.run(["git", "-C", rc_src, "rev-parse", "HEAD"], capture_output=True,
                                                text=True).stdout.strip()},
        "plan_settings": override(plan_file, case["overrides"]),
    }
    areas = HdfMesh.get_mesh_areas(geom_hdf)
    polys = {r.mesh_name: r.geometry for r in areas.itertuples()}

    lines_by_area = {a: list(v) for a, v in case["lines"].items()}
    if "generate" in case:
        g = case["generate"]
        bl = HdfBndry.get_breaklines(geom_hdf)
        bl = bl[bl["Name"].isin(g["breaklines"])][["Name", "geometry"]]
        gen = GeomReferenceFeatures.generate_reference_lines_from_longitudinal_line(
            bl, spacing=g["spacing"], line_length=g["line_length"], include_end=False,
            name_template=g["name_template"], storage_area=g["storage_area"])
        gen = [r for r in gen if float(r.get("station", 1.0)) > 0.0]  # skip station 0 (at the breakline end)
        lines_by_area[g["storage_area"]] = clip_to_area(gen, polys[g["storage_area"]]) + lines_by_area.get(g["storage_area"], [])
        rec["generated"] = {**g, "generator": "GeomReferenceFeatures.generate_reference_lines_from_longitudinal_line",
                            "kept_after_clip": [r["name"] for r in lines_by_area[g["storage_area"]]]}

    injected = []
    for area, recs in lines_by_area.items():
        for r in recs:
            ln = LineString(r["coordinates"])
            if not polys[area].covers(ln):
                raise RuntimeError(f"{r['name']} is not inside {area}")
        n = GeomReferenceFeatures.add_reference_lines(geom_file, recs, area)
        injected += [{"name": r["name"], "storage_area": area, "coordinates": [list(c) for c in r["coordinates"]],
                      "method": "GeomReferenceFeatures.add_reference_lines"} for r in recs]
        assert n == len(recs)
    for area, recs in case.get("direct_lines", {}).items():
        raw = open(geom_file, "rb").read().decode("utf-8")
        nl = "\r\n" if "\r\n" in raw else "\n"
        rows = raw.split(nl)
        # after the last API-inserted reference-line block (its Text Position line)
        last = max(i for i, l in enumerate(rows) if l.startswith("Reference Line Text Position="))
        block = []
        for r in recs:
            if not polys[area].covers(LineString(r["coordinates"])):
                raise RuntimeError(f"{r['name']} is not inside {area}")
            block += grf_mod._build_reference_line_block(r["name"], area, np.asarray(r["coordinates"], dtype=float))
            injected.append({"name": r["name"], "storage_area": area, "coordinates": [list(c) for c in r["coordinates"]],
                             "method": "direct_block (_build_reference_line_block; add_reference_lines refuses a name "
                                       "repeated across areas)"})
        rows[last + 1:last + 1] = block
        open(geom_file, "wb").write(nl.join(rows).encode("utf-8"))
    for p in case["points"]:
        if not any(poly.covers(Point(p["x"], p["y"])) for poly in polys.values()):
            raise RuntimeError(f"{p['name']} is outside every 2D area")
    GeomReferenceFeatures.add_reference_points(geom_file, case["points"])
    rec["injected_lines"] = injected
    rec["injected_points"] = case["points"]
    rec["text_round_trip"] = {
        "lines": [(l["name"], l["storage_area"]) for l in GeomReferenceFeatures.get_reference_lines(geom_file)],
        "points": [p["name"] for p in GeomReferenceFeatures.get_reference_points(geom_file)],
    }
    rec["geometry_text_sha256_after_injection"] = sha(geom_file)

    rec["method"] = ("init_ras_project(copy, '7.0.1', ras_object='new'); RasCmdr.compute_plan(plan, ras_object=ras, "
                     "num_cores=2, clear_geompre=True, force_rerun=True, verify=True)")
    t0 = time.time()
    try:
        ras = init_ras_project(dest, "7.0.1", ras_object="new")
        r = RasCmdr.compute_plan(case["plan"], ras_object=ras, num_cores=2, clear_geompre=True,
                                 force_rerun=True, verify=True)
        rec["result"] = str(r)[:2000]
        rec["success"] = bool(r.success) if hasattr(r, "success") else bool(r)
    except Exception:
        rec["error"] = traceback.format_exc()[-3000:]
        rec["success"] = False
    rec["seconds"] = round(time.time() - t0, 1)
    rec["hdf_files"] = {f: {"bytes": os.path.getsize(os.path.join(dest, f)), "sha256": sha(os.path.join(dest, f))}
                        for f in sorted(os.listdir(dest)) if f.lower().endswith(".hdf")
                        and (f".p{case['plan']}." in f or f".{case['geom']}." in f)}
    return rec


def main(rc_src, out_root, keys):
    sys.path.insert(0, rc_src)
    os.makedirs(out_root, exist_ok=True)
    out_path = os.path.join(out_root, "author_701_reflines.json")
    results = json.load(open(out_path)) if os.path.exists(out_path) else {}
    for k in keys or list(CASES):
        rec = author(k, CASES[k], out_root, rc_src)
        results[k] = rec
        json.dump(results, open(out_path, "w"), indent=1)
        print(k, rec["success"], rec["seconds"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
