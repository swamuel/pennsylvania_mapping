SELECT
    STATEFP
    ,UNSDLEA
    ,GEOID
    ,GEOIDFQ
    ,NAME
    ,LSAD
    ,LOGRADE
    ,HIGRADE
    ,MTFCC
    ,SDTYP
    ,FUNCSTAT
    ,ALAND
    ,AWATER
    ,INTPTLAT
    ,INTPTLON
    ,geom
    ,sourcefile
    ,loadtime

FROM {{ source('raw', 'tiger_schooldistrict') }}


