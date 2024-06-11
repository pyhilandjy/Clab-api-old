from typing import List, Optional

from fastapi import APIRouter, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel

from app.database.query import LOGIN, SELECT_USERS
from app.database.worker import execute_select_query

router = APIRouter()


class LoginInfo(BaseModel):
    id: str
    pw: str


class UserLoginResponse(BaseModel):
    role_id: int


# 패스워드 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/", tags=["Users"], response_model=List[dict])
async def get_users():
    """
    유저의 목록을 가져오는 엔드포인트
    """
    user_info = execute_select_query(query=SELECT_USERS)

    if not user_info:
        raise HTTPException(status_code=404, detail="Users not found")

    return user_info


@router.post("/login/", tags=["Users"], response_model=Optional[UserLoginResponse])
async def login(login_model: LoginInfo):
    """
    로그인 하기 위한 정보를 가져오는 엔드포인트
    """
    login_info = execute_select_query(
        query=LOGIN, params={"id": login_model.id, "pw": login_model.pw}
    )

    if not login_info:
        raise HTTPException(status_code=404, detail="User not found")

    # pw는 반환하면 위험하므로 user 설정
    user = login_info[0]

    # 비밀번호 검증
    if not pwd_context.verify(login_model.pw, user["pw"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    return {"role_id": user["role_id"]}
