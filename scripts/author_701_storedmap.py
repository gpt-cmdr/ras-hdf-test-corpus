"""Produce a HEC-RAS 7.0.1 RAS Mapper stored map (WSE + depth, Max) for a 7.0.1 run.

Copies the run folder (so the receipted run stays untouched), then calls
ras_commander RasMap.store_all_maps(mode="selected") with HEC-RAS 7.0.1's
packaged RAS Mapper helper. Lists every HDF it writes (PostProcessing.hdf is the
detection case: Results only, no root attributes) with sizes and hashes.

Usage: python -B author_701_storedmap.py RAS_COMMANDER_SRC RUN_DIR WORK_DIR PLAN
"""
import hashlib
import json
import os
import shutil
import sys
import traceback


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main(src, run_dir, work, plan):
    sys.path.insert(0, src)
    from ras_commander import RasMap, init_ras_project
    if os.path.exists(work):
        shutil.rmtree(work)
    shutil.copytree(run_dir, work)
    before = {os.path.join(r, f) for r, _, fs in os.walk(work) for f in fs}
    rec = {"hecras_version": "7.0.1", "plan": plan, "run_dir": run_dir}
    try:
        ras = init_ras_project(work, "7.0.1", ras_object="new")
        rec["result"] = RasMap.store_all_maps(plan, ras_object=ras, mode="selected", wse=True, depth=True,
                                              profile="Max", ras_version="7.0.1", timeout=1200)
    except Exception:
        rec["error"] = traceback.format_exc()[-2000:]
    new = sorted({os.path.join(r, f) for r, _, fs in os.walk(work) for f in fs} - before)
    rec["new_files"] = {os.path.relpath(p, work): {"bytes": os.path.getsize(p), "sha256": sha(p)} for p in new}
    json.dump(rec, open(os.path.join(work, "author_701_storedmap.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in rec.items() if k != "result"}, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:5])
