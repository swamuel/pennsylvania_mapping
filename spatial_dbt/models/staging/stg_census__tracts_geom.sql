SELECT
    GEOID,
    NAME,
    COUNTYFP,
    ALAND,
    AWATER,
    geom
FROM {{ source('raw', 'tiger_censustract') }}