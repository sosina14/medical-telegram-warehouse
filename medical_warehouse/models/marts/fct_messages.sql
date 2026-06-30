-- models/marts/fct_messages.sql
WITH stg AS (SELECT * FROM {{ ref('stg_telegram_messages') }}),
     ch  AS (SELECT * FROM {{ ref('dim_channels') }}),
     dt  AS (SELECT * FROM {{ ref('dim_dates') }})
SELECT
    stg.message_id,
    ch.channel_key,
    dt.date_key,
    stg.message_text,
    stg.message_length,
    stg.view_count,
    stg.forward_count,
    stg.has_image,
    stg.image_path,
    stg.message_date
FROM stg
LEFT JOIN ch ON stg.channel_name     = ch.channel_name
LEFT JOIN dt ON stg.message_date::DATE = dt.full_date
