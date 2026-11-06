import duckdb
con = duckdb.connect("db/dev/spatial_store.duckdb")
con.execute("INSTALL spatial;")
con.execute("LOAD spatial;")

#con.execute("DROP TABLE IF EXISTS pa_bulk_election")

con.execute("""
    insert into pa_bulk_election 
    SELECT ,'2016_PA_bulk_data.txt' as sourcefile,now()  as loaded_at FROM read_csv('D:/ProjectWork/SpatialDataRepository/Data/Raw/pa_election_data/2016_PA_bulk_data.txt',header = false, all_varchar = true
        ,names = ['election_year', 'election_type', 'county_code', 'precinct_code',
'candidate_office_rank', 'candidate_district', 'candidate_party_rank',
'candidate_ballot_position', 'candidate_office_code', 'candidate_party_code',
'candidate_number', 'candidate_last_name', 'candidate_first_name',
'candidate_middle_name', 'candidate_suffix', 'vote_total', 'yes_vote_total',
'no_vote_total', 'us_congressional_district', 'state_senatorial_district',
'state_house_district', 'municipality_type_code', 'municipality_name',
'municipality_breakdown_code_1', 'municipality_breakdown_name_1',
'municipality_breakdown_code_2', 'municipality_breakdown_name_2',
'bi_county_code', 'mcd_code', 'fips_code', 'vtd_code', 'ballot_question',
'record_type', 'previous_precinct_code', 'previous_us_congressional_district',
'previous_state_senatorial_district', 'previous_state_house_district'])
""")

con.sql("SELECT COUNT(*),election_year FROM pa_bulk_election group by election_year").show()
con.sql("DESCRIBE pa_bulk_election").show()