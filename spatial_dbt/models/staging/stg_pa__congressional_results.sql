with returns as (
    select
        *,
        -- 1992 elected the 103rd Congress; the 104 file's boundaries cover it
        greatest((election_year - 1786) // 2, 104) as congress
    from {{ ref('stg_pa__election_returns') }}
    where candidate_office_code = 'USC'
)

select
    r.election_year,
    r.congress,
    r.county_name,
    r.us_congressional_district  as district,
    r.candidate_party_code,
    r.candidate_last_name,
    sum(r.vote_total)            as votes,
    d.geom
from returns r
join {{ ref('stg_lewis__congressional_districts_geom') }} d
  on d.congress = r.congress
 and d.district = r.us_congressional_district
group by all