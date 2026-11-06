SELECT
    osmid,
    highway,
    name,
    length,
    access,
    geometry
FROM {{ source('raw', 'osm_roads') }}
WHERE highway NOT IN (
    'motorway',
    'motorway_link',
    'trunk',
    'trunk_link',
    'service',
    'track'
)