"""Assemble proposed_manifest.json (revision 4, 2026-10-24). Read-only on sources.

Support policy (maintainer, 2026-10-24): CI tests only the latest HEC-RAS
version, 7.0.1. smoke/core/extended hold only files written by HEC-RAS 7.0.1
(plans, geometries, RAS Mapper layers) plus synthetic fixtures. Older-version
files are assigned automatically from their writer (root "File Version", or
WRITER below for files without one) to legacy/archive.

Profiles and caps:
  smoke     what third-party CI (terrio) downloads; each file <= 10 MB, total ~50 MB; 7.0.1 only
  core      engine / ras-commander per-PR CI; each file <= 25 MB (superset of smoke); 7.0.1 only
  extended  nightly / manual; 7.0.1 files above the core cap, full time axes
  legacy    engine best-effort suites only (not per-PR, not terrio); HEC-RAS 5.0.x-7.0;
            each file <= 25 MB, total <= 100 MB
  archive   older-version files above the legacy cap; on demand, no CI
  external  fetched from the upstream public host, not republished
Nothing above ~50 MB may appear in a per-PR profile (smoke/core). The caps and
the 7.0.1 coverage rule are asserted below. Excluded material is checked against a
local, git-ignored deny list (denylist_check.py) and is never named here.

Sizes: full files use their byte size. Excerpts use the measured sizes in
excerpt_measurements.json (excerpt_plan.py: built, verified byte-exact and
deleted). Source hashes come from candidate_inventory.json or are computed here
(cached in _hash_cache.json).

Usage: python -I build_proposed_manifest.py
"""
import hashlib
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir
from property_table_census import census as pt_census  # noqa: E402
from coverage_701 import REQUIREMENTS, features as feature_census  # noqa: E402

HERE =os.path.dirname(os.path.abspath(__file__))
INV = {r["path"]: r for r in json.load(open(os.path.join(HERE, "candidate_inventory.json")))}
EXM = json.load(open(os.path.join(HERE, "excerpt_measurements.json")))
CACHE_P = os.path.join(HERE, "_hash_cache.json")
CACHE = json.load(open(CACHE_P)) if os.path.exists(CACHE_P) else {}

MB = 1_000_000
SMOKE_FILE, SMOKE_TOTAL, CORE_FILE, PER_PR_MAX = 10 * MB, 55 * MB, 25 * MB, 50 * MB
LEGACY_FILE, LEGACY_TOTAL = 25 * MB, 100 * MB
CURRENT = "7.0.1"

F = "D:/CLB-Dev/ras-native-release/fixtures/"
C = F + "h4/corpus/"
P = F + "parity-w2-work/"
ZIP66 = "H:/CLB-Repos/ras-commander/Example_Projects_6_6.zip"
RBFS_TMP = HERE + "/_tmp_rbfs/"
BLE = ("H:/RBFS_webmap_extracted/_worker_handoff/2026-07-27/rbfs-statewide-v1/CLB09/_failed_workspace_recovery/"
       "rbfs-statewide-v1-clb09-big-cow-creek-r3-20260730T220330Z/work/expanded/package_001_1201000506 Big Cow Creek/"
       "1201000506 Big Cow Creek/SUPPLEMENTAL DATA/Previous Studies/BLE Model/Hydraulic Models/BigCowCreek/")
GLAISE = ("H:/eBFE_Audit_Recovery_20261008/backfill_recovery_20261009/little_red7_full_original_sources_v1/"
          "Glaise Creek-White River_1101001306/")
AO_ORG = ("<CLB_LOCAL>/austin_oyster_ebfe/organized/AustinOyster_12040205/"
          "RAS Model/AustinOyster/Input/")
R701 = "D:/CLB-Dev/ras701-corpus/runs/"          # run_6x_examples.py, HEC-RAS 7.0.1 (2026-10-24)
L701 = "D:/CLB-Dev/ras701-corpus/layers/BaldEagleCrkMulti2D/Layers701/"  # author_701_layers.py
T701 = "D:/CLB-Dev/ras701-corpus/terrain701/"     # author_701_terrain.py
S701 = "D:/CLB-Dev/ras701-corpus/synthetic/"      # make_synthetic_fixtures.py
SM701 = "D:/CLB-Dev/ras701-corpus/storedmap/Muncie_p03/2D 50ft Grid/"  # author_701_storedmap.py
S248 = "D:/CLB-Dev/ras701-corpus/runs/"          # run_6x_examples.py, eBFE Stream248 in HEC-RAS 7.0.1 (2026-10-25)
R507 = "D:/CLB-Dev/ras507-corpus/runs/"           # run_507_examples.py, HEC-RAS 5.0.7 (2026-10-24)
RL701 = "D:/CLB-Dev/ras701-corpus/reflines/"      # author_701_reflines.py, HEC-RAS 7.0.1 (2026-10-25)
KNOWN_SHA = {AO_ORG + "AustinOyster.p03.hdf": "fdaff5045ad36bf5d424489ff64b3d86a1e0e3ef92a628554488f009047cad92"}

# ---------------------------------------------------------------- provenance
HEC_DL = "https://www.hec.usace.army.mil/software/hec-ras/download.aspx"
HEC_ATTR = "Source: US Army Corps of Engineers, Hydrologic Engineering Center (HEC), HEC-RAS example projects"
HEC_LIC = "Public domain (US Government work, 17 USC 105); attribution to HEC requested"
EBFE_ATTR = "Source: FEMA estimated Base Flood Elevation (eBFE) program"
RBFS_ATTR = "Source: Texas General Land Office, River Basin Flood Studies"
PD = "Public domain (maintainer ruling 2026-10-24)"
JB = "Model by Jacob Beatty, CLB Engineering Corporation; used with permission"


def hec_shipped(member):
    return {"program": "USACE HEC-RAS example projects", "download_location": HEC_DL,
            "zip_name": "Example_Projects_6_6.zip", "zip_sha256_local_copy":
            "ea239b506155a2dfeda2af80b3c2af948eef42c40218bcd65de472cfed386887",
            "path_in_zip": member, "attribution": HEC_ATTR, "licence": HEC_LIC,
            "verification": "byte-identical to the zip member (sha256 compared 2026-10-24)"}


def hec_run(project, version, extra=""):
    return {"program": "USACE HEC-RAS example projects; outputs computed by CLB Engineering",
            "download_location": HEC_DL, "zip_name": "Example_Projects_6_6.zip",
            "path_in_zip": project, "computed_with": f"HEC-RAS {version} via ras-commander (fixtures-20261021 MANIFEST/fixture.json receipts)",
            "attribution": HEC_ATTR + "; computed by CLB Engineering Corporation" + extra,
            "licence": HEC_LIC + "; CLB computation under the corpus licence"}


def hec_run701(project, plan, settings):
    return {"program": "USACE HEC-RAS example projects; outputs computed by CLB Engineering",
            "download_location": HEC_DL, "zip_name": "Example_Projects_6_6.zip",
            "zip_sha256_local_copy": "ea239b506155a2dfeda2af80b3c2af948eef42c40218bcd65de472cfed386887",
            "path_in_zip": project,
            "computed_with": f"HEC-RAS 7.0.1 (June 2026) via ras-commander 0.108.0 RasCmdr.compute_plan(plan {plan}, "
                             "num_cores=2, clear_geompre=True) on a fresh copy; receipt "
                             "D:/CLB-Dev/ras701-corpus/runs/run_7.0.1_results.json (run_6x_examples.py)",
            "plan_changes": settings,
            "attribution": HEC_ATTR + "; computed by CLB Engineering Corporation",
            "licence": HEC_LIC + "; CLB computation CC0"}


REFLINE701_PROV = lambda project, plan, settings: {
    "program": "USACE HEC-RAS example projects; reference lines/points added and outputs computed by CLB Engineering",
    "download_location": HEC_DL, "zip_name": "Example_Projects_6_6.zip",
    "zip_sha256_local_copy": "ea239b506155a2dfeda2af80b3c2af948eef42c40218bcd65de472cfed386887",
    "path_in_zip": project,
    "computed_with": f"CLB-generated from HEC example {project} (public domain source): reference lines and points "
                     "injected with ras-commander 0.108.1 (git e851408e5) GeomReferenceFeatures.add_reference_lines / "
                     "add_reference_points / generate_reference_lines_from_longitudinal_line (notebooks 207/314), then "
                     f"HEC-RAS 7.0.1 via RasCmdr.compute_plan(plan {plan}, num_cores=2, clear_geompre=True, force_rerun=True, "
                     "verify=True) on a fresh copy; receipt D:/CLB-Dev/ras701-corpus/reflines/RECEIPT.md + "
                     "author_701_reflines.json (author_701_reflines.py)",
    "plan_changes": settings,
    "attribution": HEC_ATTR + "; reference features and computation by CLB Engineering Corporation",
    "licence": HEC_LIC + "; CLB additions and computation CC0"}

HEC507_PROV = lambda project, plan: {
    "program": "USACE HEC-RAS 5.0.7 example projects; outputs computed by CLB Engineering",
    "download_location": HEC_DL + " (HEC-RAS 5.0.7 installer, HEC-RAS_507_Setup.exe, sha256 "
                         "c43d0dc26ca33ee4c8b0e0e27c79d3b8d6a5e6a6e95bde5b21e8f0776eb8b795)",
    "examples_archive": "installed 'Example Projects/Example_Projects.exe' (7z SFX, sha256 "
                        "874cdbd5817605c5c6f7e4f2f729a05590d79a742770a3c646f5c1b12df916d7), unpacked with 7-Zip, not executed",
    "path_in_archive": project,
    "computed_with": f"HEC-RAS 5.0.7 (already installed) via ras-commander RasControl COM (RAS507.HECRASController), "
                     f"plan {plan}, fresh copy, only 'Mapping Interval=1HOUR' changed; receipt "
                     "D:/CLB-Dev/ras507-corpus/runs/run_507_results.json (run_507_examples.py)",
    "attribution": HEC_ATTR + "; computed by CLB Engineering Corporation", "licence": HEC_LIC + "; CLB computation CC0"}

LAYER701_PROV = lambda what: {
    "program": "HEC-RAS 7.0.1 RAS Mapper layer authored by CLB from HEC example inputs",
    "inputs": "Example_Projects_6_6.zip: 2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D/Land Classification/LandCover.tif, "
              "Soils Data/Hydrologic Soil Groups.tif and the class tables of the shipped layers",
    "computed_with": f"HEC-RAS 7.0.1 RasMapperLib via ras-commander 0.108.0 ({what}); 6,000 ft extent "
                     "(1965981.77, 289578.11)-(1971981.77, 295578.11) PA North ft; receipt "
                     "D:/CLB-Dev/ras701-corpus/layers/BaldEagleCrkMulti2D/author_701_layers.json (author_701_layers.py)",
    "attribution": HEC_ATTR + "; layer authored by CLB Engineering Corporation", "licence": HEC_LIC + "; CLB authoring CC0"}

TERRAIN701_PROV = {
    "program": "HEC-RAS 7.0.1 terrain authored by CLB from HEC example terrain",
    "inputs": "Example_Projects_6_6.zip: 2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D/Terrain/Terrain50.dtm_20ft.tif "
              "(windowed rasterio copy of the same 6,000 ft extent) + Terrain/Projection.prj",
    "computed_with": "HEC-RAS 7.0.1 RasProcess.exe CreateTerrain via ras-commander RasTerrain.create_terrain_hdf; "
                     "receipt D:/CLB-Dev/ras701-corpus/terrain701/author_701_terrain.json (author_701_terrain.py)",
    "attribution": HEC_ATTR + "; terrain authored by CLB Engineering Corporation", "licence": HEC_LIC + "; CLB authoring CC0"}

STOREDMAP701_PROV = {
    "program": "HEC-RAS 7.0.1 RAS Mapper stored map computed by CLB from a HEC example run",
    "inputs": "hec701r/Muncie.p03 (Example_Projects_6_6.zip: 2D Unsteady Flow Hydraulics/Muncie, run in 7.0.1) and the "
              "example terrain",
    "computed_with": "ras-commander RasMap.store_all_maps(mode='selected', wse=True, depth=True, profile='Max') with "
                     "HEC-RAS 7.0.1 RAS Mapper; receipt D:/CLB-Dev/ras701-corpus/storedmap/Muncie_p03/author_701_storedmap.json",
    "attribution": HEC_ATTR + "; stored map computed by CLB Engineering Corporation", "licence": HEC_LIC + "; CLB computation CC0"}

JH = "H:/Jacob/Homewood/HECRAS/"
HOMEWOOD_LAYER_PROV = lambda f: {
    "program": "CLB Engineering model (Homewood)", "credit": JB, "attribution": JB,
    "licence": "CLB-owned; CC0 (used with permission)",
    "copy_used": f"H:/Jacob/Homewood/HECRAS/Land Classification/{f} (Jacob Beatty's working folder; referenced by "
                 "Homewood.rasmap). Same project as clb/Homewood.p02: its GreenAmpt_Infiltration.hdf is byte-identical "
                 "(sha256 92e7ec99...) to the wave3b copy already in the manifest",
    "writer_note": "HEC-RAS 7.0 project (rasmap Version 2.0.0, geometry Program Version 7.00)"}

STREAM248_URL = "https://ebfedata.s3.amazonaws.com/12100203_SanMarcos/12100203_Models.zip"
STREAM248_PROV = lambda plan: {
    **ebfe(STREAM248_URL, "12100203_Models.zip", "Hydraulic_Models/1210020304/Stream248/",
           "HUC8 12100203 San Marcos (FEMA Region 6, Texas), HUC10 1210020304, 1D BLE model 'Stream248'. zip sha256 "
           "3a900b5ed587567e66b13d966e008bc336ea6155d164c44df2fd1c742a061c7a (68,778,649 bytes). Delivered as HEC-RAS 4.10 "
           "steady text files; the package has no HDF."),
    "program": "FEMA eBFE model computed by CLB in HEC-RAS 7.0.1" + ("" if plan == "01" else "; plan 02 and flow u01 added by CLB"),
    "computed_with": f"HEC-RAS 7.0.1 via ras-commander 0.108.0 RasCmdr.compute_plan(plan {plan}, num_cores=2, clear_geompre=True) "
                     "on a fresh copy (run_6x_examples.py); receipts provenance/ras701-corpus/runs/run_7.0.1_results.json "
                     f"(key Stream248.p{plan}) and provenance/ras701-corpus/ebfe-stream248/RECEIPT.json (original 7.0.1 run of the same inputs: delivered members, CLB additions; this release uses an identical rerun whose only differences are Last Edited timestamps and the project path)",
    "clb_changes_vs_delivered": ["Stream248.prj lists p02 and u01",
                                 "new Stream248.p02 'CLB Unsteady Constant 10yr' and Stream248.u01 (constant 450 cfs = eBFE "
                                 "10-year at RS 7000 for 24 h; normal depth 0.005 at RS 576; 10 s computation interval)"],
    "attribution": EBFE_ATTR + "; computed in HEC-RAS 7.0.1 by CLB Engineering Corporation",
    "licence": PD + "; CLB computation and additions CC0"}

SYN_PROV = lambda what: {"program": "Synthetic (CLB Engineering)", "generator": "make_synthetic_fixtures.py",
                         "what": what, "attribution": "Synthetic fixture by CLB Engineering Corporation", "licence": "CC0 1.0"}


def ebfe(url, zip_name, path_in_zip, note=""):
    return {"program": "FEMA estimated Base Flood Elevation (eBFE)", "download_location": url,
            "portal": "https://webapps.usgs.gov/infrm/estBFE/", "zip_name": zip_name,
            "path_in_zip": path_in_zip, "attribution": EBFE_ATTR, "licence": PD, "note": note}


TDIS = "TDIS Data Modeling and Query Tool, https://dmqt.cloud.tdis.io (free registration)"


def rbfs(archive_key, zip_name, path_in_zip, note=""):
    return {"program": "Texas GLO River Basin Flood Studies (RBFS)", "download_location": TDIS,
            "tdis_archive_key": archive_key, "zip_name": zip_name, "path_in_zip": path_in_zip,
            "attribution": RBFS_ATTR, "licence": PD, "note": note}


DCC_KEY = "rbfs/approved-models/west-region/100-percent-final/archive/979fc50e-ff22-4f00-a0f3-514e54dc7420/"
DCC_ZIP = "HUC1211020202_DowntownCorpusChristi_100%_Final.zip"
DCC_IN = ("HUC1211020202_DowntownCorpusChristi_100%25_Final/HUC1211020202_DowntownCorpusChristi_100%_Final/"
          "DowntownCorpusChristi100%Final/DowntownCorpusChristi_RASv641/DowntownCorpusChristi/")
BCC_KEY = "rbfs/approved-models/east-region/100-percent-final/archive/24bcb72d-f9c2-4c18-9917-473b4d4249c6/"
BCC_ZIP = "1201000506 Big Cow Creek.zip"
BCC_IN = "1201000506 Big Cow Creek/SUPPLEMENTAL DATA/Previous Studies/BLE Model/Hydraulic Models/BigCowCreek/"
BCC_NOTE = ("TDIS catalog TDIS-d6074d6e-20f3-4314-8804-6b2028eb5f12. FEMA Base Level Engineering model redistributed "
            "as a 'Previous Studies' supplement. Path inside the zip is from CLB's expanded tree; confirm the member "
            "CRC against the TDIS zip at release build.")
GLAISE_URL = "https://ebfedata.s3.amazonaws.com/11010014_LittleRed/11010014_Models.zip"
GLAISE_NOTE = ("Outer member 'Hydraulic Models/Glaise Creek-White River_1101001306.zip' per CLB extraction receipt "
               "FULL_SOURCE_EXTRACTION_RECEIPT.json (CRC-verified). The outer zip's central directory could not be "
               "re-read by HTTP range probe on 2026-10-24; reconfirm membership at release build.")
AO_URL = "https://ebfedata.s3.amazonaws.com/12040205_AustinOyster/12040205_Models.zip"

AO_P01_PROV = {
    "program": "FEMA eBFE-derived; CLB-run plan",
    "derived_from": ebfe(AO_URL, "12040205_Models.zip", "RAS Model/Hydraulic_Models/RAS_Submittal.zip -> Terrain.zip (terrain)"),
    "attribution": EBFE_ATTR + "; SH35 'firehose' geometry, flow and plan by CLB Engineering Corporation",
    "licence": PD + " (eBFE inputs); CLB additions under the corpus licence",
    "clb_changes_vs_delivered": [
        "new geometry g01 'SH35_FIREHOSE': one 3,314-cell 2D area (200 ft spacing, ~15.7 x 15.4 kft) inside the delivered 1,872,746-cell 'Perimeter 1' extent",
        "uses the delivered eBFE terrain (..\\Terrain\\Terrain.hdf, same terrain file date) and delivered default Manning's n 0.06; no land-cover layer",
        "14 breaklines: 12 copied by name from the delivered 1,360, plus 'Breakline 446' split into _BRK01/_BRK02",
        "2 BC lines: 'Emitter1' flow hydrograph (synthetic ramp 0 to 8,640 cfs, 37 hourly rows, 1.5 days) and 'Outlet_DS' normal depth",
        "1 reference line named 'USGS 08078400' (public USGS gage ID); no structures (delivered has one connection)",
        "new flow file u08 '100yr' and plan p01; HEC-RAS 6.6 (delivered model is 5.0.7)",
        "only internal detail: 'Project Filename' attrs hold a CLB worktree path C:\\GH\\rc-wt-956\\working\\austin_bayou_firehose\\...; no client names, credentials or non-public data",
    ],
    "verdict": "no non-public inputs found; publishable in core",
}

LR = "D:/CLB-Dev/ras701-corpus/runs/"
EBFE_RR701 = [
    ("ebfe701/1101001404.g01.rr", "core", "full", LR + "1101001404_p01_ovr_geompre/1101001404.g01.hdf",
     {**ebfe(GLAISE_URL, "11010014_Models.zip",
             "Hydraulic Models/Outlet Middle Fork Little Red River_1101001404.zip -> Input/1101001404.g01 (+ Output/1101001404.g01.hdf, "
             "Terrain/, Land Classification/, flow files)",
             "Delivered model is HEC-RAS 6.3.1 (delivered g01.hdf sha256 077ecf70a2a61073021416f18fc738de2cf467a87f7d67a4788b70c182466eff, "
             "231,641 cells, 83 refinement regions). Local CRC-verified extraction: "
             "H:/eBFE_Audit_Recovery_20261008/backfill_recovery_20261009/little_red7_full_original_sources_v1/"
             "Outlet Middle Fork Little Red River_1101001404 (FULL_SOURCE_EXTRACTION_RECEIPT.json)."),
      "program": "FEMA eBFE model re-preprocessed by CLB in HEC-RAS 7.0.1",
      "computed_with": "HEC-RAS 7.0.1 via ras-commander 0.108.0 RasCmdr.compute_plan(plan 01, num_cores=2, clear_geompre=True) "
                       "on an assembled copy (run_ebfe_rr_701.py -> run_6x_examples.py); plan changes 'Run UNet=0', "
                       "'Run PostProcess=0' (geometry preprocessing only); receipt D:/CLB-Dev/ras701-corpus/runs/run_7.0.1_results.json "
                       "key 1101001404.p01.ovr.geompre",
      "result_note": "7.0.1 rewrote the geometry HDF (File Version 'HEC-RAS 7.0.1 June 2026') with all 83 refinement regions, "
                     "breaklines, BC lines and reference lines, but its mesh generation failed: '8 cell(s) with more than 8 sides' "
                     "(6.3.1 accepted the same cell points). The file has the 2D perimeter and 231,641 cell points but no faces "
                     "or property tables, although Geometry 'Complete Geometry' is 'True'. Same failure for 1101001403/05/07 "
                     "(5/10/30 cells).",
      "known_issue": "Known issue: HEC-RAS 7.0.1 rejected the 6.3.1 mesh (cells with more than 8 sides), so the file has no faces or property tables. Not fixed, because the fixture is only used to read refinement regions and other geometry features.",
      "attribution": EBFE_ATTR + "; re-preprocessed in HEC-RAS 7.0.1 by CLB Engineering Corporation",
      "licence": PD + "; CLB processing CC0"},
     "7.0.1-written 2D refinement regions (83), breaklines, BC lines, reference lines; mesh generation failed in 7.0.1 (no faces)", None),
]

# ---------------------------------------------------------------- entries
# (id, profile, mode, path_or_zipmember, provenance, coverage, low_level_native_reason)
Z = lambda m: "zip66!" + m  # member of the local HEC 6.6 example zip
E = [
    # ---- detection / layout anchors: one full native file per writer version
    ("rbfs/BLE.UNT106.p01.v505", "core", "full", BLE + "UNT 106 in Big Cow Cr Watershed/UNT 106 in Big Cow Cr Watershed.p01.hdf",
     rbfs(BCC_KEY, BCC_ZIP, BCC_IN + "UNT 106 in Big Cow Cr Watershed/UNT 106 in Big Cow Cr Watershed.p01.hdf", BCC_NOTE),
     "HEC-RAS 5.0.5 1D steady plan; root File Type 'HEC-RAS Geometry' although it holds Results; no Projection attr", "native writer 5.0.5"),
    ("rbfs/BLE.UNT123.p01.v507", "smoke", "full", BLE + "UNT 123 in Big Cow Cr Watershed/UNT 123 in Big Cow Cr Watershed.p01.hdf",
     rbfs(BCC_KEY, BCC_ZIP, BCC_IN + "UNT 123 in Big Cow Cr Watershed/UNT 123 in Big Cow Cr Watershed.p01.hdf", BCC_NOTE),
     "HEC-RAS 5.0.7 1D steady plan; root File Type 'HEC-RAS Geometry' although it holds Results (the 5.0.7 detection case)", "native writer 5.0.7"),
    ("rbfs/BLE.UNT123.g01.v507", "core", "full", BLE + "UNT 123 in Big Cow Cr Watershed/UNT 123 in Big Cow Cr Watershed.g01.hdf",
     rbfs(BCC_KEY, BCC_ZIP, BCC_IN + "UNT 123 in Big Cow Cr Watershed/UNT 123 in Big Cow Cr Watershed.g01.hdf", BCC_NOTE),
     "5.0.7 geometry HDF (true geometry, same File Type) to contrast with the plan", None),
    ("ebfe/AustinOyster.p03.v507.structural", "smoke", "excerpt:ebfe/AustinOyster.p03.v507", AO_ORG + "AustinOyster.p03.hdf",
     ebfe(AO_URL, "12040205_Models.zip", "RAS Model/Hydraulic_Models/RAS_Submittal.zip -> Output.zip -> AustinOyster.p03.hdf (relocated to Input/ by reconstruction; bytes unmodified)"),
     "HEC-RAS 5.0.7 2D unsteady plan (1.87M cells) whose File Type says 'HEC-RAS Geometry'; structural excerpt keeps root attrs, Plan Data, Event Conditions, summaries, Time axes, 2D attribute table, BC lines", None),
    ("hec-asis/WaterQualityExamp.p01", "smoke", "full", Z("Water Quality/Nutrient Example/WaterQualityExamp.p01.hdf"),
     hec_shipped("Water Quality/Nutrient Example/WaterQualityExamp.p01.hdf"),
     "HEC-RAS 6.0.0 SI steady plan; File Type 'HEC-RAS Geometry' with Results (6.x instance of the mislabel)", "native writer 6.0.0"),
    ("hec-asis/WaterQualityExamp.g01", "core", "full", Z("Water Quality/Nutrient Example/WaterQualityExamp.g01.hdf"),
     hec_shipped("Water Quality/Nutrient Example/WaterQualityExamp.g01.hdf"), "SI geometry 6.0.0", None),
    ("hec-asis/BaldEagleDamBrk.g13", "core", "full", Z("2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D/BaldEagleDamBrk.g13.hdf"),
     hec_shipped("2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D/BaldEagleDamBrk.g13.hdf"), "2D + storage-area geometry", "native writer 6.2.0"),
    ("hec-asis/Muncie.g04", "smoke", "full", Z("2D Unsteady Flow Hydraulics/Muncie/Muncie.g04.hdf"),
     hec_shipped("2D Unsteady Flow Hydraulics/Muncie/Muncie.g04.hdf"), "1D/2D geometry, breaklines", "native writer 6.3 Beta 2"),
    ("hec-asis/Chippewa_2D.g01", "core", "full", Z("2D Sediment Transport/Chippewa_2D/Chippewa_2D.g01.hdf"),
     hec_shipped("2D Sediment Transport/Chippewa_2D/Chippewa_2D.g01.hdf"), "2D sediment geometry (File Type Results)", "native writer 6.4"),
    ("hec-asis/SimplifiedBSTEM.g01", "core", "full", Z("1D Sediment Transport/BSTEM - Simple Example/SimplifiedBSTEM.g01.hdf"),
     hec_shipped("1D Sediment Transport/BSTEM - Simple Example/SimplifiedBSTEM.g01.hdf"), "1D BSTEM geometry", "native writer 6.5"),
    ("rbfs/DowntownCorpusChris.g12", "smoke", "full", RBFS_TMP + "DowntownCorpusChris.g12.hdf",
     rbfs(DCC_KEY, DCC_ZIP, DCC_IN + "DowntownCorpusChris.g12.hdf"), "6.4.1 2D geometry incl. property tables", "native writer 6.4.1"),
    ("clb/AustinOyster.p01", "smoke", "full", F + "golden/AustinOyster.p01.hdf", AO_P01_PROV,
     "6.6 2D unsteady results, reference line TS, BC lines, breaklines; xdist access-violation regression fixture", "native writer 6.6 (results)"),
    ("ext/DavisStormSystem.p02.full", "extended", "full", C + "701/Davis/p02/F0/DavisStormSystem.p02.hdf", hec_run("Pipes (beta)/Davis", "7.0.1"),
     "7.0.1 native 2D + pipe network + pump results, full time axis", None),
    ("hec70/BaldEagleDamBrk.p18.full", "core", "full", F + "structures-fixtures/BaldEagleDamBrk.p18.hdf", hec_run("2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D (p18)", "7.0"),
     "7.0 (April 2026) native two-area 2D-to-2D results", "native writer 7.0"),
    # ---- 1D (HEC shipped geometry, 6.3 Beta 2 writer)
    *[(f"hec-asis/{n}", "core", "full", Z(m), hec_shipped(m), cov, None) for n, m, cov in [
        ("Baxter.g02", "1D Steady Flow Hydraulics/Baxter RAS Mapper/RAS Model/Baxter.g02.hdf", "junctions + storage areas"),
        ("beaver.g01", "1D Unsteady Flow Hydraulics/Bridge Hydraulics/beaver.g01.hdf", "bridge geometry"),
        ("ConSpan.g01", "1D Steady Flow Hydraulics/ConSpan Culvert/ConSpan.g01.hdf", "culvert geometry"),
        ("Diamond.g01", "Applications Guide/Example 17 - Unsteady Flow Application/Diamond.g01.hdf", "junctions + storage"),
        ("OrleansEx.g04", "Applications Guide/Example 23 - Urban Modeling/OrleansEx.g04.hdf", "urban 1D, pumps"),
        ("Inline_3Gates.g01", "1D Unsteady Flow Hydraulics/Inline Structure with Gated Spillways/Inline_3Gates.g01.hdf", "gated inline"),
        ("JunctionHydraulics.g01", "1D Unsteady Flow Hydraulics/JunctionHydraulics/JunctionHydraulics.g01.hdf", "junctions"),
        ("3Reach_with_Lat.g01", "1D Unsteady Flow Hydraulics/Lateral Structure connected to a River Reach/3Reach_with_Lat.g01.hdf", "lateral structure"),
        ("UnsteadyEncroachment.g01", "1D Unsteady Flow Hydraulics/Unsteady Flow Encroachment Analysis/UnsteadyEncroachment.g01.hdf", "encroachment (6.6 writer)"),
        ("Muncie.g01", "2D Unsteady Flow Hydraulics/Muncie/Muncie.g01.hdf", "1D + storage areas")]],
    # ---- CLB-computed HEC examples, 6.6
    ("hec66/BaldEagle.p01", "core", "full", P + "computed/Balde_Eagle_Creek_p01/BaldEagle.p01.hdf", hec_run("1D Unsteady Flow Hydraulics/Balde Eagle Creek", "6.6"), "1D unsteady XS time series", None),
    ("hec66/BaldEagle.p02", "core", "full", C + "66/Balde_Eagle_Creek/p02/steady/BaldEagle.p02.hdf", hec_run("1D Unsteady Flow Hydraulics/Balde Eagle Creek", "6.6"), "1D steady, bridges + inline (6.6 pair of hec701)", None),
    ("hec66/Baxter.p01", "core", "full", P + "computed/Baxter_RAS_Mapper_p01/Baxter.p01.hdf", hec_run("Baxter RAS Mapper", "6.6"), "steady junctions/storage", None),
    ("hec66/beaver.p03", "core", "full", P + "computed/Bridge_Hydraulics_p03/beaver.p03.hdf", hec_run("Bridge Hydraulics", "6.6"), "1D unsteady bridge", None),
    ("hec66/ConSpan.p01", "core", "full", P + "computed/ConSpan_Culvert_p01/ConSpan.p01.hdf", hec_run("ConSpan Culvert", "6.6"), "steady culvert", None),
    ("hec66/OrleansEx.p02", "core", "full", P + "computed/Example_23_-_Urban_Modeling_p02/OrleansEx.p02.hdf", hec_run("Example 23", "6.6"), "urban 1D unsteady, pump TS", None),
    ("hec66/Inline_3Gates.p01", "core", "full", P + "computed/Inline_Structure_with_Gated_Spillways_p01/Inline_3Gates.p01.hdf", hec_run("Inline gated spillways", "6.6"), "unsteady gated inline", None),
    ("hec66/JunctionHydraulics.p01", "core", "full", P + "computed/JunctionHydraulics_p01/JunctionHydraulics.p01.hdf", hec_run("JunctionHydraulics", "6.6"), "unsteady junctions", None),
    ("hec66/FLODENCR.p02", "core", "full", F + "wave3b-fixtures/floodway-FLODENCR.p02.hdf", hec_run("Floodway encroachment example", "6.6"), "steady encroachment", None),
    ("hec66/FLODENCR.g01", "core", "full", F + "wave3b-fixtures/floodway-FLODENCR.g01.hdf", hec_run("Floodway encroachment example", "6.6"), "encroachment geometry", None),
    ("hec66/MBex.p01", "core", "full", F + "wave3b-fixtures/sediment-1d-MBex.p01.hdf", hec_run("1D sediment example", "6.6"), "1D sediment", None),
    ("hec66/MBex.g02", "core", "full", F + "wave3b-fixtures/sediment-1d-MBex.g02.hdf", hec_run("1D sediment example", "6.6"), "1D sediment geometry", None),
    ("hec66/DavisStormSystem.g02", "core", "full", C + "66/Davis/p02/F0/DavisStormSystem.g02.hdf", hec_run("Pipes (beta)/Davis", "6.6"), "pipe network geometry 6.6", None),
    ("hec66/Weise.g08", "core", "full", C + "66/Weise_2D/p01/sed_active_layer/Weise.g08.hdf", hec_run("2D Sediment Transport/Weise_2D", "6.6"), "SI 2D geometry", None),
    ("hec66/BaldEagleDamBrk.p07", "core", "excerpt:hec66/BaldEagleDamBrk.p07.noproptables", F + "structures-fixtures/BaldEagleDamBrk.p07.hdf", hec_run("BaldEagleCrkMulti2D (p07)", "6.6"),
     "storage area, SA/2D connection, dam-breach variables; property tables removed", None),
    # ---- CLB-computed HEC examples, 7.0.1
    ("hec701/BaldEagle.p02", "smoke", "full", C + "701/Balde_Eagle_Creek/p02/steady/BaldEagle.p02.hdf", hec_run("Balde Eagle Creek", "7.0.1"), "1D steady, 10 bridges + inline", None),
    ("hec701/BaldEagle.g01", "core", "full", C + "701/Balde_Eagle_Creek/p02/steady/BaldEagle.g01.hdf", hec_run("Balde Eagle Creek", "7.0.1"), "1D geometry", None),
    *[(f"hec701/{n}", "core", "full", C + f"701/{d}", hec_run(proj, "7.0.1"), cov, None) for n, d, proj, cov in [
        ("ConSpan.p01", "ConSpan_Culvert/p01/steady/ConSpan.p01.hdf", "ConSpan", "steady culvert"),
        ("ConSpan.g01", "ConSpan_Culvert/p01/steady/ConSpan.g01.hdf", "ConSpan", "culvert geometry"),
        ("NIT.p01", "Example_12_-_Inline_Structure/p01/steady/NIT.p01.hdf", "Example 12", "steady gated inline"),
        ("NIT.g01", "Example_12_-_Inline_Structure/p01/steady/NIT.g01.hdf", "Example 12", "gated inline geometry"),
        ("BEAVCREK.p01", "Example_2_-_Beaver_Creek/p01/steady/BEAVCREK.p01.hdf", "Example 2", "pressure/weir bridge"),
        ("BEAVCREK.g01", "Example_2_-_Beaver_Creek/p01/steady/BEAVCREK.g01.hdf", "Example 2", "bridge geometry"),
        ("MULTCULV.p01", "Example_4_-_Multiple_Culverts/p01/steady/MULTCULV.p01.hdf", "Example 4", "culvert groups"),
        ("MULTCULV.g01", "Example_4_-_Multiple_Culverts/p01/steady/MULTCULV.g01.hdf", "Example 4", "culvert geometry"),
        ("MULTOPEN.p02", "Example_5_-_Multiple_Openings/p02/steady/MULTOPEN.p02.hdf", "Example 5", "multiple openings"),
        ("MULTOPEN.g02", "Example_5_-_Multiple_Openings/p02/steady/MULTOPEN.g02.hdf", "Example 5", "multiple-opening geometry"),
        ("Pumps.g01", "Pumping_Station_with_Rules/p01/F0/Pumps.g01.hdf", "Pumping Station with Rules", "pump geometry"),
        ("PumpRule.p03", "Pumping_Station_with_Rules/p03/F0/PumpRule.p03.hdf", "Pumping Station with Rules", "pump rules TS"),
        ("PumpRule.g01", "Pumping_Station_with_Rules/p03/F0/PumpRule.g01.hdf", "Pumping Station with Rules", "pump rules geometry"),
        ("Weise.g08", "Weise_2D/p01/sed_active_layer/Weise.g08.hdf", "Weise_2D", "SI 2D geometry 7.0.1"),
        ("Chippewa_2D.p02", "Chippewa_2D/p02/sed_active_layer_2d/Chippewa_2D.p02.hdf", "Chippewa_2D", "2D sediment, active-layer D10/D16/D50/D90 (full: excerpting enlarges it)")]],
    ("hec701/DavisStormSystem.g02", "smoke", "full", C + "701/Davis/p02/F0/DavisStormSystem.g02.hdf", hec_run("Davis", "7.0.1"),
     "pipe network geometry 7.0.1; native pipe Cell/Face Property Tables and 2D face/cell tables (smoke native anchor for pipe tables)", None),
    ("hec701/Pumps.p01", "smoke", "full", C + "701/Pumping_Station_with_Rules/p01/F0/Pumps.p01.hdf", hec_run("Pumping Station with Rules", "7.0.1"), "1D unsteady XS TS, storage area, pump TS", "native writer 7.0.1 (results)"),
    ("hec701/DavisStormSystem.p02", "smoke", "excerpt:hec701/DavisStormSystem.p02", C + "701/Davis/p02/F0/DavisStormSystem.p02.hdf", hec_run("Davis", "7.0.1"), "2D mesh + pipe network + pumps (9 time rows)", None),
    ("hec701/DavisStormSystem.p02.all2d", "core", "excerpt:hec701/DavisStormSystem.p02.all2d", C + "701/Davis/p02/F1_all2d/DavisStormSystem.p02.hdf", hec_run("Davis", "7.0.1"), "all optional 2D output variables", None),
    ("hec701/BaldEagleDamBrk.p18.all2d", "smoke", "excerpt:hec701/BaldEagleDamBrk.p18.all2d", C + "701/BaldEagleCrkMulti2D/p18/F1_all2d/BaldEagleDamBrk.p18.hdf", hec_run("BaldEagleCrkMulti2D (p18)", "7.0.1"), "two 2D areas, 2D-to-2D connection, all optional 2D variables", None),
    ("hec701/BaldEagleDamBrk.p03.all2d", "core", "excerpt:hec701/BaldEagleDamBrk.p03.all2d.noproptables", C + "701/BaldEagleCrkMulti2D/p03/F1_all2d/BaldEagleDamBrk.p03.hdf", hec_run("BaldEagleCrkMulti2D (p03)", "7.0.1"), "27 optional 2D datasets, 1D/2D, structures; property tables removed", None),
    ("hec701/BaldEagleDamBrk.p03.refpts", "core", "excerpt:hec701/BaldEagleDamBrk.p03.refpts.noproptables", C + "701/BaldEagleCrkMulti2D/p03/F3_refpts_lines/BaldEagleDamBrk.p03.hdf", hec_run("BaldEagleCrkMulti2D (p03) + CLB reference points/line", "7.0.1"), "reference points/lines geometry + TS; property tables removed", None),
    ("hec701/BaldEagleDamBrk.p06.infil", "core", "excerpt:hec701/BaldEagleDamBrk.p06.infil.noproptables", C + "701/BaldEagleCrkMulti2D/p06/infil_regions/BaldEagleDamBrk.p06.hdf", hec_run("BaldEagleCrkMulti2D (p06) + CLB infiltration regions", "7.0.1"),
     "gridded met precip Values (9 rows), Geometry/Infiltration regions + base overrides, infiltration results; property tables removed", None),
    ("hec701/Weise.p01", "core", "excerpt:hec701/Weise.p01", C + "701/Weise_2D/p01/sed_active_layer/Weise.p01.hdf", hec_run("Weise_2D", "7.0.1"), "SI 2D sediment, output level 6, active layer", None),
    ("hec701/EtherHollow.p01.bingham700", "core", "excerpt:hec701/EtherHollow.p01.bingham700.noproptables", C + "fixtures-20261022-ether-hollow/full_2core/bingham_ty700/EtherHollow.p01.hdf",
     {"program": "CLB recreation of HEC 'Expedited Debris Flow Tutorial'", "inputs": "USGS 3DEP 1 m lidar (public domain), USGS post-fire burn polygons, HMS design hydrograph",
      "computed_with": "HEC-RAS 7.0.1", "attribution": "Inputs: USGS; tutorial: USACE HEC; model and run: CLB Engineering Corporation", "licence": "Public domain inputs; CLB run under the corpus licence"},
     "non-Newtonian Bingham viscous/yield stress, mixture viscosity; property tables removed", None),
    # ---- CLB (Jacob Beatty) models
    ("clb/Homewood.p02", "core", "excerpt:clb/Homewood.p02", HERE + "/Homewood.p02.hdf",
     {"program": "CLB Engineering model", "credit": JB, "attribution": JB, "licence": "CLB-owned; corpus licence (used with permission)",
      "copy_used": "golden-corpus/Homewood.p02.hdf (identical to local-scratch-archive-20261022/wave3-fixtures/Homewood.p02.hdf)",
      "source_sha256_expected": "f07c62be5e82c831f564226c02e75adcd7bc2ab7919679f33c4fcfc7de5341eb"},
     "HEC-RAS 7.0 2D results (68,743 cells), reference lines; property tables removed", None),
    ("clb/CahabaRiver.g03", "smoke", "excerpt:clb/CahabaRiver.g03", F + "wave3b-fixtures/extra-CahabaRiver.g03.hdf",
     {"program": "CLB Engineering model", "credit": JB, "attribution": JB, "licence": "CLB-owned; corpus licence (used with permission)"},
     "HEC-RAS 7.0 geometry HDF (File Type 'HEC-RAS Results'), 61,955 cells; property tables removed", None),
    # ---- eBFE / RBFS results
    ("ebfe/1101001306.p01.features", "smoke", "excerpt:ebfe/1101001306.p01.features", GLAISE + "Output/1101001306.p01.hdf",
     ebfe(GLAISE_URL, "11010014_Models.zip", "Hydraulic Models/Glaise Creek-White River_1101001306.zip -> Output/1101001306.p01.hdf", GLAISE_NOTE),
     "6.3.1 writer: refinement regions, reference lines + TS, BC lines/BC TS, breaklines, summaries (mesh arrays removed)", None),
    ("rbfs/DowntownCorpusChris.p17", "core", "excerpt:rbfs/DowntownCorpusChris.p17", RBFS_TMP + "DowntownCorpusChris.p17.hdf",
     rbfs(DCC_KEY, DCC_ZIP, DCC_IN + "DowntownCorpusChris.p17.hdf"), "6.4.1 2D unsteady results (coastal Texas); property tables removed", None),
    ("rbfs/DCC_S_002PCT.PostProcessing", "core", "full", RBFS_TMP + "DCC_S_002PCT__PostProcessing.hdf",
     rbfs(DCC_KEY, DCC_ZIP, DCC_IN + "DCC_S_002PCT/PostProcessing.hdf"), "RAS Mapper stored-map PostProcessing.hdf: Results only, no root attributes", None),
    ("rbfs/DowntownCorpusChris.p50.stub", "core", "full", RBFS_TMP + "DowntownCorpusChris.p50.hdf",
     rbfs(DCC_KEY, DCC_ZIP, DCC_IN + "DowntownCorpusChris.p50.hdf"), "12.9 KB plan HDF with only a Results group and no root attributes (detection must not misclassify)", None),
    # ---- RAS Mapper layer files (detection by File Type / LC Type)
    ("layer/landcover.hec", "smoke", "full", F + "wave3b-fixtures/00-LandCover.hdf", hec_shipped("2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D/Land Classification/LandCover.hdf"), "File Type 'HEC Land Cover', LC Type LandCover, with Classification Polygons", None),
    ("layer/landcover.legacy-noattrs", "core", "full", F + "wave3b-fixtures/05-LandCover.hdf", hec_shipped("2D Unsteady Flow Hydraulics/Muncie/LandCover/LandCover.hdf"), "legacy land cover (IDs/ManningsN/Names) with no root attributes", None),
    ("layer/landcover.combined", "core", "full", F + "wave3b-fixtures/06-LandCoverCombined.hdf", hec_shipped("2D Unsteady Flow Hydraulics/Muncie/LandCover/LandCoverCombined.hdf"), "legacy layout with File Type but no LC Type", None),
    ("layer/landcover.rbfs", "core", "full", RBFS_TMP + "Land Classification__LC_Exist_CoCC_20240328.hdf", rbfs(DCC_KEY, DCC_ZIP, DCC_IN + "Land Classification/LC_Exist_CoCC_20240328.hdf"), "6.4.1-era land cover, no classification polygons", None),
    ("layer/soils.hsg.hec", "smoke", "full", F + "wave3b-fixtures/01-Hydrologic Soil Groups.hdf", hec_shipped("2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D/Soils Data/Hydrologic Soil Groups.hdf"), "File Type 'HEC Land Cover', LC Type Soils (HSG)", None),
    ("layer/soils.rbfs", "core", "full", RBFS_TMP + "Land Classification__Sand.hdf", rbfs(DCC_KEY, DCC_ZIP, DCC_IN + "Land Classification/Sand.hdf"), "LC Type Soils", None),
    ("layer/infiltration.scs.hec", "smoke", "full", F + "wave3b-fixtures/03-Infiltration.hdf", hec_shipped("2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D/Soils Data/Infiltration.hdf"), "LC Type InfiltrationSCSCurveNumber, NO File Type attribute", None),
    ("layer/infiltration.greenampt.homewood", "smoke", "full", F + "wave3b-fixtures/16-GreenAmpt_Infiltration.hdf",
     {"program": "CLB Engineering model (Homewood)", "credit": JB, "attribution": JB, "licence": "CLB-owned; corpus licence (used with permission)"},
     "File Type 'HEC Land Cover' + LC Type InfiltrationGreenAmpt, raster-parameter layout", None),
    ("layer/infiltration.deficitconstant.rbfs", "smoke", "full", RBFS_TMP + "Land Classification__Infiltration_100yr.hdf", rbfs(DCC_KEY, DCC_ZIP, DCC_IN + "Land Classification/Infiltration_100yr.hdf"),
     "LC Type InfiltrationDeficitConstantLoss, no File Type", None),
    ("layer/landcover.ebfe631", "core", "full", GLAISE + "Land Classification/LandCover.hdf", ebfe(GLAISE_URL, "11010014_Models.zip", "Hydraulic Models/Glaise Creek-White River_1101001306.zip -> Land Classification/LandCover.hdf", GLAISE_NOTE), "eBFE land cover", None),
    ("layer/soils.ebfe631", "core", "full", GLAISE + "Land Classification/Soils.hdf", ebfe(GLAISE_URL, "11010014_Models.zip", "Hydraulic Models/Glaise Creek-White River_1101001306.zip -> Land Classification/Soils.hdf", GLAISE_NOTE), "eBFE soils", None),
    ("layer/infiltration.scs.ebfe631", "core", "full", GLAISE + "Land Classification/Infiltration.hdf", ebfe(GLAISE_URL, "11010014_Models.zip", "Hydraulic Models/Glaise Creek-White River_1101001306.zip -> Land Classification/Infiltration.hdf", GLAISE_NOTE), "eBFE SCS infiltration", None),
    ("layer/sediment-materials.hec", "core", "full", F + "wave3b-fixtures/14-Sediment Materials.hdf", {**hec_shipped("2D Sediment Transport/Chippewa_2D/External Dependencies/Sediment Materials.hdf"),
                                         "stored_version_stamp": "root attrs LC Type=SedimentBedMaterial, Version=2.0, GUID; no File Type or File Version",
                                         "also_in": "Example_Projects_7_0.zip (same sha256)"},
     "LC Type SedimentBedMaterial, no File Type; used as input by the HEC-RAS 7.0.1 Chippewa p02 sediment run", None),
    ("layer/terrain.v12.etherhollow", "smoke", "full", F + "h4/sidecar/eh_terrain/Terrain.hdf",
     {"program": "CLB Ether Hollow terrain (USGS 3DEP)", "attribution": "Terrain data: USGS 3DEP; RAS Mapper terrain by CLB Engineering Corporation", "licence": "Public domain input; corpus licence"},
     "HEC-RAS 7.0.1 terrain: File Type 'HEC Terrain', Version 1.2 (HDF only; source TIFFs not shipped)", None),
    ("layer/terrain.modifications.rbfs", "smoke", "full", RBFS_TMP + "Terrain__DCC_Final.hdf", rbfs(DCC_KEY, DCC_ZIP, DCC_IN + "Terrain/DCC_Final.hdf"),
     "terrain with Modifications group, Version 1.2, NO File Type", None),
    ("layer/terrain.legacy-noattrs.hec", "core", "full", F + "wave3b-fixtures/09-Terrain.hdf", hec_shipped("2D Unsteady Flow Hydraulics/Muncie/Terrain/Terrain.hdf"), "legacy terrain with no root attributes", None),
    ("layer/terrain.withchannel.hec", "core", "full", F + "wave3b-fixtures/10-TerrainWithChannel.hdf", hec_shipped("2D Unsteady Flow Hydraulics/Muncie/Terrain/TerrainWithChannel.hdf"), "terrain with File Type 'HEC Terrain'", None),
    # ---- revision 3: HEC examples run in HEC-RAS 7.0.1 (2026-10-24) to give every family a 7.0.1 file
    *[(f"hec701r/{n}", prof, "full", R701 + d, hec_run701(proj, plan, st), cov, None) for n, prof, d, proj, plan, st, cov in [
        ("BaldEagle.p01", "core", "Balde_Eagle_Creek_p01/BaldEagle.p01.hdf", "1D Unsteady Flow Hydraulics/Balde Eagle Creek", "01", [],
         "1D unsteady XS time series, bridges + inline (replaces hec66/BaldEagle.p01)"),
        ("beaver.p03", "core", "Bridge_Hydraulics_p03/beaver.p03.hdf", "1D Unsteady Flow Hydraulics/Bridge Hydraulics", "03", [], "1D unsteady bridge series + bridge property tables"),
        ("beaver.g01", "core", "Bridge_Hydraulics_p03/beaver.g01.hdf", "1D Unsteady Flow Hydraulics/Bridge Hydraulics", "03", [], "bridge geometry (7.0.1 writer)"),
        ("Beav_Culvert.p01", "core", "Culvert_Hydraulics_p01/Beav_Culvert.p01.hdf", "1D Unsteady Flow Hydraulics/Culvert Hydraulics", "01", [], "1D unsteady culvert groups + barrels"),
        ("Beav_Culvert.g01", "core", "Culvert_Hydraulics_p01/Beav_Culvert.g01.hdf", "1D Unsteady Flow Hydraulics/Culvert Hydraulics", "01", [], "culvert geometry (7.0.1 writer)"),
        ("OrleansEx.p02", "core", "Example_23_-_Urban_Modeling_p02/OrleansEx.p02.hdf", "Applications Guide/Example 23 - Urban Modeling", "02", [], "urban 1D unsteady, storage areas, pumps"),
        ("OrleansEx.g04", "core", "Example_23_-_Urban_Modeling_p02/OrleansEx.g04.hdf", "Applications Guide/Example 23 - Urban Modeling", "02", [], "urban geometry (7.0.1 writer)"),
        ("FLODENCR.p04", "core", "Example_6_-_Floodway_Determination_p04/FLODENCR.p04.hdf", "Applications Guide/Example 6 - Floodway Determination", "04", [], "steady floodway encroachments"),
        ("FLODENCR.g01", "core", "Example_6_-_Floodway_Determination_p04/FLODENCR.g01.hdf", "Applications Guide/Example 6 - Floodway Determination", "04", [], "encroachment geometry (7.0.1 writer)"),
        ("Inline_3Gates.p01", "core", "Inline_Structure_with_Gated_Spillways_p01/Inline_3Gates.p01.hdf", "1D Unsteady Flow Hydraulics/Inline Structure with Gated Spillways", "01", [], "gated inline structure series"),
        ("Inline_3Gates.g01", "core", "Inline_Structure_with_Gated_Spillways_p01/Inline_3Gates.g01.hdf", "1D Unsteady Flow Hydraulics/Inline Structure with Gated Spillways", "01", [], "gate groups geometry (7.0.1 writer)"),
        ("JunctionHydraulics.p01", "core", "JunctionHydraulics_p01/JunctionHydraulics.p01.hdf", "1D Unsteady Flow Hydraulics/JunctionHydraulics", "01", [], "unsteady junctions"),
        ("JunctionHydraulics.g01", "core", "JunctionHydraulics_p01/JunctionHydraulics.g01.hdf", "1D Unsteady Flow Hydraulics/JunctionHydraulics", "01", [], "junction geometry (7.0.1 writer)"),
        ("3Reach_with_Lat.p01", "core", "Lateral_Structure_connected_to_a_River_Reach_p01/3Reach_with_Lat.p01.hdf", "1D Unsteady Flow Hydraulics/Lateral Structure connected to a River Reach", "01", [], "lateral structure series"),
        ("3Reach_with_Lat.g01", "core", "Lateral_Structure_connected_to_a_River_Reach_p01/3Reach_with_Lat.g01.hdf", "1D Unsteady Flow Hydraulics/Lateral Structure connected to a River Reach", "01", [], "lateral structure geometry (7.0.1 writer)"),
        ("Muncie.p03", "smoke", "Muncie_p03_map1HOUR/Muncie.p03.hdf", "2D Unsteady Flow Hydraulics/Muncie", "03", ["Mapping Interval=1HOUR"], "1D/2D unsteady results, native 7.0.1 2D series, breaklines"),
        ("Muncie.g02", "core", "Muncie_p03_map1HOUR/Muncie.g02.hdf", "2D Unsteady Flow Hydraulics/Muncie", "03", ["Mapping Interval=1HOUR"], "1D/2D geometry (7.0.1 writer)"),
        ("Baxter.p01", "core", "RAS_Model_p01/Baxter.p01.hdf", "1D Steady Flow Hydraulics/Baxter RAS Mapper/RAS Model", "01", [], "steady junctions/storage"),
        ("Baxter.g02", "core", "RAS_Model_p01/Baxter.g02.hdf", "1D Steady Flow Hydraulics/Baxter RAS Mapper/RAS Model", "01", [], "junction geometry (7.0.1 writer)"),
        ("MBex.p01", "core", "Simple_Sediment_Transport_Example_p01/MBex.p01.hdf", "1D Sediment Transport/Simple Sediment Transport Example", "01", [], "1D sediment results"),
        ("MBex.g02", "core", "Simple_Sediment_Transport_Example_p01/MBex.g02.hdf", "1D Sediment Transport/Simple Sediment Transport Example", "01", [], "1D sediment geometry (7.0.1 writer)"),
        ("Beaver_LS_SAConn.p01", "core", "Storage_Area_Hydraulic_Connection_p01/Beaver_LS_SAConn.p01.hdf", "1D Unsteady Flow Hydraulics/Storage Area Hydraulic Connection", "01", [], "storage areas + SA/SA hydraulic connection"),
        ("Beaver_LS_SAConn.g01", "core", "Storage_Area_Hydraulic_Connection_p01/Beaver_LS_SAConn.g01.hdf", "1D Unsteady Flow Hydraulics/Storage Area Hydraulic Connection", "01", [], "storage-area geometry (7.0.1 writer)"),
        ("BaldEagleDamBrk.p19", "core", "BaldEagleCrkMulti2D_p19_map1HOUR/BaldEagleDamBrk.p19.hdf", "2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D", "19", ["Mapping Interval=1HOUR"],
         "SA-to-2D connection with dam breach, native 7.0.1 property tables"),
        ("Weise.p01.si-hydro", "smoke", "Weise_2D_p01_ovr/Weise.p01.hdf", "2D Sediment Transport/Weise_2D", "01", ["Run Sediment= 0", "Mapping Interval=5MIN"],
         "SI-unit 2D hydrodynamics without sediment results"),
    ]],
    ("hec701r/Muncie.p04", "extended", "full", R701 + "Muncie_p04_map1HOUR/Muncie.p04.hdf",
     hec_run701("2D Unsteady Flow Hydraulics/Muncie", "04", ["Mapping Interval=1HOUR"]), "2D with n-value regions (Muncie p03 covers 1D/2D in core)", None),
    ("hec701r/BaldEagleDamBrk.p15", "core", "excerpt:hec701/BaldEagleDamBrk.p15", R701 + "BaldEagleCrkMulti2D_p15_map1HOUR/BaldEagleDamBrk.p15.hdf",
     hec_run701("2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D", "15", ["Mapping Interval=1HOUR"]),
     "1D/2D refined grid: lateral structures, bridges, inline, breach, storage areas; native 7.0.1 property tables kept (9 time rows)", None),
    ("ext/BaldEagleDamBrk.p15.full", "extended", "full", R701 + "BaldEagleCrkMulti2D_p15_map1HOUR/BaldEagleDamBrk.p15.hdf",
     hec_run701("2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D", "15", ["Mapping Interval=1HOUR"]), "full time axis of p15", None),
    # ---- revision 3: RAS Mapper layers written by HEC-RAS 7.0.1
    ("layer701/landcover", "smoke", "full", L701 + "LandCover701.hdf", LAYER701_PROV("RasMap.add_landcover_layer"), "File Type 'HEC Land Cover', LC Type LandCover, Version 2.0, Percent Impervious", None),
    ("layer701/landcover.tif", "smoke", "full", L701 + "LandCover701.tif", LAYER701_PROV("RasMap.add_landcover_layer"), "companion GeoTIFF of layer701/landcover", None),
    ("layer701/soils", "smoke", "full", L701 + "Soils701.hdf", LAYER701_PROV("_landcover_native.create_soils on a clipped HSG raster"), "File Type 'HEC Land Cover', LC Type Soils (HSG)", None),
    ("layer701/soils.tif", "smoke", "full", L701 + "Soils701.tif", LAYER701_PROV("_landcover_native.create_soils"), "companion GeoTIFF of layer701/soils", None),
    ("layer701/infiltration.scs", "smoke", "full", L701 + "Infiltration701_scs_curve_number.hdf", LAYER701_PROV("RasMap.add_infiltration_layer('scs_curve_number')"),
     "LC Type InfiltrationSCSCurveNumber, NO File Type attribute (a 7.0.1 quirk)", None),
    ("layer701/infiltration.greenampt", "smoke", "full", L701 + "Infiltration701_green_ampt.hdf", LAYER701_PROV("RasMap.add_infiltration_layer('green_ampt')"),
     "LC Type InfiltrationGreenAmpt, NO File Type attribute (a 7.0.1 quirk)", None),
    ("layer701/infiltration.deficitconstant", "smoke", "full", L701 + "Infiltration701_deficit_constant.hdf", LAYER701_PROV("RasMap.add_infiltration_layer('deficit_constant')"),
     "LC Type InfiltrationDeficitConstantLoss, NO File Type attribute (a 7.0.1 quirk)", None),
    ("layer701/terrain", "smoke", "full", T701 + "Terrain701.hdf", TERRAIN701_PROV, "File Type 'HEC Terrain', Version 1.2, 7.0.1-written, with its GeoTIFF + VRT", None),
    ("layer701/terrain.tif", "smoke", "full", T701 + "Terrain701.dtm_20ft_clip.tif", TERRAIN701_PROV, "terrain GeoTIFF tile (300 x 300 px, 20 ft) for elevation sampling", None),
    ("layer701/terrain.vrt", "smoke", "full", T701 + "Terrain701.vrt", TERRAIN701_PROV, "terrain VRT written by RasProcess", None),
    # ---- revision 3: 7.0.1 RAS Mapper stored map (results raster for terrio)
    ("storedmap701/Muncie.p03.wse_max.tif", "core", "full", SM701 + "WSE (Max).Terrain.muncie_clip.tif", STOREDMAP701_PROV,
     "7.0.1 stored-map GeoTIFF: WSE (Max), sloping render mode, on the Muncie terrain grid", None),
    ("storedmap701/Muncie.p03.wse_max.vrt", "core", "full", SM701 + "WSE (Max).vrt", STOREDMAP701_PROV, "VRT of the stored map", None),
    # ---- revision 4: HEC-shipped bed-material layer, used as input by the 7.0.1 Weise sediment run
    ("layer/sediment-bed-material.weise", "core", "full", Z("2D Sediment Transport/Weise_2D/Land Classification/Sediment Bed Material.hdf"),
     {**hec_shipped("2D Sediment Transport/Weise_2D/Land Classification/Sediment Bed Material.hdf"),
       "stored_version_stamp": "root attrs LC Type=SedimentBedMaterial, Version=2.0, GUID; no File Type or File Version",
       "also_in": "Example_Projects_7_0.zip (same sha256)"},
     "LC Type SedimentBedMaterial, Version 2.0, no File Type; used as input by the HEC-RAS 7.0.1 Weise sediment run", None),
    # ---- revision 3: synthetic fixtures (CC0)
    ("synthetic/albers", "core", "full", S701 + "synthetic_albers.DavisStormSystem.g02.hdf",
     SYN_PROV("byte copy of hec701/DavisStormSystem.g02 with only the root 'Projection' attribute replaced by NAD83 / CONUS Albers (ESRI WKT); coordinates untouched"),
     "Albers CRS metadata handling (no public 7.0.1 model in Albers found)", None),
    ("synthetic/infiltration-parameters", "core", "full", S701 + "synthetic_infiltration_parameters.hdf",
     SYN_PROV("root 'Infiltration Parameters' table as read by HdfInfiltration.get_infiltration_parameters; not written by any HEC-RAS/RAS Mapper output examined"),
     "code-shaped only: unverified against real HEC output", None),
    ("synthetic/legacy-ts-structures", "legacy", "full", S701 + "synthetic_legacy_ts_structures.h5",
     SYN_PROV("legacy generic '.../Unsteady Time Series/Structures' layout read by HdfStruc1D's fallback; written by no HEC-RAS version observed"),
     "HdfStruc1D fallback + refusal paths", None),
    # ---- revision 3: native HEC-RAS 5.0.7 runs (legacy only; 5.0.7 was already installed)
    ("hec507/Muncie.p03", "legacy", "full", R507 + "Muncie_p03_map1HOUR/Muncie.p03.hdf", HEC507_PROV("Muncie", "03"),
     "native 5.0.7 1D/2D results; root File Type 'HEC-RAS Geometry' although it holds Results", "native writer 5.0.7 (2D results)"),
    ("hec507/BaldEagleDamBrk.p18", "legacy", "full", R507 + "BaldEagleCrkMulti2D_p18_map1HOUR/BaldEagleDamBrk.p18.hdf", HEC507_PROV("BaldEagleCrkMulti2D", "18"),
     "native 5.0.7 2D-to-2D results with native 5.0.7 face/cell tables", None),
    # ---- v1.0.1: eBFE San Marcos 1D BLE model Stream248, computed in HEC-RAS 7.0.1
    *[(i, "smoke", "full", S248 + rel, STREAM248_PROV(plan), cov, None) for i, rel, plan, cov in [
        ("ebfe/Stream248.g01", "Stream248_p02/Stream248.g01.hdf", "02",
         "eBFE 1D geometry (14 cross sections) written by HEC-RAS 7.0.1, with XS property tables"),
        ("ebfe/Stream248.p01", "Stream248_p01/Stream248.p01.hdf", "01",
         "eBFE delivered 1D steady plan 'Multiple Run' (7 profiles) computed unchanged in HEC-RAS 7.0.1"),
        ("clb/Stream248.p02", "Stream248_p02/Stream248.p02.hdf", "02",
         "CLB-added 1D unsteady plan on the eBFE geometry (constant 450 cfs, 24 h) computed in HEC-RAS 7.0.1"),
    ]],
    # ---- revision 4: Weise SI 2D with sediment ON in 7.0.1 (native sediment results; full file)
    ("hec701r/Weise.p01.sed", "smoke", "full", R701 + "Weise_2D_p01_ovr_sed/Weise.p01.hdf",
     hec_run701("2D Sediment Transport/Weise_2D", "01", ["Mapping Interval=5MIN"]),
     "SI 2D sediment results, native 7.0.1 (sediment ON as shipped; output level 3)", None),
    # ---- 2026-10-25: native 7.0.1 reference lines + reference points (engine #12 qualification)
    ("hec701r/Weise.p01.reflines", "smoke", "full", RL701 + "Weise_p01/Weise.p01.hdf",
     REFLINE701_PROV("2D Sediment Transport/Weise_2D", "01", ["Run Sediment= 0", "Mapping Interval=5MIN"]),
     "SI flume, one 2D area: 5 reference lines (transverse, diagonal, 3-point longitudinal) + 5 reference points; "
     "block and per-area (2D Flow Areas/<area>/) reference series, Base + DSS Hydrograph blocks", None),
    ("hec701r/BaldEagleDamBrk.p18.reflines", "core", "full", RL701 + "BaldEagleDamBrk_p18/BaldEagleDamBrk.p18.hdf",
     REFLINE701_PROV("2D Unsteady Flow Hydraulics/BaldEagleCrkMulti2D", "18", ["Mapping Interval=1HOUR"]),
     "two 2D areas (BaldEagleCr, Upper 2D Area): 8 reference lines (4 breakline-derived transverse) + 5 reference points "
     "in both areas; a name repeated across areas is renamed by 7.0.1 (RL_Shared -> 'RL_Shared 1')", None),
    # ---- revision 4: eBFE refinement regions re-preprocessed in 7.0.1
    *EBFE_RR701,
    # ---- revision 4: Homewood layers recovered from H:/Jacob (Jacob Beatty's folder); HEC-RAS 7.0 project
    ("layer/landcover.homewood", "legacy", "full", JH + "Land Classification/LandCover.hdf", HOMEWOOD_LAYER_PROV("LandCover.hdf"),
     "File Type 'HEC Land Cover', LC Type LandCover, Version 2.0, GUID + Projection attrs (Homewood)", None),
    ("layer/landcover.homewood.tif", "legacy", "full", JH + "Land Classification/LandCover.tif", HOMEWOOD_LAYER_PROV("LandCover.tif"),
     "companion GeoTIFF of layer/landcover.homewood", None),
    ("layer/infiltration.greenampt.buffered.homewood", "legacy", "full", JH + "Land Classification/GreenAmpt_Buffered.hdf",
     HOMEWOOD_LAYER_PROV("GreenAmpt_Buffered.hdf"),
     "LC Type InfiltrationGreenAmpt, raster-parameter layout (Ks, suction, porosity rasters), buffered variant", None),
    ("layer/infiltration.greenampt.buffered.homewood.tif", "legacy", "full", JH + "Land Classification/GreenAmpt_Buffered.tif",
     HOMEWOOD_LAYER_PROV("GreenAmpt_Buffered.tif"), "companion GeoTIFF of the buffered Green-Ampt layer", None),
    # ---- extended (nightly)
    ("ext/BaldEagleDamBrk.p03.warmup_restart", "extended", "excerpt:hec701/BaldEagleDamBrk.p03.warmup_restart", C + "701/BaldEagleCrkMulti2D/p03/F2F4_warmup_restart/BaldEagleDamBrk.p03.hdf", hec_run("BaldEagleCrkMulti2D (p03)", "7.0.1"), "warmup + restart output", None),
    ("ext/BaldEagleDamBrk.p03.baseline", "extended", "excerpt:hec701/BaldEagleDamBrk.p03", C + "701/BaldEagleCrkMulti2D/p03/F0/BaldEagleDamBrk.p03.hdf", hec_run("BaldEagleCrkMulti2D (p03)", "7.0.1"), "default-output baseline", None),
    ("ext/BaldEagleDamBrk.p06.infil.with-proptables", "extended", "excerpt:hec701/BaldEagleDamBrk.p06.infil", C + "701/BaldEagleCrkMulti2D/p06/infil_regions/BaldEagleDamBrk.p06.hdf", hec_run("BaldEagleCrkMulti2D (p06)", "7.0.1"), "same with property tables", None),
    ("ext/BaldEagleDamBrk.p07.with-proptables", "extended", "excerpt:hec66/BaldEagleDamBrk.p07", F + "structures-fixtures/BaldEagleDamBrk.p07.hdf", hec_run("BaldEagleCrkMulti2D (p07)", "6.6"), "same with property tables", None),
    ("ext/BaldEagleDamBrk.p03.refpts.66", "extended", "excerpt:hec66/BaldEagleDamBrk.p03.refpts", C + "66/BaldEagleCrkMulti2D/p03/F3_refpts_lines/BaldEagleDamBrk.p03.hdf", hec_run("BaldEagleCrkMulti2D (p03)", "6.6"), "6.6 reference TS", None),
    ("ext/Canal.p01.701", "extended", "full", C + "701/Rule_Operations/p01/F0/Canal.p01.hdf", hec_run("Rule Operations", "7.0.1"), "multi-inline rule operations", None),
    ("ext/ManningsCalibration.p02.701", "extended", "full", C + "701/Example_24_-_Mannings-n-Calibration/p02/F0/Manning'snCalibra.p02.hdf", hec_run("Example 24", "7.0.1"), "2 inline structures, 28 laterals", None),
    ("ext/1101001306.p01.noproptables", "extended", "excerpt:ebfe/1101001306.p01", GLAISE + "Output/1101001306.p01.hdf", ebfe(GLAISE_URL, "11010014_Models.zip", "Hydraulic Models/Glaise Creek-White River_1101001306.zip -> Output/1101001306.p01.hdf", GLAISE_NOTE), "6.3.1 587k-cell mesh with series", None),
    ("ext/Homewood.p02.full", "extended", "full", HERE + "/Homewood.p02.hdf", {"program": "CLB Engineering model", "credit": JB, "attribution": JB, "licence": "CLB-owned; corpus licence (used with permission)"}, "full native 7.0 incl. property tables", None),
    ("ext/Homewood.g13.full", "extended", "full", F + "wave3b-fixtures/extra-Homewood.g13.hdf", {"program": "CLB Engineering model", "credit": JB, "attribution": JB, "licence": "CLB-owned; corpus licence (used with permission)"}, "7.0 geometry of p02", None),
    ("ext/CahabaRiver.g03.full", "extended", "full", F + "wave3b-fixtures/extra-CahabaRiver.g03.hdf", {"program": "CLB Engineering model", "credit": JB, "attribution": JB, "licence": "CLB-owned; corpus licence (used with permission)"}, "full geometry incl. property tables", None),
    ("ext/DowntownCorpusChris.p17.full", "extended", "full", RBFS_TMP + "DowntownCorpusChris.p17.hdf", rbfs(DCC_KEY, DCC_ZIP, DCC_IN + "DowntownCorpusChris.p17.hdf"), "full native 6.4.1 results", None),
    ("ext/EtherHollow.p01.bingham2500", "extended", "full", C + "fixtures-20261022-ether-hollow/full_2core/bingham_ty2500/EtherHollow.p01.hdf", {"program": "CLB Ether Hollow", "licence": "Public domain inputs; corpus licence"}, "second Bingham yield stress", None),
    ("ext/EtherHollow.p01.clear", "extended", "full", C + "fixtures-20261022-ether-hollow/full_2core/clear/EtherHollow.p01.hdf", {"program": "CLB Ether Hollow", "licence": "Public domain inputs; corpus licence"}, "clear-water control", None),
    ("lwi/LC_LowerCalcasieu.p05", "external", "full", C + "fixtures-20261022-lower-calcasieu/inputs/LC_LowerCalcasieu.p05.hdf",
     {"program": "Louisiana Watershed Initiative", "download_location": "s3://lwi-model-data/endmc-managed/model_application/6855fd1f829315e6f26d6001/LC_LowerCalcasieu.p05.hdf",
      "attribution": "Louisiana Watershed Initiative (LWI) Model Data, Louisiana Watershed Council", "licence": "CC BY 4.0 (AWS Registry of Open Data)",
      "verification": "size match + 5 sampled 1 MiB ranges identical to CLB copy"}, "6.4.1 132k-cell coastal 2D, refinement regions, tidal BCs, met precip", None),
]

DROPPED = [
    ("hec701/DavisStormSystem.p02 full (21.3 MB) -> extended", "the 9-row excerpt is in smoke; native 7.0.1 results come from Pumps.p01 and native 2D series layout from hec70 p18"),
    ("property-table families in BaldEagle p03/p06/p07, Ether Hollow, Homewood, Cahaba, RBFS p17 excerpts", "kept full in native anchors (DowntownCorpusChris.g12, hec70 p18, HEC-shipped g13/Muncie/Chippewa); variants with tables stay in extended"),
    ("hec701/BaldEagleDamBrk.g09.refpts / .66 (15.4 / 11.7 MB)", "geometry already inside the p03.refpts excerpt"),
    ("hec701/BaldEagleDamBrk.g09.infil (15.4 MB)", "Geometry/Infiltration regions are inside the p06 infil excerpt"),
    ("hec66/BaldEagleDamBrk.p03.refpts excerpt (13.8 MB) -> extended", "7.0.1 excerpt and AustinOyster.p01 cover reference series in core"),
    ("hec701/BaldEagleDamBrk.p03 F0 excerpt (17.4 MB) -> extended", "all2d excerpt is a superset of the default outputs"),
    ("hec66/Pumps.g01/.p01, hec66/DavisStormSystem.p02, hec66/Weise.p01", "7.0.1 versions cover the families; 6.6 container coverage comes from AustinOyster.p01 and the hec66 1D plans"),
    ("hec701/Chippewa_2D.g01 (0.42 MB)", "HEC-shipped 6.4 Chippewa g01 kept instead"),
    ("hec-asis/sidecar.Terrain50 (4.9 MB)", "legacy no-attribute terrain covered by Muncie Terrain.hdf (0.85 MB)"),
    ("hec-asis/sidecar.Infiltration_GA_reg (15-*)", "origin not in the HEC 6.6 zip; Green-Ampt covered by Homewood layer"),
    ("hec701/sidecar.be701oc.* (LandCover/HSG/Infiltration)", "same layouts as the HEC-shipped layers"),
    ("hec701/BaldEagle.g01 .66, hec66/BaldEagle.g01", "hec701 BaldEagle.g01 kept"),
    ("7.0-DavisStormSystem.g02 (HEC-RAS 6.7 Beta 5)", "origin unverified; not in the 6.6 zip"),
    ("hec701/BaldEagleDamBrk.g08 (15.96 MB, 7.0.1)", "geometry is inside the hec701r/BaldEagleDamBrk.p15 excerpt"),
    ("hec507 Muncie p01/p04, Muncie/BaldEagle g01/g02/g04/g11 (5.0.7 runs)", "legacy needs one native 5.0.7 2D plan pair only; p03 and p18 kept"),
    ("6.3.1 regeneration, 7.0 regeneration, version-specific property-table gaps", "not pursued: older versions are best effort (policy 2026-10-24)"),
    ("RBFS Reese Bayou / East Fork San Jacinto AAFMR (HEC-RAS 6.6)", "public TDIS entries found, but under the 7.0.1 policy they would only add 6.6 files to legacy, which already has 6.6 coverage"),
    ("Local LC_LowerCalcasieu copy", "replaced by the identical public LWI object (external)"),
    ("Duplicates/scratch (c05 Davis copy, Ether Hollow result_* copies, diagnostics, *.tmp.hdf, *.backup.hdf, sediment-2d-Weise.u01 = Davis u01)", "duplicate or scratch"),
]


def sha_of(path):
    if path.startswith("zip66!"):
        m = path[6:]
        key = "zip66!" + m
        if key not in CACHE:
            b = zipfile.ZipFile(ZIP66).read(m)
            CACHE[key] = [len(b), hashlib.sha256(b).hexdigest()]
        return CACHE[key]
    if path in INV:
        return [INV[path]["bytes"], INV[path]["sha256"]]
    if path in KNOWN_SHA:
        return [os.path.getsize(path), KNOWN_SHA[path]]
    if path not in CACHE:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for blk in iter(lambda: f.read(1 << 22), b""):
                h.update(blk)
        CACHE[path] = [os.path.getsize(path), h.hexdigest()]
    return CACHE[path]


def is_hdf(path):
    return path.lower().endswith((".hdf", ".h5"))


# Writer of files that carry no root "File Version" (layers, terrains, synthetic).
WRITER = {
    "layer/landcover.hec": "6.x (HEC 6.6 example zip)", "layer/landcover.legacy-noattrs": "pre-6 (HEC 6.6 example zip)",
    "layer/landcover.combined": "pre-6 (HEC 6.6 example zip)", "layer/soils.hsg.hec": "6.x (HEC 6.6 example zip)",
    "layer/infiltration.scs.hec": "6.x (HEC 6.6 example zip)", "layer/sediment-materials.hec": "6.x (HEC 6.6 example zip)",
    "layer/sediment-bed-material.weise": "6.x (HEC 6.6 example zip)",
    "layer/terrain.legacy-noattrs.hec": "pre-6 (HEC 6.6 example zip)", "layer/terrain.withchannel.hec": "6.x (HEC 6.6 example zip)",
    "layer/landcover.rbfs": "6.4.1 (RBFS)", "layer/soils.rbfs": "6.4.1 (RBFS)", "layer/infiltration.deficitconstant.rbfs": "6.4.1 (RBFS)",
    "layer/terrain.modifications.rbfs": "6.4.1 (RBFS)", "rbfs/DCC_S_002PCT.PostProcessing": "6.4.1 (RBFS)",
    "rbfs/DowntownCorpusChris.p50.stub": "6.4.1 (RBFS)",
    "layer/landcover.ebfe631": "6.3.1 (eBFE)", "layer/soils.ebfe631": "6.3.1 (eBFE)", "layer/infiltration.scs.ebfe631": "6.3.1 (eBFE)",
    "layer/infiltration.greenampt.homewood": "7.0 (Homewood)",

    "layer/landcover.homewood": "7.0 (Homewood)", "layer/landcover.homewood.tif": "7.0 (Homewood)",
    "layer/infiltration.greenampt.buffered.homewood": "7.0 (Homewood)",
    "layer/infiltration.greenampt.buffered.homewood.tif": "7.0 (Homewood)",
    "layer/terrain.v12.etherhollow": "7.0.1 (CLB Ether Hollow terrain, RasProcess 7.0.1)",
}
WRITER.update({i: "7.0.1 (RasMapperLib / RasProcess)" for i in (
    "layer701/landcover", "layer701/landcover.tif", "layer701/soils", "layer701/soils.tif", "layer701/infiltration.scs",
    "layer701/infiltration.greenampt", "layer701/infiltration.deficitconstant", "layer701/terrain", "layer701/terrain.tif",
    "layer701/terrain.vrt", "storedmap701/Muncie.p03.wse_max.tif", "storedmap701/Muncie.p03.wse_max.vrt")})
WRITER.update({i: "synthetic" for i in ("synthetic/albers", "synthetic/infiltration-parameters", "synthetic/legacy-ts-structures")})
COMPANION_OF = {"layer/landcover.homewood.tif": "layer/landcover.homewood",
                "layer/infiltration.greenampt.buffered.homewood.tif": "layer/infiltration.greenampt.buffered.homewood",
                "layer701/landcover.tif": "layer701/landcover", "layer701/soils.tif": "layer701/soils",
                "layer701/terrain.tif": "layer701/terrain", "layer701/terrain.vrt": "layer701/terrain"}


def writer_of(e):
    if e["id"] in WRITER:
        return WRITER[e["id"]]
    v = (e.get("hec_ras_version") or "").replace("HEC-RAS ", "")
    return v.split(" ")[0] if v else "unknown"


def is_current(writer):
    """7.0.1 fixture: written by 7.0.1, synthetic, or an input layer used as input by a HEC-RAS 7.0.1 compute_plan run (see CONSUMED_BY_701)."""
    return writer.startswith(CURRENT) or writer == "synthetic" or writer == "used as input by a HEC-RAS 7.0.1 compute_plan run"


# Input layers (land cover, soils, infiltration, sediment) qualify for core when a recorded 7.0.1
# run consumed them successfully. Verified at build time: the run's receipt says success, the run
# copy's rasmap references the layer, and the run copy's file has the entry's source SHA-256.
R701_RECEIPT = "D:/CLB-Dev/ras701-corpus/runs/run_7.0.1_results.json"
INPUT_LC_TYPES = ("LandCover", "Soils", "SedimentBedMaterial")  # plus Infiltration*
CONSUMED_BY_701 = {
    "layer/sediment-bed-material.weise": ("Weise_2D.p01.ovr.sed", "Weise_2D_p01_ovr_sed",
                                          "Land Classification/Sediment Bed Material.hdf"),
    "layer/sediment-materials.hec": ("Chippewa_2D.p02.ovr.sed", "Chippewa_2D_p02_ovr_sed",
                                     "External Dependencies/Sediment Materials.hdf"),
}


def consumed_by_701(e):
    """Return the consumption record for an input layer, after verifying it, or None."""
    if e["id"] not in CONSUMED_BY_701:
        return None
    key, folder, rel = CONSUMED_BY_701[e["id"]]
    lc = e.get("lc_type") or ""
    assert lc in INPUT_LC_TYPES or lc.startswith("Infiltration"), (e["id"], lc)
    rec = json.load(open(R701_RECEIPT))[key]
    assert rec["success"], key
    run_dir = os.path.join("D:/CLB-Dev/ras701-corpus/runs", folder)
    rasmap = [f for f in os.listdir(run_dir) if f.endswith(".rasmap")][0]
    assert rel.replace("/", "\\") in open(os.path.join(run_dir, rasmap), encoding="latin-1").read(), (e["id"], rel)
    h = hashlib.sha256(open(os.path.join(run_dir, rel), "rb").read()).hexdigest()
    assert h == e["source_sha256"], (e["id"], h)
    return {"run": key, "receipt": R701_RECEIPT, "run_copy": run_dir.replace("\\", "/") + "/" + rel,
             "plan_settings": rec["plan_settings"], "result": rec["result"],
             "bytes_unchanged_by_run": True, "sha256_after_run": h}


# Older-version files under the legacy file cap that still go to archive, to keep legacy
# <= 100 MB with headroom: their families are covered in
# core by 7.0.1 files and their writer version keeps another legacy anchor.
ARCHIVE_FORCE = {
    "ext/BaldEagleDamBrk.p03.refpts.66": "6.6 reference series also in clb/AustinOyster.p01 (legacy) and 7.0.1 p03.refpts (core)",
    "hec66/OrleansEx.p02": "7.0.1 hec701r/OrleansEx.p02 in core; 6.6 container anchored by clb/AustinOyster.p01",
    "hec66/BaldEagle.p01": "7.0.1 hec701r/BaldEagle.p01 in core",
    "hec66/beaver.p03": "7.0.1 hec701r/beaver.p03 in core",
    "hec66/BaldEagleDamBrk.p07": "SA/2D connection + breach covered by 7.0.1 hec701r/BaldEagleDamBrk.p19 in core",
    "rbfs/DowntownCorpusChris.p17": "6.4.1 anchored by rbfs/DowntownCorpusChris.g12 (legacy)",
    "clb/Homewood.p02": "7.0 anchored by hec70/BaldEagleDamBrk.p18.full; clb/CahabaRiver.g03 keeps the Beatty models in legacy",
}


def assign_profile(e, declared):
    """7.0.1 policy: only current-writer and synthetic files stay in smoke/core/extended."""
    w = e.get("writer") or writer_of(e)
    if e["id"] in ARCHIVE_FORCE:
        return "archive"
    if declared in ("smoke", "core", "extended") and not is_current(w):
        return "legacy" if e["published_bytes"] <= LEGACY_FILE else "archive"
    return declared


def attrs_of(path):
    import h5py
    import io
    if not is_hdf(path):
        return {"file_type": None, "hec_ras_version": None, "lc_type": None, "units": None, "layer_version": None,
                "top_groups": [], "format": os.path.splitext(path)[1].lstrip(".").lower()}
    if path.startswith("zip66!"):
        f = h5py.File(io.BytesIO(zipfile.ZipFile(ZIP66).read(path[6:])), "r")
    else:
        f = h5py.File(path, "r")
    with f:
        g = lambda k: (f.attrs[k].decode("latin-1") if isinstance(f.attrs[k], bytes) else str(f.attrs[k])) if k in f.attrs else None
        return {"file_type": g("File Type"), "hec_ras_version": g("File Version"), "lc_type": g("LC Type"),
                "units": g("Units System"), "layer_version": g("Version"), "top_groups": sorted(f.keys())}


def expected_kind(e):
    """Human-reviewed detection truth (rules below were checked against every entry)."""
    top, lc, ft = set(e["top_groups"]), e["lc_type"], e["file_type"]
    if e.get("format") in ("tif", "vrt"):
        return f"companion-{e['format']}"
    if "Terrain" in top:
        return "terrain"
    if lc:
        return {"LandCover": "land-cover", "Soils": "soils", "SedimentBedMaterial": "sediment-material"}.get(
            lc, "infiltration" if lc.startswith("Infiltration") else "layer-other")
    if {"IDs", "ManningsN", "Names"} <= top:
        return "land-cover-legacy"
    if "Plan Data" in top and "Results" in top:
        return "plan-results"
    if "Plan Data" in top:
        return "plan-no-results"
    if top == {"Geometry"}:
        return "geometry"
    if top == {"Results"}:
        return "stored-map-results" if "PostProcessing" in e["local_source"] else "results-fragment"
    return "unknown"


def build():
    entries = []
    for i, prof, mode, path, prov, cov, native in E:
        nbytes, sha = sha_of(path)
        e = {"id": i, "declared_profile": prof, "mode": "full" if mode == "full" else "excerpt", "local_source": path,
             "source_bytes": nbytes, "source_sha256": sha, "provenance": prov, "coverage": cov,
             **attrs_of(path)}
        if native:
            e["low_level_native"] = native
        k = expected_kind(e)
        e["detection"] = {"expected_kind": k,
                          "file_type_mismatch": bool((k == "plan-results" and e["file_type"] == "HEC-RAS Geometry")
                                                     or (k == "geometry" and e["file_type"] == "HEC-RAS Results")),
                          "has_file_type_attr": e["file_type"] is not None}
        if mode.startswith("excerpt:"):
            m = EXM[mode.split(":", 1)[1]]
            assert m["source_sha256"] == sha, i
            assert m["verify"] == "OK", i
            e.update(excerpt_recipe=mode.split(":", 1)[1], excerpt_args=m["args"],
                     published_bytes=m["excerpt_bytes"], excerpt_sha256_measured=m["excerpt_sha256"])
        else:
            e["published_bytes"] = nbytes
        e["writer"] = writer_of(e)
        used = consumed_by_701(e)
        if used:
            e["stored_writer"] = e["writer"]
            e["writer"] = "used as input by a HEC-RAS 7.0.1 compute_plan run"
            e["used_by_701_run"] = used
        e["profile"] = assign_profile(e, prof)
        e["profiles"] = {"smoke": ["smoke", "core"], "core": ["core"]}.get(e["profile"], [e["profile"]])
        if i in COMPANION_OF:
            e["companion_of"] = COMPANION_OF[i]
        e["features"] = feature_census(path, ZIP66, e.get("excerpt_args")) if is_hdf(path) else []
        entries.append(e)
    json.dump(CACHE, open(CACHE_P, "w"), indent=1)
    return entries


# ---------------------------------------------------------------- property tables
# Readers per family: map_property_table_readers.py on ras-commander 0.108.0
# (D:/CLB-Dev/release-020/rc-rel, commit 836dde1fc) plus tests/rust_route_1/_cases.py.
PT_READERS = {
    "face_area_elevation": [
        "HdfMesh.get_mesh_face_property_tables",
        "HdfMesh.get_mesh_face_hydraulic_properties_at_stage (rust_route_1 _cases.py face interpolation)",
        "HdfLandCover.audit_final_mannings_n", "RasBreakout2D._read_boundary_face_flow",
        "RasProcess._geometry_completion_semantics", "GeomPreprocessor / _preprocess_contract.validate",
        "_landcover_native._validate_property_tables_postcondition", "geom._cell_subset._build_subset",
        "_container_compute._mesh", "_fast_hdf_typed MESH_FIELDS face_area_elevation_info/values"],
    "cell_volume_elevation": [
        "HdfMesh.get_mesh_cell_property_tables", "RasProcess._geometry_completion_semantics",
        "GeomPreprocessor / _preprocess_contract.validate", "_landcover_native._validate_property_tables_postcondition",
        "geom._cell_subset._build_subset", "_container_compute._mesh",
        "_fast_hdf_typed MESH_FIELDS cell_volume_elevation_info/values"],
    "xs_property_tables": [
        "HdfHydraulicTables.get_xs_htab / get_all_xs_htabs (rust_route_1 _cases.py)", "GeomPreprocessor",
        "_preprocess_contract.invalidate_products", "_fast_hdf_typed XS_FIELDS Property Tables/XSEC Info/Value"],
    "xs_property_cells": ["HdfHydraulicTables (Property Tables/Cell Info/Value)",
                          "_fast_hdf_typed XS_FIELDS Property Tables/Cell Info/Value"],
    "storage_area_volume_elevation": [
        "HdfStorageArea.get_volume_elevation_curve (also compute_stage_storage_curve / compute_volume_below_elevation)"],
    "structure_property_tables": ["_preprocess_contract.invalidate_products", "HdfStruc (empty Property Tables group handling)"],
    "pipe_property_tables": ["HdfPipe.get_pipe_network", "HdfMesh face/cell property-table readers (pipe-network exclusion)"],
}
GROUP_FAMILY = {f: "ptab_" + f for f in PT_READERS}
# Base test groups and the property-table families each reads.
# geometry_features: refinement regions, 2D perimeter, cell points, breaklines, BC lines, reference
# lines (no mesh faces/polygons, no property tables). The full "geometry" group includes mesh face and
# polygon readers, so it must not be assigned to a file without faces.
GROUP_READS = {"detection": set(), "metadata": set(), "timeseries": set(), "geometry": set(),
               "geometry_features": set(),
               "tables": {"xs_property_tables", "xs_property_cells"},
               **{g: {f} for f, g in GROUP_FAMILY.items()},
               "ptab_face_roundtrip": {"face_area_elevation"}}
# Declared intent for every excerpt: the test groups it is assigned. The rule
# below forbids dropping a family that any of these groups reads.
EXCERPT_INTENT = {
    # full file with a known issue (no faces/property tables): only face-free groups
    "ebfe701/1101001404.g01.rr": ["detection", "metadata", "geometry_features"],
    "ebfe/AustinOyster.p03.v507.structural": ["detection", "metadata"],
    "ebfe/1101001306.p01.features": ["detection", "metadata", "timeseries", "geometry"],
    "hec66/BaldEagleDamBrk.p07": ["detection", "metadata", "tables", "timeseries", "geometry"],
    "hec701/BaldEagleDamBrk.p03.all2d": ["detection", "metadata", "tables", "timeseries", "geometry"],
    "hec701/BaldEagleDamBrk.p03.refpts": ["detection", "metadata", "tables", "timeseries", "geometry"],
    "hec701/BaldEagleDamBrk.p06.infil": ["detection", "metadata", "tables", "timeseries", "geometry"],
    "hec701/EtherHollow.p01.bingham700": ["detection", "metadata", "tables", "timeseries"],
    "clb/Homewood.p02": ["detection", "metadata", "tables", "timeseries", "geometry"],
    "clb/CahabaRiver.g03": ["detection", "metadata", "tables", "geometry"],
    "rbfs/DowntownCorpusChris.p17": ["detection", "metadata", "tables", "timeseries", "geometry"],
    "ext/1101001306.p01.noproptables": ["detection", "metadata", "tables", "timeseries", "geometry"],
}
EXPLICIT_GROUPS = {"hec70/BaldEagleDamBrk.p18.full": ["ptab_face_roundtrip"]}
ROUNDTRIP_NOTE = (
    "Run on a temporary copy renamed BaldEagleDamBrk.p18.tmp.hdf; its root File Type 'HEC-RAS Results' and "
    "File Version 'HEC-RAS 7.0 April 2026' satisfy the writer guards. Verified 2026-10-24 with ras-commander "
    "0.108.0 source: 3 faces written, exact readback, 197 other faces unchanged, backup created. Negative guard: "
    "the native 7.0.1 EtherHollow.p01.tmp.hdf is rejected before backup by the version guard.")




def apply_property_table_rule(entries):
    """Assign test groups, enforce the drop rule and record dropped families."""
    for e in entries:
        if not is_hdf(e["local_source"]):
            e["property_tables"] = {"published": [], "native": True, "dropped": []}
            e["test_groups"] = ["detection", "raster-companion"]
            continue
        c = pt_census(e["local_source"], ZIP66, e.get("excerpt_args"))
        published = [f for f, v in c.items() if v["published"]]
        dropped = [f for f, v in c.items() if v["in_source"] and not v["published"]]
        if e["mode"] == "excerpt" and dropped and e["id"] not in EXCERPT_INTENT:
            raise AssertionError(f"{e['id']}: excerpt drops {dropped} but declares no test-group intent")
        base = EXCERPT_INTENT.get(e["id"], ["detection", "metadata", "tables", "timeseries", "geometry"])
        groups = list(base) + [GROUP_FAMILY[f] for f in published] + EXPLICIT_GROUPS.get(e["id"], [])
        for f in dropped:
            readers = [g for g in groups if f in GROUP_READS.get(g, set())]
            assert not readers, f"{e['id']}: drops {f} but assigned groups {readers} read it"
        e["property_tables"] = {
            "published": published,
            "native": e["mode"] == "full",
            "dropped": [{"family": f, "why": f"none of the assigned test groups {sorted(set(base))} read {f}; "
                                             "native coverage is provided by other core fixtures"} for f in dropped],
        }
        e["test_groups"] = sorted(set(groups))
        if e.get("provenance", {}).get("known_issue"):
            e["known_issue"] = e["provenance"]["known_issue"]
            needs_mesh = {"geometry", "tables", "timeseries", "ptab_face_roundtrip"} | {g for g in e["test_groups"] if g.startswith("ptab_")}
            assert not (set(e["test_groups"]) & needs_mesh), (e["id"], e["test_groups"])
        if e["id"] in EXPLICIT_GROUPS:
            e["roundtrip"] = ROUNDTRIP_NOTE


def _fx(e):
    return {"id": e["id"], "profile": e["profile"], "bytes": e["published_bytes"], "writer": e["writer"]}


def property_table_coverage(entries):
    """Every family needs >= 1 native 7.0.1 fixture in core (prefer one in smoke). Legacy native
    writers are listed for the engine's best-effort suites."""
    cov = {}
    for f, readers in PT_READERS.items():
        rows = [e for e in entries if "core" in e["profiles"] and f in e["property_tables"]["published"]]
        native = [e for e in rows if e["property_tables"]["native"]]
        assert native and all(is_current(e["writer"]) for e in native), f"no native 7.0.1 core fixture carries {f}"
        smoke_native = [e["id"] for e in native if "smoke" in e["profiles"]]
        legacy = [e for e in entries if e["profile"] in ("legacy", "archive") and f in e["property_tables"]["published"]
                  and e["property_tables"]["native"]]
        cov[f] = {"readers": readers, "status": "ok (7.0.1 native in smoke)" if smoke_native else "ok (7.0.1 native in core)",
                  "native_writer_versions": sorted({e["writer"] for e in native}),
                  "native_fixtures": [_fx(e) for e in native],
                  "verbatim_in_excerpts": [e["id"] for e in rows if not e["property_tables"]["native"]],
                  "smoke_native": smoke_native,
                  "legacy_native_writers": sorted({e["writer"] for e in legacy})}
    rt = [e for e in entries if "ptab_face_roundtrip" in e["test_groups"]]
    assert rt and all("face_area_elevation" in e["property_tables"]["published"] and e["property_tables"]["native"] for e in rt)
    cov["face_property_table_write_roundtrip"] = {
        "readers": ["HdfMesh.write_linux_tmp_face_property_tables",
                    "HdfMesh.set_mesh_face_property_tables (deprecated wrapper)",
                    "HdfMesh.extend_linux_tmp_face_property_tables"],
        "status": "legacy only: the ras-commander writer guard accepts HEC-RAS 7.0 and rejects 7.0.1 (7.0.1 gap)",
        "native_writer_versions": sorted({e["writer"] for e in rt}),
        "native_fixtures": [_fx(e) for e in rt],
        "note": ROUNDTRIP_NOTE + " Under the 7.0.1 policy this needs the writer guard to admit 7.0.1; then any native "
                                 "7.0.1 core plan with face tables (hec701r/BaldEagleDamBrk.p19) can serve."}
    cov["GeomStorage"] = {
        "readers": [], "status": "n/a", "native_writer_versions": [], "native_fixtures": [],
        "note": "GeomStorage reads only text-geometry 2D tolerance keys ('2D Face Area Elevation Profile Filter "
                "Tolerance', '2D Face Area Elevation Conveyance Ratio'); no HDF property-table reads."}
    return cov


# 7.0.1 coverage rule. Requirements with no 7.0.1 file under the caps must be listed
# here with the proposed fill; anything else unmet fails the build.
KNOWN_701_GAPS = {}
DETECTION_REQUIRED = {
    "plan-results": "plan HDF with results", "geometry": "geometry HDF", "land-cover": "land-cover layer",
    "soils": "soils (HSG) layer", "infiltration": "infiltration layer", "terrain": "terrain HDF",
    "companion-tif": "layer/terrain GeoTIFF", "sediment-material": "sediment bed-material layer",
}
KNOWN_DETECTION_GAPS = {
    "sediment-material": "no sediment bed-material layer that is 7.0.1-written or used as input by a recorded 7.0.1 run (add it to CONSUMED_BY_701 with its run receipt)",
    "stored-map-results": "not a 7.0.1 gap: 7.0.1 StoreAllMaps (Muncie p03, 2026-10-24) writes TIFF + VRT only, no "
                          "PostProcessing.hdf; the RBFS 6.4.1 PostProcessing.hdf stays in legacy. The 7.0.1 WSE (Max) "
                          "GeoTIFF is in core (storedmap701/)",
}
LC_TYPES_REQUIRED = ["LandCover", "Soils", "InfiltrationSCSCurveNumber", "InfiltrationGreenAmpt",
                     "InfiltrationDeficitConstantLoss"]


def coverage_701(entries):
    core = [e for e in entries if "core" in e["profiles"]]
    assert all(is_current(e["writer"]) for e in core), [e["id"] for e in core if not is_current(e["writer"])]
    out = {"features": {}, "detection": {}, "lc_types": {}, "units": {}, "gaps": {}}
    for k, (desc, _) in REQUIREMENTS.items():
        have = [e["id"] for e in core if k in e["features"]]
        smoke = [e["id"] for e in core if k in e["features"] and "smoke" in e["profiles"]]
        out["features"][k] = {"description": desc, "core_fixtures": have, "smoke_fixtures": smoke,
                              "status": "ok" if have else "GAP"}
        if not have:
            assert k in KNOWN_701_GAPS, f"7.0.1 coverage: no core file has {k} and no proposal is recorded"
            out["gaps"][k] = KNOWN_701_GAPS[k]
    for k, desc in DETECTION_REQUIRED.items():
        have = [e["id"] for e in core if e["detection"]["expected_kind"] == k]
        out["detection"][k] = {"description": desc, "core_fixtures": have, "status": "ok" if have else "GAP"}
        if not have:
            assert k in KNOWN_DETECTION_GAPS, k
            out["gaps"]["detection:" + k] = KNOWN_DETECTION_GAPS[k]
    out["gaps"]["detection:stored-map-results"] = KNOWN_DETECTION_GAPS["stored-map-results"]
    for t in LC_TYPES_REQUIRED:
        have = [e["id"] for e in core if e["lc_type"] == t]
        assert have, t
        out["lc_types"][t] = have
    for u in ("US Customary", "SI Units"):
        have = [e["id"] for e in core if (e["units"] or "") == u and e["detection"]["expected_kind"] == "plan-results"]
        assert have, u
        out["units"][u] = have
    out["quirks_701"] = {
        "geometry_labelled_results": [e["id"] for e in core if e["detection"]["expected_kind"] == "geometry"
                                      and e["file_type"] == "HEC-RAS Results"],
        "layer_without_file_type": [e["id"] for e in core if e["lc_type"] and not e["file_type"]],
    }
    return out




def check_caps(entries):
    per_pr = [e for e in entries if "core" in e["profiles"]]
    smoke = [e for e in entries if "smoke" in e["profiles"]]
    legacy = [e for e in entries if e["profile"] == "legacy"]
    for e in smoke:
        assert e["published_bytes"] <= SMOKE_FILE, ("smoke cap", e["id"], e["published_bytes"])
    for e in per_pr:
        assert e["published_bytes"] <= CORE_FILE, ("core cap", e["id"], e["published_bytes"])
        assert e["published_bytes"] <= PER_PR_MAX
    for e in legacy:
        assert e["published_bytes"] <= LEGACY_FILE, ("legacy cap", e["id"], e["published_bytes"])
    assert sum(e["published_bytes"] for e in smoke) <= SMOKE_TOTAL, sum(e["published_bytes"] for e in smoke)
    assert sum(e["published_bytes"] for e in legacy) <= LEGACY_TOTAL, sum(e["published_bytes"] for e in legacy)
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids)), "duplicate ids"


def main():
    entries = build()
    apply_property_table_rule(entries)
    ptcov = property_table_coverage(entries)
    cov701 = coverage_701(entries)
    hc = []
    tot = {}
    for e in entries + hc:
        for p in e.get("profiles", [e.get("profile", "?")]):
            n, b = tot.get(p, (0, 0))
            tot[p] = (n + 1, b + int(e.get("published_bytes", 0)))
    out = {"revision": 4, "generated": "2026-10-24",
           "support_policy": "CI tests only the latest HEC-RAS version, 7.0.1. smoke/core/extended contain only "
                             "7.0.1-written files and synthetic fixtures; HEC-RAS 5.0.x-7.0 files are best effort in "
                             "legacy (engine suites only) or archive (no CI).",
           "licence": "CC0 1.0 for CLB's contribution; upstream attribution in NOTICE",
           "repository": "gpt-cmdr/ras-hdf-test-corpus",
           "caps": {"smoke_file_bytes": SMOKE_FILE, "smoke_total_target_bytes": 50 * MB,
                    "core_file_bytes": CORE_FILE, "per_pr_max_bytes": PER_PR_MAX,
                    "legacy_file_bytes": LEGACY_FILE, "legacy_total_bytes": LEGACY_TOTAL},
           "excerpt_default": "--rows 8 --keep-last (first 8 time rows + last)",
           "totals": {p: {"files": n, "bytes": b} for p, (n, b) in tot.items()},
           "property_table_rule": "An excerpt may drop a property-table family only if none of its assigned test "
                                  "groups read that family (enforced by apply_property_table_rule).",
           "property_table_coverage": ptcov,
           "coverage_701": cov701,
           "entries": entries + hc, "dropped": [{"what": a, "why": b} for a, b in DROPPED]}
    for p, (n, b) in tot.items():
        mx = max(int(e.get("published_bytes", 0)) for e in entries + hc if p in e.get("profiles", [e.get("profile")]))
        print(f"{p:9} {n:3} files {b/MB:8.1f} MB   largest {mx/MB:6.2f} MB")
    for f, v in ptcov.items():
        print(f"{f:36} {v['status']:28} native={[(x['id'], round(x['bytes'] / MB, 2)) for x in v['native_fixtures']]}")
    for k, v in cov701["features"].items():
        print(f"  {k:26} {v['status']:4} {v['core_fixtures'][:4]}")
    for k, v in cov701["detection"].items():
        print(f"  det:{k:22} {v['status']:4} {v['core_fixtures'][:4]}")
    print("gaps:", json.dumps(cov701["gaps"], indent=1))
    print("quirks:", cov701["quirks_701"])
    check_caps(entries)
    json.dump(out, open(os.path.join(HERE, "proposed_manifest.json"), "w"), indent=1)
    print("written proposed_manifest.json")


if __name__ == "__main__":
    main()
