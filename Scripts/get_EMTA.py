import duckdb
import requests
import zipfile
from pathlib import Path

RAW_DIR = Path("data/raw")
DB_PATH = "db/dev/spatial_store.duckdb"

url = "https://emta.availtec.com/InfoPoint/gtfs-zip.ashx"
zip_path = RAW_DIR / "emta_gtfs.zip"
extract_dir = RAW_DIR / "emta_gtfs"


RAW_DIR.mkdir(parents=True, exist_ok=True)

if not zip_path.exists():
    print(f"Downloading {url} ...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status() #throws exception if an http requests
    zip_path.write_bytes(resp.content)
    print(f"Saved to {zip_path}")
else:
    print("Zip already downloaded, skipping.")

if not extract_dir.exists():
    print("Extracting...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)
else:
    print("Already extracted, skipping.")


stops_path = extract_dir / "stops.txt"

con = duckdb.connect(DB_PATH)
con.execute("DROP TABLE IF EXISTS bus_stops")
con.execute(f"""
    CREATE TABLE emta_busstops AS
    SELECT stop_id,stop_code,stop_name,stop_desc,stop_lat,stop_lon,zone_id,stop_url,location_type,parent_station,wheelchair_boarding
    FROM read_csv_auto('{stops_path.as_posix()}')
""")

count = con.execute("SELECT COUNT(*) FROM bus_stops").fetchone()

print(f"Loaded {count[0]} stops for from EMTA file")

con.sql("DESCRIBE bus_stops").show()

con.close()