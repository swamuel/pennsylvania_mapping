import duckdb
import requests
import zipfile
from pathlib import Path


def getwebfile (url,filename):
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    store_path = raw_dir / f"{filename}.zip"
    if not store_path.exists():
        resp =  requests.get(url, timeout=60)
        resp.raise_for_status()
        store_path.write_bytes(resp.content)
        print(f"Saved to {store_path}")
    else:
        print("Zip already downloaded, skipping.")

    return store_path

def extractfile (file):
    raw_dir = Path("data/raw")
    extract_dir = raw_dir / file.stem
    print("Extracting...")
    with zipfile.ZipFile(file, "r") as z:  # only zip file in read mode
        z.extractall(extract_dir)  #

    return extract_dir