select
    congress,
    -- the election in this year chose this Congress
    1786 + 2 * congress                       as election_year,
    cast(DISTRICT as integer)                 as district,
    lpad(cast(cast(DISTRICT as integer) as varchar), 2, '0') as district_code,
    cast(STARTCONG as integer)                as start_congress,
    cast(ENDCONG as integer)                  as end_congress,
    ID                                        as district_id,
    STATENAME                                 as state_name,
    geom,
    sourcefile,
    loaded_at
from {{ source('raw', 'pa_congressional_districts') }}