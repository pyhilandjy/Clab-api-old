import os
import io
import zipfile
from datetime import date
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, FileResponse

from app.services.stt import sum_record_times, recordtime_to_min_sec

from app.database.query import (
    ADD_SELECTED_INDEX_DATA,
    DECREASE_INDEX,
    DELETE_INDEX_DATA,
    EDIT_STATUS,
    INCREASE_INDEX,
    SELECT_ACT_ID_STT,
    SELECT_ACT_NAME,
    SELECT_IMAGE_FILES,
    SELECT_IMAGE_TYPE,
    SELECT_STT_RESULTS,
    SELECT_STT_RESULTS_FOR_IMAGE,
    UPDATE_ACT_ID,
    UPDATE_STT_EDIT_TEXT,
    UPDATE_STT_SPEAKER,
    UPDATE_STT_TEXT,
    SENTENCE_LEN,
    SELECT_AUDIO,
    COUNT_ACT_ID,
)
from app.database.worker import execute_insert_update_query_single, execute_select_query
from app.services.gen_wordcloud import (
    FONT_PATH,
    create_wordcloud,
    violin_chart,
    fetch_image_from_s3,
    analyze_speech_data,
)

router = APIRouter()

ZIP_PATH = "../backend/app/image/image.zip"


class Files(BaseModel):
    file_id: str


@router.post("/results-by-file_id/", tags=["stt_results"], response_model=List[dict])
async def get_stt_results_by_file_id(stt_model: Files):
    """file_id별로 stt result를 가져오는 엔드포인트"""
    files_info = execute_select_query(
        query=SELECT_STT_RESULTS, params={"file_id": stt_model.file_id}
    )

    if not files_info:
        raise HTTPException(status_code=404, detail="Users not files_info")

    return files_info


class ImageModel(BaseModel):
    user_id: str
    start_date: date
    end_date: date


@router.post("/create/wordcloud/", tags=["image"])
async def generate_wordcloud(image_model: ImageModel):
    """워드클라우드를 생성하여 이미지 반환하는 엔드포인트"""
    stt_wordcloud = execute_select_query(
        query=SELECT_STT_RESULTS_FOR_IMAGE,
        params={
            "user_id": image_model.user_id,
            "start_date": image_model.start_date,
            "end_date": image_model.end_date,
        },
    )

    if not stt_wordcloud:
        raise HTTPException(
            status_code=404,
            detail="No STT results found for the specified user and date range.",
        )

    font_path = FONT_PATH

    # 워드클라우드 생성 및 이미지 저장
    type = "wordcloud"
    response, local_image_paths = create_wordcloud(
        stt_wordcloud, font_path, type, **dict(image_model)
    )
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])

    return {"local_image_paths": local_image_paths}


@router.get("/images/{image_path}", response_class=FileResponse, tags=["image"])
def get_image(image_path: str):
    """이미지를 제공하는 엔드포인트"""
    file_path = os.path.join("./app/image/", image_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)


class Imagefile(BaseModel):
    user_id: str
    start_date: date
    end_date: date
    type: str


@router.post("/image_files/images/", tags=["image"])
async def get_images(imagefilemodel: Imagefile):
    """
    images를 zip파일로 반환하는 엔드포인트
    """

    image_files_path = execute_select_query(
        query=SELECT_IMAGE_FILES,
        params={
            "user_id": imagefilemodel.user_id,
            "start_date": imagefilemodel.start_date,
            "end_date": imagefilemodel.end_date,
            "type": imagefilemodel.type,
        },
    )

    if not image_files_path:
        raise HTTPException(status_code=404, detail="files not found")
    bucket_name = "connectslab"
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for item in image_files_path:
            object_key = item["image_path"]
            image_data = fetch_image_from_s3(bucket_name, object_key)
            zip_file.writestr(os.path.basename(object_key), image_data)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={image_files_path}_images.zip"
        },
    )


class Imagetype(BaseModel):
    user_id: str
    start_date: date
    end_date: date


@router.post("/image_files/image_type/", tags=["image"], response_model=List[dict])
async def get_image_type(imagetypemodel: Imagetype):
    """
    user_id, start_date, end_date 별로 image_type을 가져오는 엔드포인트
    """

    image_type = execute_select_query(
        query=SELECT_IMAGE_TYPE,
        params={
            "user_id": imagetypemodel.user_id,
            "start_date": imagetypemodel.start_date,
            "end_date": imagetypemodel.end_date,
        },
    )

    if not image_type:
        raise HTTPException(status_code=404, detail="type not found")

    return image_type


@router.post("/create/violinplot/", tags=["image"])
async def generate_violin_chart(image_model: ImageModel):
    """워드클라우드를 생성하여 이미지 반환하는 엔드포인트(현재 2개의 파일은 보여지는것 구현x)"""
    stt_violin_chart = execute_select_query(
        query=SELECT_STT_RESULTS_FOR_IMAGE,
        params={
            "user_id": image_model.user_id,
            "start_date": image_model.start_date,
            "end_date": image_model.end_date,
        },
    )
    user_id = image_model.user_id
    start_date = image_model.start_date
    end_date = image_model.end_date
    type = "violin"
    font_path = FONT_PATH

    if not stt_violin_chart:
        raise HTTPException(
            status_code=404,
            detail="No STT results found for the specified user and date range.",
        )
    response = violin_chart(
        stt_violin_chart, user_id, start_date, end_date, type, font_path
    )
    if "error" in response:
        raise HTTPException(status_code=500, detail=response["error"])
    # 생성된 이미지를 직접 반환
    return FileResponse(response)


class UpdateText(BaseModel):
    file_id: str
    old_text: str
    new_text: str


@router.post("/results/update_text/", tags=["update_results"])
async def update_stt_text(update_text_model: UpdateText):
    update_text = execute_insert_update_query_single(
        query=UPDATE_STT_TEXT,
        params={
            "file_id": update_text_model.file_id,
            "old_text": update_text_model.old_text,
            "new_text": update_text_model.new_text,
        },
    )

    if update_text == 0:
        raise HTTPException(
            status_code=404, detail="STT result not found or no changes made"
        )

    return {
        "message": "STT result updated successfully",
    }


class UpdateSpeaker(BaseModel):
    file_id: str
    old_speaker: str
    new_speaker: str


@router.post("/results/update_speaker/", tags=["update_results"])
async def update_stt_speaker(update_speaker_model: UpdateSpeaker):
    update_speaker = execute_insert_update_query_single(
        query=UPDATE_STT_SPEAKER,
        params={
            "file_id": update_speaker_model.file_id,
            "old_speaker": update_speaker_model.old_speaker,
            "new_speaker": update_speaker_model.new_speaker,
        },
    )

    if update_speaker == 0:
        raise HTTPException(
            status_code=404, detail="STT result not found or no changes made"
        )

    return {
        "message": "STT result updated successfully",
    }


class UpdateTextEdit(BaseModel):
    file_id: str
    index: int
    new_text: str


@router.post("/results/update_text_edit/", tags=["update_results"])
async def update_stt_text_edit(update_text_edit: UpdateTextEdit):
    text_edit = execute_insert_update_query_single(
        query=UPDATE_STT_EDIT_TEXT,
        params={
            "file_id": update_text_edit.file_id,
            "index": update_text_edit.index,
            "new_text": update_text_edit.new_text,
        },
    )

    if text_edit == 0:
        raise HTTPException(
            status_code=404, detail="STT result not found or no changes made"
        )

    return {
        "message": "STT result updated successfully",
    }


class AddIndexData(BaseModel):
    file_id: str
    selected_index: int
    new_index: int


@router.post("/results/posts/index_add_data/", tags=["update_results"])
async def add_stt_index_data(add_index_data: AddIndexData):
    index_increase = execute_insert_update_query_single(
        query=INCREASE_INDEX,
        params={
            "file_id": add_index_data.file_id,
            "selected_index": add_index_data.selected_index,
        },
    )
    copy_data = execute_insert_update_query_single(
        query=ADD_SELECTED_INDEX_DATA,
        params={
            "file_id": add_index_data.file_id,
            "selected_index": add_index_data.selected_index,
            "new_index": add_index_data.new_index,
        },
    )

    if index_increase or copy_data == 0:
        execute_insert_update_query_single(
            query=DECREASE_INDEX,
            params={
                "file_id": add_index_data.file_id,
                "selected_index": add_index_data.selected_index,
            },
        )
        raise HTTPException(
            status_code=404, detail="STT result not found or no add row"
        )

    return {
        "message": "Add row updated successfully",
    }


class DelIndexData(BaseModel):
    file_id: str
    selected_index: int


@router.post("/results/index_delete_data/", tags=["update_results"])
async def delete_stt_index_data(del_index_data: DelIndexData):
    delete_data = execute_insert_update_query_single(
        query=DELETE_INDEX_DATA,
        params={
            "file_id": del_index_data.file_id,
            "selected_index": del_index_data.selected_index,
        },
    )
    decrement_index = execute_insert_update_query_single(
        query=DECREASE_INDEX,
        params={
            "file_id": del_index_data.file_id,
            "selected_index": del_index_data.selected_index,
        },
    )

    if delete_data or decrement_index == 0:
        raise HTTPException(
            status_code=404, detail="STT result not found or no add row"
        )

    return {
        "message": "Row deleted and indexes updated successfully",
    }


class EditStatus(BaseModel):
    file_id: str


@router.post("/results/edit_status/", tags=["status"])
async def edit_status(edit_status: EditStatus):
    edit_progress = execute_insert_update_query_single(
        query=EDIT_STATUS, params={"file_id": edit_status.file_id}
    )
    if edit_progress == 0:
        raise HTTPException(
            status_code=404, detail="STT result not found or no add row"
        )

    return {
        "message": "Edit status updated successfully",
    }


class SpeechAct(BaseModel):
    act_id: int


@router.post("/results/speech_act/", tags=["speech_act"], response_model=List[dict])
async def get_speech_act(speech_act: SpeechAct):
    """stt_result의 act_id를 통해 act_name을 불러오는 앤드포인트"""
    speech_info = execute_select_query(
        query=SELECT_ACT_ID_STT, params={"act_id": speech_act.act_id}
    )

    if not speech_info:
        raise HTTPException(status_code=404, detail="Users not found")

    return speech_info


@router.get("/get/speech_act/", tags=["speech_act"], response_model=List[dict])
async def get_act_name():
    """speech act의 목록을 가져오는 엔드포인트"""
    act_name = execute_select_query(
        query=SELECT_ACT_NAME,
    )

    if not act_name:
        raise HTTPException(status_code=404, detail="speech_act not found")

    return act_name


class ActIdUpdate(BaseModel):
    unique_id: int
    selected_act_name: str


@router.post("/update/act_id", tags=["speech_act"])
async def update_act_id(act_id_update: ActIdUpdate):
    update_act_id = execute_insert_update_query_single(
        query=UPDATE_ACT_ID,
        params={
            "selected_act_name": act_id_update.selected_act_name,
            "unique_id": act_id_update.unique_id,
        },
    )
    if update_act_id == 0:
        raise HTTPException(
            status_code=404, detail="STT result not found or cannot update act_id"
        )

    return {
        "message": "act_id updated successfully",
    }


def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(f"An error occurred while trying to delete the file: {str(e)}")


@router.post("/report/", tags=["report"])
async def morphs(image_model: ImageModel):
    """품사비율 반환 앤드포인트"""

    params = {
        "user_id": image_model.user_id,
        "start_date": image_model.start_date,
        "end_date": image_model.end_date,
    }

    stt_results = execute_select_query(query=SENTENCE_LEN, params=params)
    record_time = execute_select_query(query=SELECT_AUDIO, params=params)
    sum_record_time = sum_record_times(record_time)
    sum_record_time = recordtime_to_min_sec(sum_record_time)
    record_time_report = f"{sum_record_time['분']}분 {sum_record_time['초']}초"

    temp = {
        "가장 긴 문장": stt_results[0]["max_length"],
        "평균 문장 길이": int(stt_results[0]["avg_length"]),
        "녹음시간": record_time_report,
    }
    # return speech_data
    return temp


@router.post("/report/morps", tags=["report"])
async def morphs(image_model: ImageModel):
    """품사비율 반환 앤드포인트"""

    params = {
        "user_id": image_model.user_id,
        "start_date": image_model.start_date,
        "end_date": image_model.end_date,
    }

    morphs_data = execute_select_query(
        query=SELECT_STT_RESULTS_FOR_IMAGE, params=params
    )

    speech_data = analyze_speech_data(morphs_data)

    return speech_data


@router.post("/report/act_count", tags=["report"])
async def act_count(image_model: ImageModel):
    """품사비율 반환 앤드포인트"""

    params = {
        "user_id": image_model.user_id,
        "start_date": image_model.start_date,
        "end_date": image_model.end_date,
    }

    count_act_name = execute_select_query(query=COUNT_ACT_ID, params=params)
    speaker_act_count_dict = {}
    for row in count_act_name:
        speaker_label = row["speaker_label"]
        act_name = row["act_name"]
        count = row["count"]

        if speaker_label not in speaker_act_count_dict:
            speaker_act_count_dict[speaker_label] = {}

        speaker_act_count_dict[speaker_label][act_name] = count

    return speaker_act_count_dict


@router.post("/sentence_len/", tags=["stt_results"])
async def sentence_len(image_model: ImageModel):
    """문장길이, 평균길이 반환 앤드포인트"""
    stt_results = execute_select_query(
        query=SENTENCE_LEN,
        params={
            "user_id": image_model.user_id,
            "start_date": image_model.start_date,
            "end_date": image_model.end_date,
        },
    )

    if not stt_results:
        raise HTTPException(
            status_code=404,
            detail="No STT results found for the specified user and date range.",
        )
    return stt_results


@router.post("/record_time/", tags=["stt_results"])
async def record_time(image_model: ImageModel):
    """녹음 시간 반환 앤드포인트"""
    record_time = execute_select_query(
        query=SELECT_AUDIO,
        params={
            "user_id": image_model.user_id,
            "start_date": image_model.start_date,
            "end_date": image_model.end_date,
        },
    )
    sum_record_time = sum_record_times(record_time)
    if not record_time:
        raise HTTPException(
            status_code=404,
            detail="No STT results found for the specified user and date range.",
        )
    return recordtime_to_min_sec(sum_record_time)
