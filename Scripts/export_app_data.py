"""Export the small slice of data the Streamlit app needs, as Parquet.

Reads the dbt models in the local DuckDB and writes four files to
app/app_data/. The app reads only these files, so it runs anywhere
(including Streamlit Community Cloud) with no database and no spatial
extension. Re-run after loading new elections or rebuilding dbt.

Geometry is simplified and rounded here, once, so the app stays fast.
"""
import json
import logging
import sys
from pathlib import Path

import duckdb

DB_PATH = Path(r"D:\ProjectWork\SpatialDataRepository\db\dev\spatial_store.duckdb")
OUT = Path(r"D:\ProjectWork\SpatialDataRepository\app\app_data")

DISTRICT_TOLERANCE = 0.001    # degrees, about 100 m
PRECINCT_TOLERANCE = 0.0003   # degrees, about 30 m
COORD_DECIMALS = 5            # about 1 m
WARN_MB = 50                  # GitHub warns at 50 MB and refuses over 100 MB

log = logging.getLogger("export_app_data")


def round_geojson(text: str, decimals: int = COORD_DECIMALS) -> str:
    """Round every coordinate and drop whitespace, to shrink the file."""
    geom = json.loads(text)

    def rnd(c):
        return round(c, decimals) if isinstance(c, (int, float)) else [rnd(x) for x in c]

    geom["coordinates"] = rnd(geom["coordinates"])
    return json.dumps(geom, separators=(",", ":"))


def write_parquet(rows, columns, path: Path) -> None:
    """columns = [(name, duckdb_type), ...]; rows = list of tuples."""
    mem = duckdb.connect()
    col_sql = ", ".join(f"{name} {typ}" for name, typ in columns)
    mem.execute(f"CREATE TABLE t ({col_sql})")
    marks = ", ".join("?" for _ in columns)
    mem.executemany(f"INSERT INTO t VALUES ({marks})", rows)
    mem.execute(f"COPY t TO '{path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    mem.close()


def report(path: Path, rows: int) -> None:
    mb = path.stat().st_size / 1e6
    log.info("%-24s %8d rows  %6.1f MB", path.name, rows, mb)
    if mb > WARN_MB:
        log.warning("%s is over %d MB - too big for a comfortable commit", path.name, WARN_MB)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    con.execute("LOAD spatial")

    # 1. district results: one row per candidate per district per year
    path = OUT / "district_results.parquet"
    con.execute(f"""
        COPY (
            SELECT election_year, district, candidate_first_name, candidate_last_name,
                   parties, votes
            FROM stg_pa__congressional_district_results
        ) TO '{path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    report(path, con.execute(f"SELECT count(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0])

    # 2. district shapes: one simplified polygon per district per year
    rows = con.execute(f"""
        SELECT election_year, district,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(any_value(geom), {DISTRICT_TOLERANCE}))
        FROM stg_pa__congressional_district_results
        GROUP BY election_year, district
        ORDER BY 1, 2
    """).fetchall()
    rows = [(y, d, round_geojson(gj)) for y, d, gj in rows if gj]
    path = OUT / "district_shapes.parquet"
    write_parquet(rows, [("election_year", "INTEGER"), ("district", "INTEGER"),
                         ("gj", "VARCHAR")], path)
    report(path, len(rows))

    # 3. precinct results: congressional races only, one row per candidate per precinct
    path = OUT / "precinct_results.parquet"
    con.execute(f"""
        COPY (
            SELECT election_year, county_name, municipality_name, precinct_code,
                   geoid, match_method,
                   us_congressional_district AS district,
                   candidate_party_code, candidate_first_name, candidate_last_name,
                   sum(vote_total) AS vote_total
            FROM stg_pa__precinct_results
            WHERE candidate_office_code = 'USC'
            GROUP BY ALL
        ) TO '{path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
    """)
    report(path, con.execute(f"SELECT count(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0])

    # 4. precinct shapes: only precincts that actually appear in the results
    rows = con.execute(f"""
        SELECT geoid, name, county_name,
               ST_X(ST_Centroid(geom)), ST_Y(ST_Centroid(geom)),
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(geom, {PRECINCT_TOLERANCE}))
        FROM stg_pa__precincts_geom
        WHERE geoid IN (SELECT DISTINCT geoid FROM stg_pa__precinct_results
                        WHERE geoid IS NOT NULL AND candidate_office_code = 'USC')
    """).fetchall()
    rows = [(g, n, c, lo, la, round_geojson(gj)) for g, n, c, lo, la, gj in rows if gj]
    path = OUT / "precinct_shapes.parquet"
    write_parquet(rows, [("geoid", "VARCHAR"), ("name", "VARCHAR"),
                         ("county_name", "VARCHAR"), ("lon", "DOUBLE"),
                         ("lat", "DOUBLE"), ("gj", "VARCHAR")], path)
    report(path, len(rows))

    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
