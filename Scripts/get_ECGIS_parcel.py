import duckdb

con = duckdb.connect("db/dev/spatial_store.duckdb")
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")

con.execute("DROP TABLE IF EXISTS ECGIS_parcel")
con.execute("""
    CREATE TABLE ECGIS_parcel AS
    SELECT * FROM ST_Read('data/raw/eriecounty_parcel_2025/ErieCountyParcels202603.shp')
""")

con.sql("SELECT COUNT(*) FROM ECGIS_parcel").show()
con.sql("DESCRIBE ECGIS_parcel").show()