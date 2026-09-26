from fastapi import APIRouter, Depends, status, Request, Form, UploadFile, File
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from service.record_stream_service import get_record_stream_api_service
from service.record_stream_service import get_record_stream_kafka_service

#exception and validation
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



origins = ["*"]

SECRET_KEY = "3e8a3f31aab886f8793176988f8298c9265f84b8388c9fef93635b08951f379b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


# Dummy database of users
fake_users_db = {
    "recordstreamtews": {
        "username": "recordstreamtews",
        "hashed_password": pwd_context.hash("recordstreamtews12#"),
    }
}


router = APIRouter(
    prefix ="/api/v1/recordstream"
)

################################## USER GET ALL USER ##################################
@router.get("/get")
async def get_all_open_method(
        request:Request,
        # db: Session = Depends(get_database_session),
        # current_user: User = Depends(get_current_user)
    ):
    params = request.query_params
    print(params)
    year = params["year"]
    network = params["network"]
    station = params["station"]
    location = params["location"]
    channel = params["channel"]
    sds_type = params["sds_type"]
    doy = params["doy"]
    starttime = params["starttime"]
    endtime = params["endtime"]

    response = await get_record_stream_api_service(
        year,
        network,
        station,
        location,
        channel,
        sds_type,
        doy,
        starttime,
        endtime
    )
    return response


