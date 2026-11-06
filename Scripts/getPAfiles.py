"""Step 1: download PA legislative district shapefiles and print their layout.

Downloads the House/Senate plans (and the precinct geography) from the PA
Legislative Reapportionment Commission site, saves each under a clean local
name, and prints the shapefile name inside and its columns so we can write
the loader against what is actually there.

Nothing is written to DuckDB in this step.
"""
import logging
import sys
import zipfile
from pathlib import Path

import duckdb
import requests

DEST = Path(r"D:\ProjectWork\SpatialDataRepository\Data\Raw\PA_Legislative")
DISTRICTS = "https://www.redistricting.state.pa.us/Resources/GISData/Districts/"
CENSUS = "https://www.redistricting.state.pa.us/resources/GISData/Census/"

# (base url, path from the page, clean local name)
FILES = [
    (DISTRICTS, "Legislative/House/1991/SHAPE/PA-House-Districts-1991.zip", "house_1991"),
    (DISTRICTS, "Legislative/House/2001/SHAPE/PA-House-Districts-2001.zip", "house_2001"),
    (DISTRICTS, "Legislative/House/2011-Revised-final/SHAPE/2011-Revised-final-Plan-SHAPEFILES-House.zip", "house_2012"),
    (DISTRICTS, "Legislative/House/2021-Final/SHAPE/2022%20LRC-House-Final.zip", "house_2021"),
    (DISTRICTS, "Legislative/Senate/1991/SHAPE/PA-Senate-Districts-1991.zip", "senate_1991"),
    (DISTRICTS, "Legislative/Senate/2001/SHAPE/PA-Senate-Districts-2001.zip", "senate_2001"),
    (DISTRICTS, "Legislative/senate/2011-Revised-final/SHAPE/FinalSenatePlan2012.zip", "senate_2012"),
    (DISTRICTS, "Legislative/Senate/2021-Final/SHAPE/2022%20LRC-Senate-Final.zip", "senate_2021"),
    (CENSUS, "2021/2021-DataSet1-WithoutPrisoner/2021%20LRC%20Data%20Release%201b%20-%20Geography.zip", "precincts_2021"),
]

log = logging.getLogger("pa_legislative")


def download(base: str, path: str, name: str) -> Path:
    """Save as DEST/<name>.zip; skip if already there."""
    DEST.mkdir(parents=True, exist_ok=True)
    out = DEST / f"{name}.zip"
    if out.exists():
        log.info("%s already downloaded", out.name)
        return out
    resp = requests.get(base + path, timeout=120)
    resp.raise_for_status()
    out.write_bytes(resp.content)
    log.info("downloaded %s (%.1f MB)", out.name, len(resp.content) / 1e6)
    return out


def find_shapefiles(zip_path: Path) -> list[str]:
    """Names of every .shp inside the zip (may be in subfolders)."""
    with zipfile.ZipFile(zip_path) as z:
        return [n for n in z.namelist() if n.lower().endswith(".shp")]


def describe(con, zip_path: Path, shp_name: str) -> None:
    uri = f"/vsizip/{zip_path.as_posix()}/{shp_name}"
    rows = con.execute(f"DESCRIBE SELECT * FROM ST_Read('{uri}')").fetchall()
    count = con.execute(f"SELECT count(*) FROM ST_Read('{uri}')").fetchone()[0]
    log.info("  %s: %d features", shp_name, count)
    for col_name, col_type, *_ in rows:
        log.info("    %-20s %s", col_name, col_type)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = duckdb.connect()
    con.execute("INSTALL spatial; LOAD spatial;")

    for base, path, name in FILES:
        log.info("=== %s", name)
        try:
            zip_path = download(base, path, name)
            shps = find_shapefiles(zip_path)
            if not shps:
                log.warning("  no .shp found in %s", zip_path.name)
            for shp in shps:
                describe(con, zip_path, shp)
        except Exception as exc:
            log.error("  %s failed: %s", name, exc)
    return 0


if __name__ == "__main__":
    sys.exit(main())