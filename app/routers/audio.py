from fastapi import APIRouter, File, UploadFile, HTTPException, Form, BackgroundTasks
from app.services.stt import (
    save_audio_file,
    gen_audio_file_id,
    gen_audio_file_path,
    create_audio_metadata,
    insert_audio_file_metadata,
    get_stt_results,
    insert_stt_segments,
    explode,
    rename_keys,
    delete_file,
    gen_audio_s3_path,
    save_audio_file_s3,
    gen_audio_file_path_m4a,
)


router = APIRouter()

# @router.post("/uploadfile/", tags=["Audio"])
# async def create_upload_file(
#     user_id: str = Form(...),
#     file: UploadFile = File(...),
# ):
#     """s3 .webm파일, stt .m4a"""
#     try:
#         file_id = gen_audio_file_id(user_id)
#         file_path = gen_audio_file_path(file_id)
#         s3_file_path = gen_audio_s3_path(file_id)
#         await save_audio_file(file, file_path)
#         m4a_file_path = gen_audio_file_path_m4a(file_id)
#         result = await process_stt_and_insert(m4a_file_path, file_id)
#         record_time = (result[0]["start_time"] + result[-1]["end_time"]) / 1000
#         metadata = create_audio_metadata(
#             file_id, user_id, file.filename, m4a_file_path, record_time
#         )
#         insert_audio_file_metadata(metadata)

#         delete_file(file_path, m4a_file_path)
#         await save_audio_file_s3(file, s3_file_path)
#         return {"message": "File uploaded and processing started in the background."}
#     except Exception as e:
#         raise e
#         # raise HTTPException(status_code=500, detail=str(e))


@router.post("/uploadfile/", tags=["Audio"])
async def create_upload_file(
    background_tasks: BackgroundTasks,
    user_id: str = Form(...),
    file: UploadFile = File(...),
):
    """s3 .webm파일, stt .m4a"""
    try:
        file_id = gen_audio_file_id(user_id)
        file_path = gen_audio_file_path(file_id)
        await save_audio_file(file, file_path)

        background_tasks.add_task(gen_audio_file, user_id, file_id, file_path)
        return {"message": "File uploaded and processing started in the background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_stt_and_insert(file_path, file_id):
    """음성파일 stt"""
    try:
        segments = get_stt_results(file_path)
        rename_segments = rename_keys(segments)
        explode_segments = explode(rename_segments, "textEdited")
        stt_results = insert_stt_segments(explode_segments, file_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return stt_results


async def gen_audio_file(user_id, file_id, file_path):
    try:
        s3_file_path = gen_audio_s3_path(file_id)
        m4a_file_path = gen_audio_file_path_m4a(file_id)

        # 저장된 파일 경로를 이용하여 STT 처리
        result = await process_stt_and_insert(m4a_file_path, file_id)

        record_time = (result[0]["start_time"] + result[-1]["end_time"]) / 1000
        metadata = create_audio_metadata(
            file_id, user_id, file_path, m4a_file_path, record_time
        )
        insert_audio_file_metadata(metadata)

        delete_file(file_path, m4a_file_path)
        await save_audio_file_s3(file_path, s3_file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
