SELECT
    osmid,
    highway,
    name,
    length,
    access,
    ST_Transform(geometry, 'EPSG:4326', 'EPSG:32617',always_xy := true) AS geometry
FROM {{ ref('stg_osm__roads_geom') }}