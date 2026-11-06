"""Load PA Congressional district boundaries (104th-119th) into DuckDB.

Reads each districtsNNN.zip in place via GDAL's /vsizip/ (no extraction),
keeps Pennsylvania only, and accumulates every Congress in one table.
Re-runnable: each file is DELETEd by sourcefile before it is INSERTed.
"""
import logging
import re
import sys
from pathlib import Path

import duckdb

DB_PATH = Path(r"D:\ProjectWork\SpatialDataRepository\db\dev\spatial_store.duckdb")
ZIP_DIR = Path(r"D:\ProjectWork\SpatialDataRepository\Data\Raw\CongressionalDistricts")
TABLE = "pa_congressional_districts"
STATE = "Pennsylvania"

log = logging.getLogger("congressional_districts")


def congress_number(zip_path: Path) -> int:
    """districts104.zip -> 104"""
    match = re.search(r"\d+", zip_path.stem)
    if not match:
        raise ValueError(f"No Congress number in filename: {zip_path.name}")
    return int(match.group())


def shp_uri(zip_path: Path) -> str:
    """GDAL virtual path to the .shp inside the zip (forward slashes)."""
    return f"/vsizip/{zip_path.as_posix()}/{zip_path.stem}.shp"


def create_table_if_missing(con, first_zip: Path) -> None:
    """Empty table with the right columns, so the loop is always DELETE + INSERT."""
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} AS
        SELECT
            0::INTEGER AS congress,
            *,
            ''::VARCHAR AS sourcefile,
            now()::TIMESTAMP AS loaded_at
        FROM ST_Read('{shp_uri(first_zip)}')
        WHERE 1 = 0
    """)


def load_one(con, zip_path: Path) -> int:
    congress = congress_number(zip_path)
    label = zip_path.name

    con.execute("BEGIN")
    try:
        con.execute(f"DELETE FROM {TABLE} WHERE sourcefile = ?", [label])
        con.execute(f"""
            INSERT INTO {TABLE}
            SELECT
                {congress} AS congress,
                *,
                ? AS sourcefile,
                now() AS loaded_at
            FROM ST_Read('{shp_uri(zip_path)}')
            WHERE STATENAME = '{STATE}'
        """, [label])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    return con.execute(
        f"SELECT count(*) FROM {TABLE} WHERE sourcefile = ?", [label]
    ).fetchone()[0]


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    zips = sorted(ZIP_DIR.glob("districts*.zip"), key=congress_number)
    if not zips:
        log.error("No districts*.zip files in %s", ZIP_DIR)
        return 1
    log.info("Found %d files: %s .. %s", len(zips), zips[0].name, zips[-1].name)

    con = duckdb.connect(str(DB_PATH))
    con.execute("INSTALL spatial; LOAD spatial;")
    create_table_if_missing(con, zips[0])

    for z in zips:
        n = load_one(con, z)
        log.info("%s -> %d %s rows", z.name, n, STATE)
        if n == 0:
            log.warning("%s loaded 0 rows - check STATENAME values", z.name)

    log.info("Rows per Congress:")
    for row in con.execute(
        f"SELECT congress, count(*) FROM {TABLE} GROUP BY congress ORDER BY congress"
    ).fetchall():
        log.info("  %s: %s", *row)
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())