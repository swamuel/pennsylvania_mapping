-- Election returns with the 2021 precinct each row maps to (geoid) and
-- how it was matched. Geometry is left in stg_pa__precincts_geom and
-- joined on geoid when needed.

select
    r.election_year,
    r.county_code,
    r.county_name,
    r.precinct_code,
    r.municipality_name,
    r.candidate_office_code,
    r.us_congressional_district,
    r.state_senatorial_district,
    r.state_house_district,
    r.candidate_party_code,
    r.candidate_first_name,
    r.candidate_last_name,
    r.vote_total,
    x.geoid,
    coalesce(x.match_method, 'none') as match_method
from {{ ref('stg_pa__election_returns') }} r
left join {{ ref('int_pa__precinct_crosswalk') }} x
       on x.election_year = r.election_year
      and x.county_code   = r.county_code
      and x.precinct_code = r.precinct_code
      and x.vtd_code is not distinct from r.vtd_code
      and x.municipality_name is not distinct from r.municipality_name