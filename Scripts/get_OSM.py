import osmnx as ox
import duckdb

from pathlib import Path

RAW_DIR = Path("data/raw")
DB_PATH = "db/dev/spatial_store.duckdb"
con = duckdb.connect(DB_PATH)

g = ox.graph_from_place("Erie County, Pennsylvania, USA", network_type='walk')

nodes, edges = ox.graph_to_gdfs(g)

edges["geometry"] = edges["geometry"].apply(lambda g: g.wkb)

con.execute("""
    DROP TABLE IF EXISTS osm_roads
""")
con.execute("""
    CREATE TABLE osm_roads AS
    SELECT osmid, highway, name, length, access, ST_GeomFromWKB(geometry) AS geometry
    FROM edges
""")

con.sql("SELECT COUNT(*) FROM osm_roads").show()

con.sql("DESCRIBE osm_roads").show()