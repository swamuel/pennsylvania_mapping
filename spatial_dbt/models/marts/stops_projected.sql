SELECT
    stop_id,
    stop_code,
    stop_name,
    ST_Transform(
        ST_Point(stop_lon, stop_lat),
        'EPSG:4326',
        'EPSG:32617',
        always_xy := true
    ) AS geom
FROM {{ ref('stg_emta__bus_stops_geom') }}