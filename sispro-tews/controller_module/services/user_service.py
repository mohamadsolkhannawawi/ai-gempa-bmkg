from repositories.user_repository import user_register_repository
from repositories.user_repository import user_find_by_username_repository
from repositories.user_repository import user_find_by_id_repository
from repositories.user_repository import user_update_by_id_repository
from repositories.user_repository import user_find_all_repository
from utils.util import get_response
from utils.util import verify_password
from utils.util import convert_object_id

from passlib.context import CryptContext
from utils.util import get_password_hash
from utils.util import verify_password
from datetime import datetime, timedelta
from pymongo import database

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


def user_login_service(db, username, password):

    user_data = user_find_by_username_repository(db, username)
    if user_data == None:
        return get_response(False, "please check your credentials", None)
    if not verify_password(pwd_context, password, user_data["password"]):
        return get_response(False, "please check your credentials", None)

    access_token = create_access_token(
        data={"sub": user_data["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    user_login_data = {
        "id": str(user_data["_id"]),
        "username": user_data["username"],
        "region": user_data["region"],
        "access_token": access_token,
    }
    return get_response(True, "user login successfully", user_login_data)


def user_register_service(db, username, password, region, current_user):

    if current_user["role"] != "superadmin":
        return get_response(
            False,
            "cannot register new user",
            None,
            # user_register_data
        )

    user_data = user_find_by_username_repository(db, username)
    if user_data != None:
        return get_response(False, "user already exist", None)

    password = get_password_hash(pwd_context, password)
    user_register_status, user_register_data = user_register_repository(
        db, username, password, region
    )

    if user_register_status:
        return get_response(
            True,
            "user register successfully",
            None,
            # user_register_data
        )

    return get_response(False, "user register failed", None)


def user_update_password_service(db, user_id, old_password, new_password, current_user):

    try:

        if str(current_user["_id"]) != user_id:
            return get_response(
                False,
                "cannot update password",
                None,
                # user_register_data
            )

        user_data = user_find_by_id_repository(db, user_id=user_id)

        if user_data == None:
            return get_response(False, "cannot update password", None)

        if not verify_password(pwd_context, old_password, user_data["password"]):
            return get_response(False, "please check your credentials", None)

        new_password = get_password_hash(pwd_context, new_password)
        user_update = user_update_by_id_repository(
            db,
            str(user_data["_id"]),
            user_data["username"],
            new_password,
            user_data["region"],
            user_data["modules"],
            user_data["stations"],
            user_data["disable_stations"],
        )

        if user_update:
            return get_response(True, "update password success", None)

        return get_response(False, "update password failed", None)
    except Exception as e:
        return get_response(False, "update password failed " + str(e), None)


def user_reset_password_service(db, user_id, current_user):

    try:

        if str(current_user["role"]) != "superadmin":
            return get_response(
                False,
                "cannot reset password",
                None,
                # user_register_data
            )

        user_data = user_find_by_id_repository(db, user_id=user_id)

        if user_data == None:
            return get_response(False, "cannot reset password", None)

        new_password = get_password_hash(pwd_context, "sispro123#")
        user_update = user_update_by_id_repository(
            db,
            str(user_data["_id"]),
            user_data["username"],
            new_password,
            user_data["region"],
            user_data["modules"],
            user_data["stations"],
            user_data["disable_stations"],
        )

        if user_update:
            return get_response(True, "reset password success", None)

        return get_response(False, "reset password failed", None)
    except Exception as e:
        return get_response(False, "reset password failed " + str(e), None)


def user_get_detail_me_service(db, current_user):

    user_data = user_find_by_id_repository(db, user_id=str(current_user["_id"]))

    if user_data != None:
        json_str = convert_object_id(user_data)
        json_str["password"] = ""
        del json_str["password"]
        return get_response(True, "get user detail success", json_str)

    return get_response(False, "cannot get user detail", None)


def user_get_detail_service(db, user_id, current_user):

    if str(current_user["role"]) != "superadmin":
        return get_response(
            False,
            "cannot get user",
            None,
            # user_register_data
        )

    user_data = user_find_by_id_repository(db, user_id=user_id)

    if user_data != None:
        json_str = convert_object_id(user_data)
        json_str["password"] = ""
        del json_str["password"]
        return get_response(True, "get user detail success", json_str)

    return get_response(False, "cannot get user detail", None)


def user_get_all_service(db: database.Database, page: int, limit: int, keyword: str | None):
    user_datas, total = user_find_all_repository(db, page, limit, keyword)

    if user_datas != None:
        datas = []
        for user_data in user_datas:
            user_data = convert_object_id(user_data)
            user_data["password"] = ""
            del user_data["password"]
            datas.append(user_data)
        return get_response(
            True, "get user all success", {"users": datas, "total": total}
        )
    return get_response(False, "cannot get user detail", None)
