select
    try_cast(e.election_year as integer)             as election_year,
    e.election_type,
    try_cast(e.county_code as integer)               as county_code,
    c.county_name,
    e.precinct_code,
    e.candidate_office_code,
    e.candidate_party_code,
    e.candidate_last_name,
    e.candidate_first_name,
     e.vtd_code,
    try_cast(e.municipality_type_code as integer) as municipality_type_code,
    e.municipality_breakdown_code_1,
    e.municipality_breakdown_name_1,
    e.municipality_breakdown_code_2,
    e.municipality_breakdown_name_2,
    try_cast(e.vote_total as integer)                as vote_total,
    try_cast(e.us_congressional_district as integer) as us_congressional_district,
    try_cast(e.state_senatorial_district as integer) as state_senatorial_district,
    try_cast(e.state_house_district as integer)      as state_house_district,
    e.municipality_name,
    e.fips_code,
    e.sourcefile,
    e.loaded_at
from {{ source('raw', 'pa_bulk_election') }} e
left join {{ ref('pa_county_codes') }} c
  on c.county_code = try_cast(e.county_code as integer)