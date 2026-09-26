from fastapi import APIRouter, Depends, status, Request, File, Form, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from configuration.database import get_database_connection
from dotenv import load_dotenv
from services.station_service import station_add_service
from services.station_service import station_get_all_service
from services.station_service import station_get_detail_service
from services.station_service import station_update_service
from services.station_service import station_get_waveform_stats_service

from services.station_service import station_get_all_by_status_service
from services.station_service import station_update_status_service
from services.station_service import station_delete_service
from repositories.user_repository import user_find_by_username_repository
import os

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
router = APIRouter(prefix="/api/v1/station")


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
@router.post("/add")
async def station_add(request: Request, current_user: dict = Depends(get_current_user)):

    req_info = await request.json()

    name = req_info["name"]
    code = req_info["code"]
    network = req_info["network"]
    channel = req_info["channel"]
    longitude = req_info["longitude"]
    latitude = req_info["latitude"]
    elevation = req_info["elevation"]
    server_seedlink = req_info["server_seedlink"]
    server_fdsn = req_info["server_fdsn"]

    response = station_add_service(
        db,
        name,
        code,
        network,
        channel,
        longitude,
        latitude,
        elevation,
        server_seedlink,
        server_fdsn,
        current_user,
    )

    return response


@router.get("/getdetail")
async def station_get_by_detail(
    request: Request,
    current_user: dict = Depends(get_current_user),
    # db: Session = Depends(get_database_session),
):
    req_info = request.query_params

    station_id = req_info["station_id"]

    response = station_get_detail_service(db, station_id, current_user)

    return response


@router.delete("/delete")
async def station_delete(
    request: Request,
    current_user: dict = Depends(get_current_user),
    # db: Session = Depends(get_database_session),
):
    req_info = request.query_params

    station_id = req_info["station_id"]

    response = station_delete_service(db, station_id, current_user)

    return response


@router.get("/getwaveformstatus")
async def station_get_waveform_stats(
    request: Request,
    current_user: dict = Depends(get_current_user),
    # db: Session = Depends(get_database_session),
):
    req_info = request.query_params

    station_id = req_info["station_id"]

    response = await station_get_waveform_stats_service(db, station_id)

    return response


@router.get("/getall")
async def station_get_all(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    req_info = request.query_params
    
    page = req_info.get("page")
    limit = req_info.get("limit")
    keyword = req_info.get("q")
    
    if page != None:
        page = int(page)
    if limit != None:
        limit = int(limit)
    
    response = station_get_all_service(db, current_user, page, limit, keyword)

    return response


@router.get("/getallbystatus")
async def station_get_all_by_status(
    request: Request,
    current_user: dict = Depends(get_current_user),
    # db: Session = Depends(get_database_session),
):
    req_info = request.query_params
    station_status = req_info["station_status"]

    response = station_get_all_by_status_service(db, station_status, current_user)

    return response


################################## GET ALL SERVER ##################################
@router.put("/update")
async def station_update(
    request: Request, current_user: dict = Depends(get_current_user)
):

    req_info = await request.json()

    station_id = req_info["station_id"]
    name = req_info["name"]
    code = req_info["code"]
    network = req_info["network"]
    channel = req_info["channel"]
    longitude = req_info["longitude"]
    latitude = req_info["latitude"]
    elevation = req_info["elevation"]
    server_seedlink = req_info["server_seedlink"]
    server_fdsn = req_info["server_fdsn"]

    response = station_update_service(
        db,
        station_id,
        name,
        code,
        network,
        channel,
        longitude,
        latitude,
        elevation,
        server_seedlink,
        server_fdsn,
        current_user,
    )

    return response


################################## GET ALL SERVER ##################################
@router.put("/updatestatus")
async def station_update_status(
    request: Request, current_user: dict = Depends(get_current_user)
):

    req_info = await request.json()

    station_id = req_info["station_id"]
    status = req_info["status"]
    response = station_update_status_service(db, station_id, status, current_user)

    return response
