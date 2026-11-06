SELECT
    OGC_FID
    ,ZCTA5CE20
    ,GEOID20
    ,GEOIDFQ20
    ,CLASSFP20
    ,MTFCC20
    ,FUNCSTAT20
    ,ALAND20
    ,AWATER20
    ,INTPTLAT20
    ,INTPTLON20
    ,geom
    ,sourcefile
    ,loadtime
FROM {{ source('raw', 'tiger_zcta') }}