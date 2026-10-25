"""Run HEC 5.0.7 example plans in HEC-RAS 5.0.7 to produce native 5.0.7 fixtures.

Uses ras-commander's legacy COM path (RasControl.run_plan, RAS507.HECRASController)
on a fresh copy of each example project, so the extracted examples stay pristine.
Writes run_507_results.json next to the runs.

Usage: python -B run_507_examples.py RAS_COMMANDER_SRC EXAMPLES_ROOT RUNS_ROOT [MAPPING_INTERVAL]
(with MAPPING_INTERVAL, reruns the 2D plans with only "Mapping Interval=" changed)
"""
import hashlib
import json
import os
import shutil
import sys
import time
import traceback

PLANS = [
    ("Muncie", "Muncie.prj", "01"),              # 1D unsteady with 9 storage areas
    ("Muncie", "Muncie.prj", "03"),              # 1D/2D, 50 ft grid
    ("Muncie", "Muncie.prj", "04"),              # 2D with user n-value regions
    ("BaldEagleCrkMulti2D", "BaldEagleDamBrk.prj", "18"),  # 2D to 2D connection
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


MAPPING_OVERRIDE = None  # e.g. "1HOUR": rewrite "Mapping Interval=" in the copied plan file


def apply_mapping_override(dest, prj, plan, value):
    stem = prj[:-4]
    pf = os.path.join(dest, f"{stem}.p{plan}")
    text = open(pf, encoding="latin-1").read()
    lines = [f"Mapping Interval={value}" if l.startswith("Mapping Interval=") else l for l in text.splitlines()]
    with open(pf, "w", encoding="latin-1", newline=chr(13)+chr(10)) as f:  # HEC-RAS text files use CRLF
        f.write(chr(10).join(lines) + chr(10))
    return [l for l in lines if l.startswith(("Mapping Interval=", "Output Interval=", "Computation Interval="))]


def main(src, examples, runs):
    sys.path.insert(0, src)
    import ras_commander
    from ras_commander import RasControl, init_ras_project
    out_path = os.path.join(runs, "run_507_results.json")
    results = json.load(open(out_path)) if os.path.exists(out_path) else {}
    for proj, prj, plan in PLANS:
        key = f"{proj}.p{plan}" + (f".map{MAPPING_OVERRIDE}" if MAPPING_OVERRIDE else "")
        if results.get(key, {}).get("success"):
            continue
        dest = os.path.join(runs, f"{proj}_p{plan}" + (f"_map{MAPPING_OVERRIDE}" if MAPPING_OVERRIDE else ""))
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(os.path.join(examples, proj), dest)
        rec = {"project": proj, "plan": plan, "copy": dest, "ras_version": "5.0.7",
               "ras_commander_src": src, "ras_commander_file": ras_commander.__file__,
               "method": "RasControl.run_plan(force_recompute=True, max_runtime=3600, observe_dialogs=True)"}
        if MAPPING_OVERRIDE:
            rec["plan_changes"] = apply_mapping_override(dest, prj, plan, MAPPING_OVERRIDE)
        t0 = time.time()
        try:
            ras = init_ras_project(dest, "5.0.7", ras_object="new")
            r = RasControl.run_plan(plan, ras_object=ras, force_recompute=True, max_runtime=3600,
                                    refresh_results=False, observe_dialogs=True)
            rec["result"] = {k: (str(v) if not isinstance(v, (int, float, bool, type(None))) else v)
                             for k, v in getattr(r, "__dict__", {}).items()} or str(r)
            rec["success"] = bool(getattr(r, "success", False))
        except Exception as e:
            rec["error"] = traceback.format_exc()[-2000:]
            rec["success"] = False
        rec["seconds"] = round(time.time() - t0, 1)
        hdfs = {}
        for f in sorted(os.listdir(dest)):
            if f.lower().endswith(".hdf"):
                p = os.path.join(dest, f)
                hdfs[f] = {"bytes": os.path.getsize(p), "sha256": sha(p)}
        rec["hdf_files"] = hdfs
        results[key] = rec
        json.dump(results, open(out_path, "w"), indent=1)
        print(key, rec["success"], rec["seconds"], flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 4:
        MAPPING_OVERRIDE = sys.argv[4]
        PLANS[:] = [p for p in PLANS if p[2] in ("03", "04", "18")]
    main(*sys.argv[1:4])
