SELECT
    GEOID,
    NAME,
    COUNTYFP,
    ALAND,
    AWATER,
    ST_Transform(geom, 'EPSG:4269', 'EPSG:32617', always_xy := true) AS geom
FROM {{ ref('stg_census__tracts_geom') }}