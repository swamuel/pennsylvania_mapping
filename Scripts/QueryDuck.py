import duckdb

con = duckdb.connect("db/spatial_store.duckdb")
con.execute("LOAD spatial;")

# queries go here
con.sql("""
    SELECT table_name, column_name, data_type
    FROM information_schema.columns
    ORDER BY table_name, ordinal_position
""").show()

con.close()