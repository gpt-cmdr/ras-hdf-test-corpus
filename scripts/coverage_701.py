"""Feature-family census for the 7.0.1 coverage rule (read-only).

Under the 2026-10-24 support policy every per-PR coverage requirement must be met
by HEC-RAS 7.0.1-written files in `core`. This module lists the HDF object names
an entry publishes (for an excerpt: those that survive its recipe, using the
same rules as property_table_census) and matches them against REQUIREMENTS.
Layer and detection requirements are checked on the manifest fields instead.

Used by build_proposed_manifest.py.
"""
import re

import h5py

from property_table_census import _args, _open

TS = r"Results/Unsteady/Output/Output Blocks/[^/]+/Unsteady Time Series/"
# requirement: (description, regexes; any match satisfies)
REQUIREMENTS = {
    "xs_timeseries_1d": ("1D cross-section unsteady time series", [TS + r"Cross Sections/"]),
    "steady_results": ("1D steady results", [r"^Results/Steady/"]),
    "mesh_timeseries_2d": ("2D cell/face unsteady time series", [TS + r"2D Flow Areas/[^/]+/(Water Surface|Face Velocity)$"]),
    "bc_lines": ("2D boundary-condition lines and their series", [r"^Geometry/Boundary Condition Lines/"]),
    "breaklines": ("2D breaklines", [r"^Geometry/2D Flow Area Break Lines/"]),
    "refinement_regions": ("2D refinement regions", [r"^Geometry/2D Flow Area Refinement Regions/"]),
    "reference_lines": ("reference-line geometry + series", [TS + r"Reference Lines/"]),
    "reference_points": ("reference-point geometry + series", [TS + r"Reference Points/"]),
    "storage_areas": ("storage areas", [r"^Geometry/Storage Areas/"]),
    "sa_2d_connections": ("SA/2D hydraulic connections", [r"SA 2D Area Conn"]),
    "bridges": ("bridges (geometry + series)", [r"^Geometry/Structures/Bridge Coefficient Attributes$", TS + r"Bridges/"]),
    "culverts": ("culverts", [r"^Geometry/Structures/Culvert Groups/", TS + r"Culverts/"]),
    "inline_structures": ("inline structures", [TS + r"Inline Structures/"]),
    "lateral_structures": ("lateral structures", [TS + r"Lateral Structures/"]),
    "breach": ("dam/levee breach variables", [TS + r".*Breach"]),
    "gates": ("gated structures", [r"^Geometry/Structures/Gate Groups/", TS + r".*/Gate Groups"]),
    "junctions": ("junctions", [r"^Geometry/Junctions/"]),
    "pump_station_geometry": ("pump-station geometry (attributes, pump groups, pumps)", [r"^Geometry/Pump Stations/"]),
    "pump_timeseries": ("pump-station structure variables", [TS + r"Pumping Stations/"]),
    "pipe_network_geometry": ("pipe-network geometry", [r"^Geometry/Pipe Networks/"]),
    "pipe_network_summary": ("pipe-network summary / volume accounting",
                             [r"Summary Output/Pipe Networks", r"Volume Accounting Pipe Networks"]),
    "sediment_1d": ("1D sediment results", [r"^Results/Sediment/Output Blocks/[^/]+/Sediment Time Series/Cross Sections"]),
    "sediment_2d": ("2D sediment results (active layer / bed change)", [r"^Results/Sediment/.*2D", TS + r"2D Flow Areas/[^/]+/.*(Bed|Sediment|Mass)"]),
    "sediment_bed_material_2d": ("2D sediment bed-material classification (geometry)", [r"^Geometry/2D Flow Areas/[^/]+/Sediment Bed Material/"]),
    "infiltration": ("infiltration geometry / results", [r"^Geometry/Infiltration", TS + r"2D Flow Areas/[^/]+/.*Infiltration"]),
    "met_precipitation": ("gridded meteorology precipitation", [r"^Event Conditions/Meteorology/Precipitation/"]),
    "encroachments": ("floodway encroachments", [r"^Results/Steady/.*Encroachment", r"^Plan Data/Encroachment"]),
    "non_newtonian": ("non-Newtonian (Bingham) settings", [r"Non-Newtonian|Bingham|Yield Stress"]),
    "structure_attributes": ("structure attribute table", [r"^Geometry/Structures/Attributes$"]),
}


def published_names(path, zip66, excerpt_args=None):
    excl = set(_args(excerpt_args or [], "--exclude-basename"))
    incl = _args(excerpt_args or [], "--include-only")
    names = []
    with _open(path, zip66) as h:
        def visit(n, o):
            names.append(n)
            if isinstance(o, (h5py.Group, h5py.Dataset)):
                names.extend(f"{n}@{a}" for a in o.attrs.keys())
        h.visititems(visit)

    def survives(n):
        n = n.split("@", 1)[0]
        if any(part in excl for part in n.split("/")):
            return False
        return not incl or any(n == p or n.startswith(p + "/") or p.startswith(n + "/") for p in incl)

    return [n for n in names if survives(n)]


def features(path, zip66, excerpt_args=None):
    names = published_names(path, zip66, excerpt_args)
    return sorted(k for k, (_, rxs) in REQUIREMENTS.items()
                  if any(re.search(rx, n) for rx in rxs for n in names))
