from fastapi import APIRouter, Depends, status, Request, File, Form, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from configuration.database import get_database_connection
from dotenv import load_dotenv
from services.user_service import user_register_service
from services.user_service import user_login_service
from services.user_service import user_update_password_service
from services.user_service import user_reset_password_service
from services.user_service import user_get_detail_service
from services.user_service import user_get_all_service
from services.user_service import user_get_detail_me_service
from repositories.user_repository import user_find_by_username_repository
import os
from services.station_service import station_add_to_user_service

# exception and validation
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
SECRET_KEY = "3e8a3f31aab886f8793176988f8298c9265f84b8388c9fef93635b08951f379b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


origins = ["*"]

load_dotenv("./.env")
SSH_HOST = os.getenv("ssh_host")
SSH_PORT = int(os.getenv("ssh_port"))
SSH_USERNAME = os.getenv("ssh_username")
SSH_PASSWORD = os.getenv("ssh_password")
MONGO_HOST = os.getenv("database_host")
MONGO_DB = os.getenv("database_name")
LOCAL_BIND_PORT = int(os.getenv("database_port"))
REMOTE_BIND_PORT = int(os.getenv("database_port"))

db = get_database_connection(
    SSH_HOST,
    SSH_PORT,
    SSH_USERNAME,
    SSH_PASSWORD,
    MONGO_HOST,
    MONGO_DB,
    LOCAL_BIND_PORT,
    REMOTE_BIND_PORT,
)
router = APIRouter(prefix="/api/v1/user")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    # db: Session = Depends(get_database_session)
):
    print(token)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        expires = payload.get("exp")
        print("expired token", expires)
        if username is None:
            raise credentials_exception
        # token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = user_find_by_username_repository(db, username=username)

    if user is None:
        raise credentials_exception
    return user


################################## GET ALL SERVER ##################################
@router.post("/login")
async def user_login(
    request: Request,
):

    req_info = await request.json()

    username = req_info["username"]
    password = req_info["password"]

    response = user_login_service(db, username, password)

    return response


@router.post("/register")
async def user_register(
    request: Request,
    current_user: dict = Depends(get_current_user),
    # db: Session = Depends(get_database_session),
):
    req_info = await request.json()

    username = req_info["username"]
    password = req_info["password"]
    region = req_info["region"]

    response = user_register_service(db, username, password, region, current_user)

    return response


################################## GET ALL SERVER ##################################
@router.put("/updatepassword")
async def user_update_password(
    request: Request, current_user: dict = Depends(get_current_user)
):

    req_info = await request.json()

    user_id = req_info["user_id"]
    old_password = req_info["old_password"]
    new_password = req_info["new_password"]

    response = user_update_password_service(
        db, user_id, old_password, new_password, current_user
    )

    return response


@router.put("/resetpassword")
async def user_reset_password(
    request: Request, current_user: dict = Depends(get_current_user)
):

    req_info = await request.json()

    user_id = req_info["user_id"]

    response = user_reset_password_service(db, user_id, current_user)

    return response


@router.put("/resetpassword")
async def user_reset_password(
    request: Request, current_user: dict = Depends(get_current_user)
):

    req_info = await request.json()

    user_id = req_info["user_id"]

    response = user_reset_password_service(db, user_id, current_user)

    return response


@router.get("/me")
async def user_get_detail(current_user: dict = Depends(get_current_user)):

    response = user_get_detail_me_service(db, current_user)

    return response


@router.get("/getdetail")
async def user_get_detail(
    request: Request, current_user: dict = Depends(get_current_user)
):

    req_info = request.query_params

    user_id = req_info["user_id"]

    response = user_get_detail_service(db, user_id, current_user)

    return response


@router.get("/getall")
async def user_get_all(request: Request):
    req_info = request.query_params
    
    page = req_info.get("page")
    limit = req_info.get("limit")
    keyword = req_info.get("q")
    
    page = 1 if page is None else int(page)
    limit = 10 if limit is None else int(limit)
    
    response = user_get_all_service(db, page, limit, keyword)

    return response


################################## GET ALL SERVER ##################################
@router.put("/station")
async def station_add_to_user(
    request: Request, current_user: dict = Depends(get_current_user)
):

    req_info = await request.json()

    user_id = req_info["user_id"]
    station_id = req_info["station_id"]

    response = station_add_to_user_service(db, user_id, station_id)

    return response
