"""Re-preprocess public eBFE 2D models in HEC-RAS 7.0.1 to get 7.0.1-written refinement regions.

For each Little Red River (HUC 11010014) project extracted from the public eBFE object
https://ebfedata.s3.amazonaws.com/11010014_LittleRed/11010014_Models.zip
(local CRC-verified extraction under SRC_ROOT), assemble a working project:
Input/* (text geometry, plans, flows, Precipitation/, Projection/), Terrain/,
Land Classification/, and from Output/ the flow HDFs, the DSS file and the delivered
geometry HDF (HEC-RAS keeps refinement regions and the saved mesh in the geometry
HDF, not the text .g01). Then run_6x_examples.py runs plan 01 in 7.0.1 with only
"Run UNet=0;Run PostProcess=0" changed (geometry preprocessing only).

Usage: python -B run_ebfe_rr_701.py RAS_COMMANDER_SRC SRC_ROOT EXAMPLES_ROOT RUNS_ROOT HUC10_DIR ...
"""
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def assemble(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(os.path.join(src, "Input"), dst)
    for sub in ("Terrain", "Land Classification"):
        shutil.copytree(os.path.join(src, sub), os.path.join(dst, sub))
    out = os.path.join(src, "Output")
    for p in glob.glob(os.path.join(out, "*.u[0-9][0-9].hdf")) + glob.glob(os.path.join(out, "*.dss")) + \
            glob.glob(os.path.join(out, "*.g[0-9][0-9].hdf")):
        shutil.copy2(p, dst)


def main(rc_src, src_root, examples, runs, dirs):
    for d in dirs:
        prj = [f for f in os.listdir(os.path.join(src_root, d, "Input")) if f.endswith(".prj")][0]
        code = prj[:-4]
        rel = f"eBFE_11010014/{code}"
        assemble(os.path.join(src_root, d), os.path.join(examples, rel))
        spec = f"{rel}:{prj}:01:Run UNet=0;Run PostProcess=0:geompre"
        subprocess.run([sys.executable, "-B", os.path.join(HERE, "run_6x_examples.py"), rc_src, "7.0.1",
                        examples, runs, spec], check=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
