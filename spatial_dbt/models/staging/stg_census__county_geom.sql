SELECT
    OGC_FID
    ,STATEFP
    ,COUNTYFP
    ,COUNTYNS
    ,GEOID
    ,GEOIDFQ
    ,NAME
    ,NAMELSAD
    ,LSAD
    ,CLASSFP
    ,MTFCC
    ,CSAFP
    ,CBSAFP
    ,METDIVFP
    ,FUNCSTAT
    ,ALAND
    ,AWATER
    ,INTPTLAT
    ,INTPTLON
    ,geom
    ,sourcefile
    ,loadtime
FROM {{ source('raw', 'tiger_county') }}


