

from repositories.config_repository import config_create_repository
from repositories.config_repository import config_by_name_repository
from repositories.config_repository import config_find_all_repository
from repositories.config_repository import config_update_by_id_repository

from utils.util import get_response
from utils.util import verify_password
from utils.util import convert_object_id

from passlib.context import CryptContext
from utils.util import get_password_hash
from utils.util import verify_password
from datetime import datetime, timedelta


from jose import jwt, JWTError

from datetime import datetime, timedelta
import json
# run the following on terminal to generate a secret key
# openssl rand -hex 32
SECRET_KEY = "3e8a3f31aab886f8793176988f8298c9265f84b8388c9fef93635b08951f379b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def config_create_service(
        db,
        name, config_value, type_data, current_user):
    
    try:
        config_create_status, config_create_data = config_create_repository(
            db,
            name,
            config_value,
            type_data,)

        if config_create_status:
            return get_response(
                True,
                "config create successfully",None
                # user_register_data
            )
        
        return get_response(
            False,
            "user register failed",
            None
        )
    except Exception as e:
        return get_response(
            False,
            str(e),
            None
        )
    
def config_get_by_name_service(
    db,
    name,current_user):
    try:
        config_data = config_by_name_repository(db, name)
        
        if config_data != None:
            json_str = convert_object_id(config_data)
        
            return get_response(
                True,
                "get config success",
                json_str
            )
        
        return get_response(
            False,
            "cannot get config",
            None
        )
    except Exception as e:
        return get_response(
            False,
            str(e),
            None
        )
def config_get_by_all_service(
    db,current_user):
    
    try:
        config_datas = config_find_all_repository(db,)
        if config_datas != None:
            datas = []
            for config_data in config_datas:
                config_data = convert_object_id(config_data)
                datas.append(config_data)
            return get_response(
                True,
                "get config data all success",
                datas
            )
        
        return get_response(
            False,
            "cannot get config all",
            None
        )
    except Exception as e:
        return get_response(
            False,
            str(e),
            None
        )
    
def config_update_service(
    db,
    config_id, 
    name, 
    config_value, 
    type_data,current_user):
    
    try:
        config_datas = config_update_by_id_repository(
            db,
            config_id, 
            name, 
            config_value, 
            type_data,)
        
        if config_datas != None:
            
            return get_response(
                True,
                "update config data success",
                
            )
        
        return get_response(
            False,
            "cannot get config all",
            None
        )
    except Exception as e:
        return get_response(
            False,
            str(e),
            None
        )