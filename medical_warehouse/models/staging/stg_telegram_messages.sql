-- models/staging/stg_telegram_messages.sql
WITH raw AS (
    SELECT * FROM raw.telegram_messages
),
cleaned AS (
    SELECT
        message_id,
        LOWER(TRIM(channel_name))                    AS channel_name,
        message_date::TIMESTAMP                      AS message_date,
        NULLIF(TRIM(message_text), '')               AS message_text,
        COALESCE(has_media, FALSE)                   AS has_media,
        image_path,
        GREATEST(COALESCE(views, 0), 0)              AS view_count,
        GREATEST(COALESCE(forwards, 0), 0)           AS forward_count,
        LENGTH(NULLIF(TRIM(message_text), ''))       AS message_length,
        (image_path IS NOT NULL)                     AS has_image
    FROM raw
    WHERE
        message_text IS NOT NULL
        AND TRIM(message_text) != ''
        AND message_date <= NOW()
        AND message_id IS NOT NULL
)
SELECT * FROM cleaned
