from fastapi import FastAPI, Depends, File, Form, UploadFile, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError, FastAPIError, HTTPException, WebSocketRequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.concurrency import iterate_in_threadpool
from passlib.context import CryptContext
from datetime import date,timedelta
from dotenv import load_dotenv
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from utils.util import my_random_string

import route.record_stream_route

import uvicorn
import datetime
import time
import logging


load_dotenv()
app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# User.Base.metadata.create_all(bind=engine)
# T24Forecast.Base.metadata.create_all(bind=engine)
# User.Base.metadata.create_all(bind=engine)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(route.record_stream_route.router)


SECRET_KEY = "3e8a3f31aab886f8793176988f8298c9265f84b8388c9fef93635b08951f379b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


@app.exception_handler(WebSocketRequestValidationError)
async def validation_exception_handler(request: Request, exc: WebSocketRequestValidationError):
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"success": False,
            "code": 404,
            "message" : str(exc.detail),
        }),
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder({"success": False,
            "code": 404,
            "message" : str(exc.detail),
        }),
    )

@app.exception_handler(500)
async def internal_server_error(request: Request, exc: Exception):

    return JSONResponse(
        status_code=500,
        content=jsonable_encoder({"success": False,
            "code": 404,
            "message" : str(exc),
        }),
    )

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response_body = [chunk async for chunk in response.body_iterator]
    response.body_iterator = iterate_in_threadpool(iter(response_body))

    today = date.today()
    today_date = today.strftime("%d-%b-%Y")
    trace_id = my_random_string()
    log = "\n"+ str(datetime.datetime.now()) +" Request "+trace_id+" : "+ request.url._url+", "+request.method+", "+ request.client.host+ ", "+request.headers.get('User-Agent')
    log += "\n"+ str(datetime.datetime.now()) +" Response "+trace_id+" : "+ response_body[0].decode()
    log += "\n"+ str(datetime.datetime.now()) +" Response Time "+trace_id+" : "+ str(int(process_time*1000))+"\n"
    # log += "\nTimestamp "+trace_id+" : "+ str(datetime.datetime.now())+"\n"
    logging.basicConfig(filename="./logs/logs_record_stream_module_"+str(today_date)+".log", level=logging.INFO)
    # logging.info(log)

  
    return response


@app.get("/")
async def hello_world():
    return {"message": "Hello, this is record stream module backend!"}


#executor main
if __name__ == "__main__":
    # uvicorn.run(app, host="127.0.0.1", port=9090)
    uvicorn.run('main:app', reload=True, port=9090)