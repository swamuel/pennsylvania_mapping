-- One row per district per plan, House and Senate.
-- Each plan names its district column differently, so each gets its own CTE.
-- geometry goes through WKB so every plan has the same type (the source
-- files carry three different CRS tags, which UNION ALL won't mix).

with house_1991 as (
    -- 14 districts are stored as several pieces; merge to one shape each
    select 'house' as chamber, '1991' as plan,
           try_cast(SLDL as integer) as district,
           ST_Union_Agg(geom) as geom
    from {{ source('raw', 'pa_house_1991') }}
    where try_cast(SLDL as integer) is not null
    group by 1, 2, 3
),
house_2001 as (
    select 'house', '2001', cast(LEG_DISTRI as integer), geom
    from {{ source('raw', 'pa_house_2001') }}
),
house_2012 as (
    select 'house', '2012', District_1, geom
    from {{ source('raw', 'pa_house_2012') }}
),
house_2021 as (
    select 'house', '2021', DISTRICT_N, geom
    from {{ source('raw', 'pa_house_2021') }}
),
senate_1991 as (
    select 'senate', '1991', District_1, geom
    from {{ source('raw', 'pa_senate_1991') }}
),
senate_2001 as (
    select 'senate', '2001', District_1, geom
    from {{ source('raw', 'pa_senate_2001') }}
),
senate_2012 as (
    select 'senate', '2012', District_1, geom
    from {{ source('raw', 'pa_senate_2012') }}
),
senate_2021 as (
    select 'senate', '2021', cast(DISTRICT as integer), geom
    from {{ source('raw', 'pa_senate_2021') }}
),

unioned as (
    select * from house_1991
    union all select * from house_2001
    union all select * from house_2012
    union all select * from house_2021
    union all select * from senate_1991
    union all select * from senate_2001
    union all select * from senate_2012
    union all select * from senate_2021
)

select
    chamber,
    plan,
    district,
    ST_GeomFromWKB(ST_AsWKB(geom)) as geom   -- EPSG:4269 (NAD83)
from unioned