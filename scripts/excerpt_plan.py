"""Excerpt build plan: build, verify and measure every proposed excerpt (read-only on sources).

Each excerpt is written to a temporary directory, checked with verify_excerpt.py,
measured, and deleted. Results go to excerpt_measurements.json, which
build_proposed_manifest.py reads. The same EXCERPTS table is the recipe the
release build would use.

Usage: python -I excerpt_plan.py [ID ...]     (no IDs = all)
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
F = "D:/CLB-Dev/ras-native-release/fixtures/"
C = F + "h4/corpus/"
EBFE_GLAISE = ("H:/eBFE_Audit_Recovery_20261008/backfill_recovery_20261009/"
               "little_red7_full_original_sources_v1/Glaise Creek-White River_1101001306/")
EBFE_AO = ("<CLB_LOCAL>/austin_oyster_ebfe/organized/"
           "AustinOyster_12040205/RAS Model/AustinOyster/Input/")

# Whole preprocessed property-table families (Values + the Info tables that index
# them), removed together so the excerpt stays internally consistent.
PROPTABLES = ["Faces Area Elevation Info", "Faces Area Elevation Values",
              "Cells Volume Elevation Info", "Cells Volume Elevation Values"]
ROWS = ["--rows", "8", "--keep-last"]

R701 = "D:/CLB-Dev/ras701-corpus/runs/"  # run_6x_examples.py outputs, HEC-RAS 7.0.1 (2026-10-24)

# id -> (source path, extra args)
EXCERPTS = {
    # 7.0.1 1D/2D refined grid: laterals, bridges, inline, breach, storage areas;
    # native 7.0.1 property tables kept, time axes trimmed.
    "hec701/BaldEagleDamBrk.p15": (R701 + "BaldEagleCrkMulti2D_p15_map1HOUR/BaldEagleDamBrk.p15.hdf", ROWS),
    "hec701/BaldEagleDamBrk.p03": (C + "701/BaldEagleCrkMulti2D/p03/F0/BaldEagleDamBrk.p03.hdf", ROWS),
    "hec701/BaldEagleDamBrk.p03.all2d": (C + "701/BaldEagleCrkMulti2D/p03/F1_all2d/BaldEagleDamBrk.p03.hdf", ROWS),
    "hec701/BaldEagleDamBrk.p03.warmup_restart": (C + "701/BaldEagleCrkMulti2D/p03/F2F4_warmup_restart/BaldEagleDamBrk.p03.hdf", ROWS),
    "hec701/BaldEagleDamBrk.p03.refpts": (C + "701/BaldEagleCrkMulti2D/p03/F3_refpts_lines/BaldEagleDamBrk.p03.hdf", ROWS),
    "hec701/BaldEagleDamBrk.p03.all2d.noproptables": (C + "701/BaldEagleCrkMulti2D/p03/F1_all2d/BaldEagleDamBrk.p03.hdf", ROWS + ["--exclude-basename"] + PROPTABLES),
    "hec701/BaldEagleDamBrk.p03.refpts.noproptables": (C + "701/BaldEagleCrkMulti2D/p03/F3_refpts_lines/BaldEagleDamBrk.p03.hdf", ROWS + ["--exclude-basename"] + PROPTABLES),
    "hec701/EtherHollow.p01.bingham700.noproptables": (C + "fixtures-20261022-ether-hollow/full_2core/bingham_ty700/EtherHollow.p01.hdf", ROWS + ["--exclude-basename"] + PROPTABLES),
    "hec701/BaldEagleDamBrk.p18.all2d": (C + "701/BaldEagleCrkMulti2D/p18/F1_all2d/BaldEagleDamBrk.p18.hdf", ROWS),
    "hec701/BaldEagleDamBrk.p06.infil": (C + "701/BaldEagleCrkMulti2D/p06/infil_regions/BaldEagleDamBrk.p06.hdf", ROWS),
    "hec701/BaldEagleDamBrk.p06.infil.noproptables": (C + "701/BaldEagleCrkMulti2D/p06/infil_regions/BaldEagleDamBrk.p06.hdf", ROWS + ["--exclude-basename"] + PROPTABLES),
    "hec701/DavisStormSystem.p02": (C + "701/Davis/p02/F0/DavisStormSystem.p02.hdf", ROWS),
    "hec701/DavisStormSystem.p02.all2d": (C + "701/Davis/p02/F1_all2d/DavisStormSystem.p02.hdf", ROWS),
    "hec701/Weise.p01": (C + "701/Weise_2D/p01/sed_active_layer/Weise.p01.hdf", ROWS),
    "hec701/Chippewa_2D.p02": (C + "701/Chippewa_2D/p02/sed_active_layer_2d/Chippewa_2D.p02.hdf", ROWS),
    "hec701/EtherHollow.p01.bingham700": (C + "fixtures-20261022-ether-hollow/full_2core/bingham_ty700/EtherHollow.p01.hdf", ROWS),
    "hec66/BaldEagleDamBrk.p07": (F + "structures-fixtures/BaldEagleDamBrk.p07.hdf", ROWS),
    "hec66/BaldEagleDamBrk.p07.noproptables": (F + "structures-fixtures/BaldEagleDamBrk.p07.hdf", ROWS + ["--exclude-basename"] + PROPTABLES),
    "hec66/BaldEagleDamBrk.p03.refpts": (C + "66/BaldEagleCrkMulti2D/p03/F3_refpts_lines/BaldEagleDamBrk.p03.hdf", ROWS),
    "hec66/Weise.p01": (F + "wave3b-fixtures/sediment-2d-Weise.p01.hdf", ROWS),
    "hec66/DavisStormSystem.p02": (C + "66/Davis/p02/F0/DavisStormSystem.p02.hdf", ROWS),
    "clb/Homewood.p02": (HERE + "/Homewood.p02.hdf", ROWS + ["--exclude-basename"] + PROPTABLES),
    "clb/CahabaRiver.g03": (F + "wave3b-fixtures/extra-CahabaRiver.g03.hdf", ["--exclude-basename"] + PROPTABLES),
    "ebfe/1101001306.p01": (EBFE_GLAISE + "Output/1101001306.p01.hdf", ROWS + ["--exclude-basename"] + PROPTABLES),
    "rbfs/DowntownCorpusChris.p17": (HERE + "/_tmp_rbfs/DowntownCorpusChris.p17.hdf", ROWS + ["--exclude-basename"] + PROPTABLES),
    # eBFE 6.3.1, 587k cells: feature-only excerpt (refinement regions, reference
    # lines, BC lines, breaklines, 2D attribute table, reference-line series,
    # summaries, Time axes). Mesh arrays and per-cell/face series removed.
    "ebfe/1101001306.p01.features": (EBFE_GLAISE + "Output/1101001306.p01.hdf", ROWS + [
        "--include-only", "Plan Data", "Event Conditions", "Results/Unsteady/Summary",
        "Geometry/2D Flow Area Refinement Regions", "Geometry/Reference Lines",
        "Geometry/Boundary Condition Lines", "Geometry/2D Flow Area Break Lines",
        "Geometry/2D Flow Areas/Attributes",
        "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Time",
        "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Time Date Stamp",
        "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Reference Lines",
        "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/2D Flow Areas/default geometry/Boundary Conditions"]),
    # HEC-RAS 5.0.7 delivered plan whose root File Type says "HEC-RAS Geometry".
    # Structural excerpt: everything except the 1.87M-cell mesh arrays and
    # per-element result series; keeps root attrs, Plan Data, Event Conditions,
    # result summaries, Time axes and the 2D area attribute table.
    "ebfe/AustinOyster.p03.v507": (EBFE_AO + "AustinOyster.p03.hdf", [
        "--include-only", "Plan Data", "Event Conditions",
        "Results/Unsteady/Summary",
        "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Time",
        "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Time Date Stamp",
        "Geometry/2D Flow Areas/Attributes", "Geometry/Boundary Condition Lines",
        "Geometry/Structures/Attributes"]),
}


def run(eid):
    src, extra = EXCERPTS[eid]
    with tempfile.TemporaryDirectory() as t:
        dst = os.path.join(t, "x.hdf")
        b = subprocess.run([sys.executable, "-I", os.path.join(HERE, "excerpt_hdf.py"), src, dst] + extra,
                           capture_output=True, text=True)
        if b.returncode:
            return {"id": eid, "error": b.stderr[-400:]}
        v = subprocess.run([sys.executable, "-I", os.path.join(HERE, "verify_excerpt.py"), src, dst],
                           capture_output=True, text=True)
        prov = json.load(open(dst + ".provenance.json"))
        return {"id": eid, "source": src, "args": extra, "source_bytes": prov["source_bytes"],
                "source_sha256": prov["source_sha256"], "excerpt_bytes": prov["excerpt_bytes"],
                "excerpt_sha256": prov["excerpt_sha256"], "truncated": len(prov["truncated"]),
                "excluded": prov["excluded"][:40], "n_excluded": len(prov["excluded"]),
                "verify": v.stdout.strip()[:200]}


def main(ids):
    path = os.path.join(HERE, "excerpt_measurements.json")
    res = json.load(open(path)) if os.path.exists(path) else {}
    for eid in ids or list(EXCERPTS):
        r = run(eid)
        res[eid] = r
        print(f"{eid:48} {r.get('source_bytes', 0)/1e6:8.1f} -> {r.get('excerpt_bytes', 0)/1e6:7.2f} MB "
              f"{r.get('verify', r.get('error', ''))[:60]}", flush=True)
        json.dump(res, open(path, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
