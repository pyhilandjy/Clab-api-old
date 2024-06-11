from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database.query import SELECT_FILES
from app.database.worker import execute_select_query

router = APIRouter()


class FileModel(BaseModel):
    user_id: str


@router.post("/", tags=["Files"])
async def get_files(file_model: FileModel):
    """
    files 데이터를 가져오는 엔드포인트
    params = user_id"""

    files = execute_select_query(
        query=SELECT_FILES, params={"user_id": file_model.user_id}
    )

    if not files:
        raise HTTPException(status_code=404, detail="files not found")

    return files
