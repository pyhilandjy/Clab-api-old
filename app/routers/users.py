from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.database.query import LOGIN, SELECT_USERS
from app.database.worker import execute_select_query
from app.config import settings


router = APIRouter()

SECRET_KEY = settings.secret_key  # 환경 변수에서 비밀 키 로드
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 180

# 패스워드 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[str] = None


class LoginInfo(BaseModel):
    id: str
    pw: str


class UserLoginResponse(BaseModel):
    role_id: int


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )  # 3시간으로 설정
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(id=user_id)
    except JWTError:
        raise credentials_exception
    user_info = execute_select_query(query=SELECT_USERS, params={"id": token_data.id})
    if not user_info:
        raise credentials_exception
    return user_info[0]


@router.post("/", tags=["Users"], response_model=List[dict])
async def get_users():
    """
    유저의 목록을 가져오는 엔드포인트
    """
    user_info = execute_select_query(query=SELECT_USERS)

    if not user_info:
        raise HTTPException(status_code=404, detail="Users not found")

    return user_info


@router.post("/login/", tags=["Users"], response_model=Token)
async def login(login_model: LoginInfo):
    """
    로그인 하기 위한 정보를 가져오는 엔드포인트
    """
    login_info = execute_select_query(query=LOGIN, params={"id": login_model.id})

    if not login_info:
        raise HTTPException(status_code=404, detail="User not found")

    user = login_info[0]

    # 비밀번호 검증
    if not verify_password(login_model.pw, user["pw"]):
        raise HTTPException(status_code=400, detail="Incorrect password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", tags=["Users"], response_model=dict)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
