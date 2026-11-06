"""Step 2: load PA legislative districts and 2021 precinct geography into DuckDB.

Bronze layer: one raw table per source file, loaded as-is (all original
columns) plus sourcefile and loaded_at. Combining and renaming happens later
in dbt, because each plan names its district column differently.

Re-runnable: each table is rebuilt from its zip every run.
"""
import logging
import sys
import zipfile
from pathlib import Path

import duckdb

DB_PATH = Path(r"D:\ProjectWork\SpatialDataRepository\db\dev\spatial_store.duckdb")
DEST = Path(r"D:\ProjectWork\SpatialDataRepository\Data\Raw\PA_Legislative")

# (table name, zip name in DEST, shapefile name inside the zip or None to auto-find)
LAYERS = [
    ("pa_house_1991", "house_1991.zip", None),
    ("pa_house_2001", "house_2001.zip", None),
    ("pa_house_2012", "house_2012.zip", None),
    ("pa_house_2021", "house_2021.zip", None),
    ("pa_senate_1991", "senate_1991.zip", None),
    ("pa_senate_2001", "senate_2001.zip", None),
    ("pa_senate_2012", "senate_2012.zip", None),
    ("pa_senate_2021", "senate_2021.zip", None),
    # precinct zip holds six layers; load only the two we need
    ("pa_voting_districts_2021", "precincts_2021.zip", "Geography/WP_VotingDistricts.shp"),
    ("pa_municipalities_2021", "precincts_2021.zip", "Geography/WP_Municipalities.shp"),
]

log = logging.getLogger("pa_legislative_load")


def find_shapefile(zip_path: Path) -> str:
    """The one .shp inside a zip; error if there are none or several."""
    with zipfile.ZipFile(zip_path) as z:
        shps = [n for n in z.namelist() if n.lower().endswith(".shp")]
    if len(shps) != 1:
        raise ValueError(f"{zip_path.name}: expected 1 .shp, found {shps}")
    return shps[0]


def load_layer(con, table: str, zip_name: str, shp: str | None) -> int:
    zip_path = DEST / zip_name
    if not zip_path.exists():
        raise FileNotFoundError(f"{zip_path} - run the download step first")
    shp = shp or find_shapefile(zip_path)
    uri = f"/vsizip/{zip_path.as_posix()}/{shp}"

    con.execute(f"""
        CREATE OR REPLACE TABLE {table} AS
        SELECT *,
               '{zip_name}' AS sourcefile,
               now()        AS loaded_at
        FROM ST_Read('{uri}')
    """)
    return con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    con = duckdb.connect(str(DB_PATH))
    con.execute("INSTALL spatial; LOAD spatial;")

    failures = 0
    for table, zip_name, shp in LAYERS:
        try:
            n = load_layer(con, table, zip_name, shp)
            log.info("%s <- %s: %d rows", table, zip_name, n)
        except Exception as exc:
            failures += 1
            log.error("%s failed: %s", table, exc)

    con.close()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())