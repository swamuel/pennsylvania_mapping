import duckdb

con = duckdb.connect("db/dev/spatial_store.duckdb")
con.execute("LOAD spatial;")

con.sql("SHOW TABLES").show()

con.sql("""
    COPY (
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        ORDER BY table_name, ordinal_position
    ) TO 'data/processed/data_dictionary.csv' (HEADER, DELIMITER ',')
""")