from sqlalchemy import text

INSERT_AUDIO_FILE_META_DATA = text(
    """
INSERT INTO files (id, user_id, file_name, file_path, created_at, record_time) VALUES 
(
    :file_id, 
    :user_id,
    :file_name,
    :file_path,
    current_timestamp,
    :record_time)
    """
)

INSERT_IMAGE_FILES_META_DATA = text(
    """
INSERT INTO image_files (id, speaker, user_id, start_date, end_date, image_path, type) VALUES 
(
    :image_id, 
    :speaker,
    :user_id,
    :start_date,
    :end_date,
    :image_path,
    :type)
    """
)

SELECT_USERS = text(
    """
SELECT id, *
FROM users
    """
)

SELECT_FILES = text(
    """
SELECT *
FROM files f
WHERE f.user_id = :user_id
"""
)


INSERT_STT_RESULT_DATA = text(
    """
INSERT INTO stt_results (file_id, index, start_time, end_time, text, confidence, speaker_label, text_edited, created_at) VALUES 
(
    :file_id, 
    :index,
    :start_time,
    :end_time,
    :text,
    :confidence,
    :speaker_label,
    :text_edited,
    current_timestamp)
    """
)

SELECT_STT_RESULTS = text(
    """
SELECT *
FROM stt_results sr
WHERE sr.file_id = :file_id
ORDER BY sr.index asc
    """
)


SELECT_STT_RESULTS_FOR_IMAGE = text(
    """
    SELECT sr.*
    FROM stt_results sr
    JOIN files f ON sr.file_id = f.id
    WHERE f.user_id = :user_id
        AND sr.created_at BETWEEN :start_date AND :end_date + INTERVAL '1 day'
    ORDER BY sr.created_at ASC, sr.index ASC

    """
)

SELECT_IMAGE_FILES = text(
    """
SELECT image_path
FROM image_files imf
WHERE imf.user_id = :user_id 
  AND imf.start_date = :start_date
  AND imf.end_date = :end_date
  AND imf.type = :type;
"""
)

SELECT_IMAGE_TYPE = text(
    """
SELECT DISTINCT type
FROM image_files
WHERE user_id = :user_id
  AND start_date = :start_date
  AND end_date = :end_date;
"""
)

UPDATE_STT_TEXT = text(
    """
    UPDATE stt_results
    SET text_edited = REPLACE(text_edited, :old_text, :new_text)
    WHERE file_id = :file_id
"""
)
UPDATE_STT_SPEAKER = text(
    """
    UPDATE stt_results
    SET speaker_label = REPLACE(speaker_label, :old_speaker, :new_speaker)
    WHERE file_id = :file_id
"""
)

UPDATE_STT_EDIT_TEXT = text(
    """
    UPDATE stt_results
    SET text_edited = :new_text
    WHERE file_id = :file_id AND index = :index;
"""
)

INCREASE_INDEX = text(
    """
UPDATE stt_results
SET index = index + 1
WHERE file_id = :file_id AND index > :selected_index
"""
)


ADD_SELECTED_INDEX_DATA = text(
    """
INSERT INTO stt_results (
    file_id, 
    index, 
    start_time, 
    end_time, 
    text, 
    confidence, 
    speaker_label, 
    text_edited, 
    created_at,
    stt_status
)
SELECT
    file_id, 
    :new_index as index,
    start_time, 
    end_time, 
    text, 
    confidence, 
    speaker_label, 
    text_edited, 
    created_at,
    stt_status
FROM
    stt_results
WHERE
    file_id = :file_id AND
    index = :selected_index;
"""
)


DELETE_INDEX_DATA = text(
    """
    DELETE FROM stt_results
    WHERE file_id = :file_id AND index = :selected_index;
    """
)


DECREASE_INDEX = text(
    """
    UPDATE stt_results
    SET index = index - 1
    WHERE file_id = :file_id AND index > :selected_index;
    """
)

EDIT_STATUS = text(
    """UPDATE files
SET edit_status = 'Edit complete'
WHERE id = :file_id
"""
)

SELECT_ACT_ID_STT = text(
    """
SELECT act_name
FROM speech_acts
WHERE id = :act_id
    """
)

SELECT_ACT_NAME = text(
    """
SELECT act_name, *
FROM speech_acts
    """
)

UPDATE_ACT_ID = text(
    """
UPDATE stt_results
SET act_id = (
    SELECT id
    FROM speech_acts
    WHERE act_name = :selected_act_name
)
WHERE id = :unique_id;
"""
)

COUNT_ACT_ID = text(
    """
SELECT
    speech_acts.act_name,
    stt_results.speaker_label,
    COUNT(stt_results.act_id) AS count
FROM
    stt_results
JOIN
    speech_acts ON stt_results.act_id = speech_acts.id
JOIN
    files f ON stt_results.file_id = f.id
WHERE
    f.user_id = :user_id
    AND stt_results.created_at BETWEEN :start_date AND :end_date + INTERVAL '1 day'
GROUP BY
    speech_acts.act_name,
    stt_results.speaker_label;

"""
)

LOGIN = text(
    """
    SELECT pw, 
    role_id FROM users 
    WHERE id = :id
"""
)


SENTENCE_LEN = text(
    """
    SELECT 
        MAX(LENGTH(text_edited)) as max_length,
        ROUND(AVG(LENGTH(text_edited))) as avg_length
    FROM stt_results sr
    JOIN files f ON sr.file_id = f.id
    WHERE f.user_id = :user_id
        AND sr.created_at BETWEEN :start_date AND :end_date + INTERVAL '1 day'

    """
)

SELECT_AUDIO = text(
    """
    SELECT record_time
    FROM files
    WHERE files.user_id = :user_id
        AND files.created_at BETWEEN :start_date AND :end_date + INTERVAL '1 day'
    """
)
