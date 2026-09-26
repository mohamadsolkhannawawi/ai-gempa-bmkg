from fastapi.logger import logger
from repositories.station_repository import station_add_repository
from repositories.station_repository import station_find_all_repository
from repositories.station_repository import station_find_by_id_repository
from repositories.station_repository import station_update_by_id_repository
from repositories.station_repository import station_delete_by_id_repository
from repositories.station_repository import station_update_status_by_id_repository
from repositories.user_repository import user_find_by_id_repository
from repositories.user_repository import user_update_by_id_repository
from pymongo import database

from utils.util import get_response
from utils.util import convert_object_id

from bson.objectid import ObjectId
from obspy import UTCDateTime
from obspy.signal.freqattributes import peak_ground_motion

import os
import numpy as np
import pandas as pd
import obspy
import aioredis
import json
import time


def station_add_service(
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
):

    if current_user["role"] != "superadmin":
        return get_response(False, "cannot add new station", None)

    # user_data = user_find_by_username_repository(db, username)
    # if user_data != None:
    #     return get_response(
    #         False,
    #         "user already exist",
    #         None
    #     )

    # password = get_password_hash(pwd_context, password)
    staion_register_status, station_register_data = station_add_repository(
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
    )

    if staion_register_status:
        return get_response(True, "add station successfully", None)

    return get_response(False, "user register failed", None)


def station_update_service(
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
):

    try:

        if str(current_user["role"]) != "superadmin":
            return get_response(
                False,
                "cannot update station",
                None,
                # user_register_data
            )

        station_data = station_find_by_id_repository(db, station_id=station_id)

        if station_data == None:
            return get_response(False, "cannot update station", None)

        station_update = station_update_by_id_repository(
            db,
            str(station_data["_id"]),
            name,
            code,
            network,
            channel,
            longitude,
            latitude,
            elevation,
            server_seedlink,
            server_fdsn,
        )

        if station_update:
            return get_response(True, "update station success", None)

        return get_response(False, "update station failed", None)
    except Exception as e:
        return get_response(False, "update password failed " + str(e), None)


def station_update_status_service(db, station_id, status, current_user):
    try:
        user_data = user_find_by_id_repository(db, current_user["_id"])
        if user_data == None:
            return get_response(False, "cannot add station to user", None)

        disable_station_datas = []
        if "disable_stations" in user_data:
            disable_station_datas = user_data["disable_stations"]
            if status == "enable":
                if ObjectId(station_id) in disable_station_datas:
                    disable_station_datas.remove(ObjectId(station_id))
            else:
                if ObjectId(station_id) not in disable_station_datas:
                    disable_station_datas.append(ObjectId(station_id))
                    # enable_station_datas.remove(station_data)
        else:
            if status == "disable":
                if ObjectId(station_id) not in disable_station_datas:
                    disable_station_datas.append(ObjectId(station_id))

        user_update = user_update_by_id_repository(
            db,
            str(user_data["_id"]),
            user_data["username"],
            user_data["password"],
            user_data["region"],
            {},
            user_data["stations"],
            disable_station_datas,
        )
        if user_update:
            return get_response(True, "update station status success", None)
        return get_response(False, "update station status failed", None)
    except Exception as e:
        return get_response(False, "update station status failed " + str(e), None)


def station_get_detail_service(db, station_id, current_user):

    station_data = station_find_by_id_repository(db, station_id=station_id)

    if station_data != None:
        json_str = convert_object_id(station_data)
        return get_response(True, "get station detail success", json_str)

    return get_response(False, "cannot get station detail", None)


async def station_get_waveform_stats_service(db, station_id):
    # Define channel priorities
    VELOCITY_CHANNEL_PRIORITY = ["BHZ", "SHZ"]

    station_data = station_find_by_id_repository(db, station_id=station_id)

    if station_data != None:
        json_str = convert_object_id(station_data)

        # Get valid channel while maintaining channel priority using set operation
        valid_channel = list(
            set(VELOCITY_CHANNEL_PRIORITY).intersection(json_str.get("channel", []))
        )

        if valid_channel == []:
            return get_response(False, "no valid channel detected", None)

        # Connect to redis
        try:
            redis_host = os.getenv("redis_host", "localhost")
            redis_port = int(os.getenv("redis_port", 6379))
            redis_client = aioredis.from_url(
                f"redis://{redis_host}:{redis_port}", decode_responses=True
            )
        except Exception:
            return get_response(False, "server error: failed to connect to redis", None)

        # == Redis data fetching
        # Fetch data from redis
        valid_channel = valid_channel[0]
        station_key = f"{station_data['network']}.{station_data['code']}.{station_data['location']}.{valid_channel}"
        current_timestamp = int(time.time())
        messages = await redis_client.lrange(
            f"{station_key}_history", 0, 6000
        )  # Limit to the last 100 messages

        # Parse JSON strings efficiently
        data_list = json.loads(
            "[" + ",".join(messages) + "]"
        )  # Join messages and parse as a list

        # Create DataFrame directly from the list of dictionaries
        df = pd.DataFrame(data_list)

        if df.empty:
            return get_response(
                False,
                "cannot get station waveform detail: waveform data unavailable",
                None,
            )

        # Filter valid data
        df["expiration_timestamp"] = pd.to_numeric(
            df["expiration_timestamp"], errors="coerce"
        )
        valid_df = df[df["expiration_timestamp"] > current_timestamp]
        waveform_values = np.concatenate(valid_df["waveform"].values)

        # == Calculate waveform statitics
        delay_second = UTCDateTime.now() - UTCDateTime(valid_df.iloc[-1]["endtime"])
        spike_amplitude = max(waveform_values)
        pga, displacement, velocity, acceleration = peak_ground_motion(
            waveform_values,
            valid_df.iloc[0]["delta"],
            valid_df.iloc[0]["sampling_rate"],
        )

        waveform_stats_dict = {
            "delay_second": delay_second,
            "spike_amplitude": spike_amplitude,
            "displacement": displacement,
            "velocity": velocity,
            "acceleration": acceleration,
        }

        return get_response(
            True, "get station detail success", {**json_str, **waveform_stats_dict}
        )

    return get_response(False, "cannot get station waveform detail", None)


def station_get_all_service(db: database.Database, current_user, page: int | None, limit: int | None, keyword: str | None):
    station_ids = None if current_user["role"] == "superadmin" else current_user["stations"]
    station_datas, total = station_find_all_repository(db, page, limit, keyword, station_ids)

    if station_datas != None:
        datas = []
        for station_data in station_datas:
            station_data = convert_object_id(station_data)
            datas.append(station_data)
        return get_response(True, "get station all success", {
            "stations": datas,
            "total": total
        })

    return get_response(False, "cannot get station detail", None)


def station_get_all_by_status_service(db, station_status, current_user):
    if current_user["role"] == "superadmin":

        station_datas = station_find_all_repository(
            db,
        )
        if station_datas != None:

            # for x in user_datas:
            #     print(x)
            # print()
            datas = []
            for station_data in station_datas:
                station_data = convert_object_id(station_data)
                if "status" in station_data:
                    if station_data["status"] == station_status:
                        datas.append(station_data)
            return get_response(True, "get station all success", datas)

    else:
        station_ids = current_user["stations"]

        station_datas = []

        for station_id in station_ids:
            station_data = station_find_by_id_repository(db, station_id=station_id)

            if station_data != None:
                station_data = convert_object_id(station_data)
                if "status" in station_data:
                    if station_data["status"] == station_status:
                        datas.append(station_data)
        return get_response(True, "get station all success", station_datas)

    return get_response(False, "cannot get station detail", None)


def station_add_to_user_service(db, user_id, station_ids):
    user_data = user_find_by_id_repository(db, user_id)
    if user_data == None:
        return get_response(False, "cannot add station to user", None)
    station_ids = [ObjectId(s) for s in station_ids]
    user_update = user_update_by_id_repository(
        db,
        str(user_data["_id"]),
        user_data["username"],
        user_data["password"],
        user_data["region"],
        user_data["modules"],
        station_ids,
    )

    if user_update:
        return get_response(True, "add station to user success", None)

    return get_response(False, "add station to user failed", None)


def station_delete_service(db, station_id, current_user):

    if current_user["role"] != "superadmin":
        return get_response(False, "delete station failed", None)

    station_data = station_delete_by_id_repository(db, station_id=station_id)

    if station_data != None:
        return get_response(True, "delete station success", None)

    return get_response(False, "delete station detail", None)
