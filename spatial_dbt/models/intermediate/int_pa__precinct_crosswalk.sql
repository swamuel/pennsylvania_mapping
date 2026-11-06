-- One row per election precinct per year, with the 2021 voting district it
-- maps to and how it was matched:
--   code = padded vtd_code matches the 2021 file
--   name = no code match, but a unique name + municipality type match
--   none = unmapped
-- A code match is never overridden by a name match.

with keys as (
    select distinct
        election_year,
        county_code,
        lpad(fips_code, 3, '0')                   as countyfp,
        precinct_code,
        vtd_code,
        lpad(vtd_code, 6, '0')                    as vtd_padded,
        municipality_type_code,
        municipality_name,
        replace(regexp_replace(upper(municipality_name),
            '\s+(W|D|P|X)\s*\d+.*$', ''), ' ', '') as base,
        try_cast(case when municipality_breakdown_code_1 = 'W' then municipality_breakdown_name_1
                      when municipality_breakdown_code_2 = 'W' then municipality_breakdown_name_2
                 end as integer)                   as ward,
        try_cast(case when municipality_breakdown_code_1 in ('D', 'P') then municipality_breakdown_name_1
                      when municipality_breakdown_code_2 in ('D', 'P') then municipality_breakdown_name_2
                 end as integer)                   as sub
    from {{ ref('stg_pa__election_returns') }}
),

precincts as (
    select * from {{ ref('stg_pa__precincts_geom') }}
)

select
    k.election_year,
    k.county_code,
    k.countyfp,
    k.precinct_code,
    k.vtd_code,
    k.municipality_name,
    coalesce(c.geoid, n.geoid)                    as geoid,
    case when c.geoid is not null then 'code'
         when n.geoid is not null then 'name'
         else 'none' end                          as match_method
from keys k
left join precincts c
       on c.countyfp = k.countyfp
      and c.vtd_id   = k.vtd_padded
left join (select * from precincts where key_count = 1) n
       on n.countyfp  = k.countyfp
      and n.muni_type = k.municipality_type_code
      and n.base      = k.base
      and n.ward is not distinct from k.ward
      and n.sub  is not distinct from k.sub