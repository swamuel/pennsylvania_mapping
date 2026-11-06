from pathlib import Path
import duckdb
from pipeline.io_utils import getwebfile, extractfile

STATE_FIPS = "42"
YEAR = "2023"
DB_PATH = "db/dev/spatial_store.duckdb"

url = f"https://www2.census.gov/geo/tiger/TIGER{YEAR}/UNSD/tl_{YEAR}_{STATE_FIPS}_unsd.zip"
zip_filename = f"tl_{YEAR}_{STATE_FIPS}_unsd"

zip_path = getwebfile(url, zip_filename)
extract_dir = extractfile(zip_path)

shp_path = extract_dir / f"{zip_filename}.shp"

con = duckdb.connect(DB_PATH)
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")

con.execute("DROP TABLE IF EXISTS tiger_schooldistrict")
con.execute(f"""
    CREATE TABLE tiger_schooldistrict AS
    SELECT *,'{zip_filename}' as sourcefile, now() as loadtime FROM ST_Read('{shp_path.as_posix()}')
""")