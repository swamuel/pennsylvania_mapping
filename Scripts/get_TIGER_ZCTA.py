from pathlib import Path
import duckdb
from pipeline.io_utils import getwebfile, extractfile

STATE_FIPS = "42"
YEAR = "2023"
DB_PATH = "db/dev/spatial_store.duckdb"

url = f"https://www2.census.gov/geo/tiger/TIGER{YEAR}/ZCTA520/tl_{YEAR}_us_zcta520.zip"

zip_filename = f"tl_{YEAR}_us_zcta520"

zip_path = getwebfile(url, zip_filename)
extract_dir = extractfile(zip_path)

shp_path = extract_dir / f"{zip_filename}.shp"

con = duckdb.connect(DB_PATH)
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")

con.execute("DROP TABLE IF EXISTS tiger_zcta")
con.execute(f"""
    CREATE TABLE tiger_zcta AS
    SELECT *,'{zip_filename}' as sourcefile, now() as loadtime FROM ST_Read('{shp_path.as_posix()}')
""")