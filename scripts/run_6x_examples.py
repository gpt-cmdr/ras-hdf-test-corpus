"""Run HEC example plans in an installed HEC-RAS 6.x to produce small native fixtures.

Each plan runs on a fresh copy of its example project via
ras_commander.RasCmdr.compute_plan (HEC-RAS command line). With a mapping
interval, only the copied plan's "Mapping Interval=" line is changed, so 2D
output stays small. Results go to run_<version>_results.json in RUNS_ROOT.

Usage:
  python -B run_6x_examples.py RAS_COMMANDER_SRC VERSION EXAMPLES_ROOT RUNS_ROOT PROJECT:PRJ:PLAN[:MAPPING[:TAG]] ...
(TAG distinguishes runs of the same plan with different overrides)
"""
import hashlib
import json
import os
import shutil
import sys
import time
import traceback


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def override(dest, prj, plan, mapping):
    """Apply plan-line overrides. ``mapping`` is either an interval (sets
    "Mapping Interval=") or ';'-separated "Key=Value" replacements."""
    pf = os.path.join(dest, f"{prj[:-4]}.p{plan}")
    lines = open(pf, encoding="latin-1").read().splitlines()
    if mapping:
        reps = dict(x.split("=", 1) for x in mapping.split(";")) if "=" in mapping else {"Mapping Interval": mapping}
        lines = [f"{l.split('=', 1)[0]}={reps[l.split('=', 1)[0]]}" if "=" in l and l.split("=", 1)[0] in reps else l
                 for l in lines]
        with open(pf, "w", encoding="latin-1", newline=chr(13) + chr(10)) as f:
            f.write(chr(10).join(lines) + chr(10))
    return [l for l in lines if l.startswith(("Mapping Interval=", "Output Interval=", "Computation Interval=",
                                              "Run Sediment="))]


def main(src, version, examples, runs, specs):
    sys.path.insert(0, src)
    import ras_commander
    from ras_commander import RasCmdr, init_ras_project
    out_path = os.path.join(runs, f"run_{version}_results.json")
    results = json.load(open(out_path)) if os.path.exists(out_path) else {}
    for spec in specs:
        proj, prj, plan, *rest = spec.split(":")
        mapping = rest[0] if rest else None
        tag = rest[1] if len(rest) > 1 else None
        key = f"{os.path.basename(proj)}.p{plan}" + ((".map" + mapping if "=" not in mapping else ".ovr") if mapping else "") + ("." + tag if tag else "")
        if results.get(key, {}).get("success"):
            continue
        dest = os.path.join(runs, key.replace(".", "_").replace(" ", "_"))
        if os.path.exists(dest):
            shutil.rmtree(dest)
        shutil.copytree(os.path.join(examples, proj), dest)
        rec = {"project": proj, "plan": plan, "ras_version": version, "copy": dest,
               "ras_commander_file": ras_commander.__file__,
               "method": "RasCmdr.compute_plan(plan, ras_object, num_cores=2, clear_geompre=True)",
               "plan_settings": override(dest, prj, plan, mapping)}
        t0 = time.time()
        try:
            ras = init_ras_project(dest, version, ras_object="new")
            r = RasCmdr.compute_plan(plan, ras_object=ras, num_cores=2, clear_geompre=True)
            rec["result"] = str(r)[:2000]
            rec["success"] = bool(r) if not hasattr(r, "success") else bool(r.success)
        except Exception:
            rec["error"] = traceback.format_exc()[-2000:]
            rec["success"] = False
        rec["seconds"] = round(time.time() - t0, 1)
        rec["hdf_files"] = {f: {"bytes": os.path.getsize(os.path.join(dest, f)), "sha256": sha(os.path.join(dest, f))}
                            for f in sorted(os.listdir(dest)) if f.lower().endswith(".hdf")}
        results[key] = rec
        json.dump(results, open(out_path, "w"), indent=1)
        print(key, rec["success"], rec["seconds"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
