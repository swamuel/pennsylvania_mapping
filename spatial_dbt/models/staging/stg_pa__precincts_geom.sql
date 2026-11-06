-- 2021 PA voting districts (precincts) with a normalized name key,
-- so election precincts can be matched by name when codes don't line up.
-- key_count > 1 means the name key is ambiguous (e.g. Waterford East/West).

with base as (
    select
        GEOID20                                   as geoid,
        COUNTYFP20                                as countyfp,
        VTDST20                                   as vtd_id,
        NAME                                      as name,
        MCD_NAME                                  as mcd_name,
        try_cast(MCD_TYP_CD as integer)           as muni_type,
        COUNTY_NME                                as county_name,
        P0010001                                  as total_pop,
        replace(upper(regexp_replace(NAME,
            '\s+(WARD|DISTRICT|PRECINCT)\s+\d+.*$'
            || '|\s+DISTRICT\s+(EAST|WEST|NORTH|SOUTH)$'
            || '|\s+Voting District$', '')), ' ', '')                          as base,
        try_cast(nullif(regexp_extract(NAME, 'WARD\s+(\d+)', 1), '') as integer) as ward,
        try_cast(nullif(regexp_extract(NAME, '(DISTRICT|PRECINCT)\s+(\d+)', 2), '') as integer) as sub,
        geom
    from {{ source('raw', 'pa_voting_districts_2021') }}
)

select
    *,
    count(*) over (partition by countyfp, muni_type, base, ward, sub) as key_count
from base