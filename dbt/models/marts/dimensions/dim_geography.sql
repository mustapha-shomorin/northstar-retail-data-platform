{{ config(materialized='table') }}

SELECT
    ROW_NUMBER() OVER (
        ORDER BY geolocation_zip_code_prefix
    ) AS geography_key,

    geolocation_zip_code_prefix,

    AVG(geolocation_lat) AS latitude,

    AVG(geolocation_lng) AS longitude,

    ANY_VALUE(geolocation_city) AS city,

    ANY_VALUE(geolocation_state) AS state

FROM {{ ref('stg_geolocation') }}

GROUP BY geolocation_zip_code_prefix