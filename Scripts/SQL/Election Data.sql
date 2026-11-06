SELECT 
election_year
, election_type
, county_code
, precinct_code
, candidate_office_rank
, candidate_district
, candidate_party_rank
, candidate_ballot_position
, candidate_office_code
, candidate_party_code
, candidate_number
, candidate_last_name
, candidate_first_name
, candidate_middle_name
, candidate_suffix
, vote_total
, us_congressional_district
, state_senatorial_district
, state_house_district
, municipality_type_code
, municipality_name
FROM spatial_store.main.pa_bulk_election
where 
us_congressional_district = '16'
and candidate_office_code = 'USC';


SELECT distinct
election_year
,candidate_number 
,candidate_party_code
, candidate_last_name
, candidate_first_name
, candidate_middle_name
,us_congressional_district
FROM spatial_store.main.pa_bulk_election
where 
us_congressional_district in ('16','3')
and candidate_office_code = 'USC'
;


INSTALL spatial;
LOAD spatial;
DESCRIBE SELECT * FROM ST_Read('/vsizip/D:/ProjectWork/SpatialDataRepository/Data/Raw/CongressionalDistricts/districts104.zip/districts104.shp');

INSTALL spatial;
LOAD spatial;
SELECT congress, DISTRICT, ST_Area(geom) AS area
FROM spatial_store.main.pa_congressional_districts
WHERE congress IN (115, 116)
ORDER BY DISTRICT, congress;

SELECT election_year, election_type, count(*) FROM pa_bulk_election GROUP BY 1, 2 ORDER BY 1, 2;
SELECT DISTINCT candidate_office_code, us_congressional_district FROM pa_bulk_election WHERE candidate_office_code = 'USC' LIMIT 20;

SELECT election_year, county_name, district, sum(votes) AS votes
FROM stg_pa__congressional_results
GROUP BY ALL
ORDER BY 1, 2, 3;

SELECT r.election_year, r.raw_votes, j.joined_votes,
       r.raw_votes - j.joined_votes AS missing
FROM (SELECT election_year, sum(vote_total) AS raw_votes
      FROM stg_pa__election_returns
      WHERE candidate_office_code = 'USC'
      GROUP BY 1) r
JOIN (SELECT election_year, sum(votes) AS joined_votes
      FROM stg_pa__congressional_results
      GROUP BY 1) j USING (election_year)
ORDER BY 1;

SELECT election_year, district, sum(votes) FROM stg_pa__congressional_district_results GROUP BY 1, 2 ORDER BY 1, 2;


SELECT candidate_last_name, parties, votes
FROM stg_pa__congressional_district_results
WHERE election_year = 2000 AND district = 14
ORDER BY votes DESC;


SELECT r.election_year, r.raw_votes, j.joined_votes,
       r.raw_votes - j.joined_votes AS missing
FROM (SELECT election_year, sum(vote_total) AS raw_votes
      FROM stg_pa__election_returns
      WHERE candidate_office_code = 'USC'
      GROUP BY 1) r
JOIN (SELECT election_year, sum(votes) AS joined_votes
      FROM stg_pa__congressional_district_results
      GROUP BY 1) j USING (election_year)
ORDER BY 1;

-- 1. Why does the 1991 House file have 220 rows?
SELECT SLDL, NAME, count(*) AS pieces
FROM pa_house_1991
GROUP BY 1, 2
ORDER BY pieces DESC, SLDL
LIMIT 20;

-- 2. Which of the two District columns in the 2012 House file is the number?
SELECT District_N, District_1 FROM pa_house_2012 ORDER BY District_1 LIMIT 5;


-- 3. Do the precinct codes line up with your election data?
SELECT e.fips_code, e.vtd_code, v.FIPS, v.VTD, v.VTDST20, v.NAME
FROM (SELECT DISTINCT fips_code, vtd_code FROM pa_bulk_election
      WHERE election_year = '2020' AND county_code = '25' LIMIT 5) e,
     (SELECT * FROM pa_voting_districts_2021 WHERE COUNTYFP20 = '049' LIMIT 5) v;


INSTALL spatial;
LOAD spatial;
SELECT chamber, plan, count(*) AS districts
FROM stg_pa__legislative_districts_geom
GROUP BY 1, 2 ORDER BY 1, 2;

SELECT DISTINCT precinct_code, vtd_code, fips_code, municipality_name,
       municipality_breakdown_code_1, municipality_breakdown_name_1,
       municipality_breakdown_code_2, municipality_breakdown_name_2
FROM pa_bulk_election
WHERE election_year = '2020' AND county_code = '25'
  AND municipality_name ILIKE 'HARBORCREEK%'
ORDER BY precinct_code;

SELECT VTDST20, NAME, MCD_NAME
FROM pa_voting_districts_2021
WHERE COUNTYFP20 = '049' AND NAME ILIKE 'HARBORCREEK%'
ORDER BY NAME;



WITH e AS (
    SELECT election_year,
           lpad(fips_code, 3, '0')                   AS countyfp,
           lpad(vtd_code, 6, '0')                    AS vtd,
           sum(try_cast(vote_total AS integer))      AS votes
    FROM pa_bulk_election
    WHERE candidate_office_code = 'USC'
    GROUP BY 1, 2, 3
)
SELECT e.election_year,
       sum(e.votes)                                                  AS total_votes,
       sum(e.votes) FILTER (WHERE v.GEOID20 IS NOT NULL)             AS matched_votes,
       round(100.0 * sum(e.votes) FILTER (WHERE v.GEOID20 IS NOT NULL)
             / sum(e.votes), 1)                                      AS pct_matched
FROM e
LEFT JOIN (SELECT DISTINCT COUNTYFP20, VTDST20, GEOID20
           FROM pa_voting_districts_2021) v
  ON v.COUNTYFP20 = e.countyfp AND v.VTDST20 = e.vtd
GROUP BY 1
ORDER BY 1;


WITH e AS (
    SELECT county_code,
           lpad(fips_code, 3, '0')              AS countyfp,
           lpad(vtd_code, 6, '0')               AS vtd,
           sum(try_cast(vote_total AS integer)) AS votes
    FROM pa_bulk_election
    WHERE candidate_office_code = 'USC' AND election_year = '2024'
    GROUP BY 1, 2, 3
)
SELECT e.county_code, e.countyfp,
       count(*)                                              AS precinct_codes,
       count(*) FILTER (WHERE v.GEOID20 IS NULL)             AS unmatched_codes,
       sum(e.votes) FILTER (WHERE v.GEOID20 IS NULL)         AS unmatched_votes
FROM e
LEFT JOIN (SELECT DISTINCT COUNTYFP20, VTDST20, GEOID20
           FROM pa_voting_districts_2021) v
  ON v.COUNTYFP20 = e.countyfp AND v.VTDST20 = e.vtd
GROUP BY 1, 2
HAVING unmatched_codes > 0
ORDER BY unmatched_votes DESC
LIMIT 15;


WITH e AS (
    SELECT election_year, county_code,
           lpad(fips_code, 3, '0')              AS countyfp,
           lpad(vtd_code, 6, '0')               AS vtd,
           sum(try_cast(vote_total AS integer)) AS votes
    FROM pa_bulk_election
    WHERE candidate_office_code = 'USC' AND county_code IN ('25', '20')
    GROUP BY 1, 2, 3, 4
)
SELECT e.election_year, e.county_code,
       sum(e.votes)                                                   AS total_votes,
       round(100.0 * sum(e.votes) FILTER (WHERE v.GEOID20 IS NOT NULL)
             / sum(e.votes), 1)                                       AS pct_matched
FROM e
LEFT JOIN (SELECT DISTINCT COUNTYFP20, VTDST20, GEOID20
           FROM pa_voting_districts_2021) v
  ON v.COUNTYFP20 = e.countyfp AND v.VTDST20 = e.vtd
GROUP BY 1, 2
ORDER BY 2, 1;

WITH e AS (
    SELECT precinct_code, vtd_code, municipality_name,
           lpad(vtd_code, 6, '0')               AS vtd,
           sum(try_cast(vote_total AS integer)) AS votes
    FROM pa_bulk_election
    WHERE candidate_office_code = 'USC'
      AND election_year = '2024' AND county_code = '25'
    GROUP BY ALL
)
SELECT e.precinct_code, e.vtd_code, e.municipality_name, e.votes
FROM e
LEFT JOIN (SELECT DISTINCT VTDST20, GEOID20
           FROM pa_voting_districts_2021
           WHERE COUNTYFP20 = '049') v
  ON v.VTDST20 = e.vtd
WHERE v.GEOID20 IS NULL
ORDER BY e.votes DESC;

SELECT DISTINCT e.municipality_name AS election_name, v.NAME AS precinct_file_name
FROM pa_bulk_election e
JOIN pa_voting_districts_2021 v
  ON v.COUNTYFP20 = lpad(e.fips_code, 3, '0')
 AND v.VTDST20    = lpad(e.vtd_code, 6, '0')
WHERE e.election_year = '1992' AND e.county_code = '25'
ORDER BY 1
LIMIT 25;

SELECT VTDST20, NAME
FROM pa_voting_districts_2021
WHERE COUNTYFP20 = '049'
  AND (NAME ILIKE 'MILLCREEK%' OR NAME ILIKE 'MCKEAN%' OR NAME ILIKE 'MC KEAN%'
       OR NAME ILIKE 'GIRARD%' OR NAME ILIKE 'WAYNE%'
       OR NAME ILIKE 'ERIE WARD 01%' OR NAME ILIKE 'CORRY%')
ORDER BY NAME;




WITH e AS (
    SELECT election_year, county_code,
           lpad(fips_code, 3, '0') AS countyfp,
           lpad(vtd_code, 6, '0')  AS vtd,
           replace(regexp_replace(upper(municipality_name),
                   '\s+(W|D|P|X)\s*\d+.*$', ''), ' ', '') AS base,
           try_cast(CASE WHEN municipality_breakdown_code_1 = 'W' THEN municipality_breakdown_name_1
                         WHEN municipality_breakdown_code_2 = 'W' THEN municipality_breakdown_name_2
                    END AS integer) AS ward,
           try_cast(CASE WHEN municipality_breakdown_code_1 = 'D' THEN municipality_breakdown_name_1
                         WHEN municipality_breakdown_code_2 = 'D' THEN municipality_breakdown_name_2
                    END AS integer) AS dist,
           sum(try_cast(vote_total AS integer)) AS votes
    FROM pa_bulk_election
    WHERE candidate_office_code = 'USC' AND county_code IN ('25', '20')
    GROUP BY ALL
),
f AS (
    SELECT COUNTYFP20 AS countyfp,
           replace(upper(regexp_replace(NAME,
                   '\s+(WARD|DISTRICT)\s+\d+.*$|\s+Voting District$', '')), ' ', '') AS base,
           try_cast(nullif(regexp_extract(NAME, 'WARD\s+(\d+)', 1), '') AS integer)     AS ward,
           try_cast(nullif(regexp_extract(NAME, 'DISTRICT\s+(\d+)', 1), '') AS integer) AS dist,
           min(VTDST20) AS name_vtd,
           count(*)     AS n
    FROM pa_voting_districts_2021
    WHERE COUNTYFP20 IN ('049', '039')
    GROUP BY ALL
),
codes AS (
    SELECT DISTINCT COUNTYFP20 AS countyfp, VTDST20 AS vtd
    FROM pa_voting_districts_2021
)
SELECT e.election_year, e.county_code,
       sum(e.votes) AS total_votes,
       round(100.0 * sum(e.votes) FILTER (WHERE c.vtd IS NOT NULL) / sum(e.votes), 1)       AS pct_by_code,
       round(100.0 * sum(e.votes) FILTER (WHERE f.name_vtd IS NOT NULL) / sum(e.votes), 1)  AS pct_by_name,
       round(100.0 * sum(e.votes) FILTER (WHERE c.vtd IS NOT NULL
                                             OR f.name_vtd IS NOT NULL) / sum(e.votes), 1)  AS pct_either,
       max(f.n) AS max_dupes
FROM e
LEFT JOIN codes c ON c.countyfp = e.countyfp AND c.vtd = e.vtd
LEFT JOIN f ON f.countyfp = e.countyfp AND f.base = e.base
           AND f.ward IS NOT DISTINCT FROM e.ward
           AND f.dist IS NOT DISTINCT FROM e.dist
GROUP BY 1, 2
ORDER BY 2, 1;



SELECT replace(upper(regexp_replace(NAME,
              '\s+(WARD|DISTRICT)\s+\d+.*$|\s+Voting District$', '')), ' ', '') AS base,
       try_cast(nullif(regexp_extract(NAME, 'WARD\s+(\d+)', 1), '') AS integer)     AS ward,
       try_cast(nullif(regexp_extract(NAME, 'DISTRICT\s+(\d+)', 1), '') AS integer) AS dist,
       count(*) AS n,
       string_agg(NAME || ' (' || VTDST20 || ')', ' | ') AS precincts
FROM pa_voting_districts_2021
WHERE COUNTYFP20 = '039'
GROUP BY 1, 2, 3
HAVING count(*) > 1;


WITH e AS (
    SELECT election_year, county_code,
           lpad(fips_code, 3, '0') AS countyfp,
           lpad(vtd_code, 6, '0')  AS vtd,
           municipality_name,
           replace(regexp_replace(upper(municipality_name),
                   '\s+(W|D|P|X)\s*\d+.*$', ''), ' ', '') AS base,
           try_cast(CASE WHEN municipality_breakdown_code_1 = 'W' THEN municipality_breakdown_name_1
                         WHEN municipality_breakdown_code_2 = 'W' THEN municipality_breakdown_name_2
                    END AS integer) AS ward,
           try_cast(CASE WHEN municipality_breakdown_code_1 = 'D' THEN municipality_breakdown_name_1
                         WHEN municipality_breakdown_code_2 = 'D' THEN municipality_breakdown_name_2
                    END AS integer) AS dist,
           sum(try_cast(vote_total AS integer)) AS votes
    FROM pa_bulk_election
    WHERE candidate_office_code = 'USC' AND county_code IN ('25', '20')
    GROUP BY ALL
),
f AS (
    SELECT COUNTYFP20 AS countyfp, VTDST20, NAME,
           replace(upper(regexp_replace(NAME,
                   '\s+(WARD|DISTRICT)\s+\d+.*$|\s+Voting District$', '')), ' ', '') AS base,
           try_cast(nullif(regexp_extract(NAME, 'WARD\s+(\d+)', 1), '') AS integer)     AS ward,
           try_cast(nullif(regexp_extract(NAME, 'DISTRICT\s+(\d+)', 1), '') AS integer) AS dist
    FROM pa_voting_districts_2021
    WHERE COUNTYFP20 IN ('049', '039')
)
SELECT e.election_year, e.county_code, e.municipality_name,
       fc.NAME AS name_by_code, fn.NAME AS name_by_name, e.votes
FROM e
JOIN f fc ON fc.countyfp = e.countyfp AND fc.VTDST20 = e.vtd
JOIN f fn ON fn.countyfp = e.countyfp AND fn.base = e.base
         AND fn.ward IS NOT DISTINCT FROM e.ward
         AND fn.dist IS NOT DISTINCT FROM e.dist
WHERE fc.VTDST20 <> fn.VTDST20
ORDER BY e.votes DESC
LIMIT 30;

SELECT DISTINCT MCD_TYP_CD, MCD_TYP_NM FROM pa_voting_districts_2021 ORDER BY 1;

SELECT VTDST20, NAME, MCD_TYP_NM, MCD_TYP_CD
FROM pa_voting_districts_2021
WHERE COUNTYFP20 IN ('039', '049')
  AND (NAME ILIKE 'WOODCOCK%' OR NAME ILIKE 'VENANGO%' OR NAME ILIKE 'WATERFORD%')
ORDER BY NAME;

SELECT DISTINCT municipality_type_code, municipality_name
FROM pa_bulk_election
WHERE election_year = '2024' AND county_code IN ('20', '25')
  AND (municipality_name ILIKE 'WOODCOCK%' OR municipality_name ILIKE 'VENANGO%'
       OR municipality_name ILIKE 'WATERFORD%')
ORDER BY 2;



SELECT election_year, county_code, match_method, count(*) AS precincts
FROM int_pa__precinct_crosswalk
WHERE county_code IN (20, 25)
GROUP BY ALL
ORDER BY county_code, election_year, match_method;

SELECT election_year, county_code, precinct_code, vtd_code, municipality_name, count(*) AS n
FROM int_pa__precinct_crosswalk
GROUP BY ALL
HAVING count(*) > 1
LIMIT 20;


SELECT x.election_year, x.county_code, x.match_method,
       sum(r.vote_total) AS votes
FROM stg_pa__election_returns r
JOIN int_pa__precinct_crosswalk x
  ON x.election_year  = r.election_year
 AND x.county_code    = r.county_code
 AND x.precinct_code  = r.precinct_code
 AND x.vtd_code       = r.vtd_code
 AND x.municipality_name = r.municipality_name
WHERE r.candidate_office_code = 'USC'
  AND r.county_code IN (20, 25)
GROUP BY ALL
ORDER BY x.county_code, x.election_year, x.match_method;

SELECT DISTINCT election_year, precinct_code, vtd_code, municipality_name
FROM int_pa__precinct_crosswalk
WHERE county_code = 25 AND match_method = 'none' AND election_year IN (1992, 2012)
ORDER BY election_year, municipality_name;

SELECT DISTINCT election_year, precinct_code, vtd_code, municipality_type_code,
       municipality_name,
       municipality_breakdown_code_1, municipality_breakdown_name_1,
       municipality_breakdown_code_2, municipality_breakdown_name_2
FROM pa_bulk_election
WHERE county_code = '25'
  AND election_year IN ('1992', '2012')
  AND precinct_code IN ('150', '170', '190', '80', '870', '900', '905', '1070', '1075')
ORDER BY election_year, precinct_code;


SELECT s.election_year,
       s.votes            AS staging_votes,
       p.votes            AS results_votes,
       p.votes - s.votes  AS diff
FROM (SELECT election_year, sum(vote_total) AS votes
      FROM stg_pa__election_returns
      WHERE candidate_office_code = 'USC'
      GROUP BY 1) s
JOIN (SELECT election_year, sum(vote_total) AS votes
      FROM stg_pa__precinct_results
      WHERE candidate_office_code = 'USC'
      GROUP BY 1) p
  USING (election_year)
ORDER BY 1;