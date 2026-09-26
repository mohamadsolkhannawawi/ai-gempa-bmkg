from repositories.arrival_repository import arrival_find_all_repository
from repositories.arrival_repository import arrival_find_by_id_repository
from repositories.arrival_repository import arrival_update_by_id_repository
from repositories.arrival_repository import arrival_find_by_station_repository

from utils.util import get_response
from utils.util import convert_object_id
from pymongo import database

from bson.objectid import ObjectId


def arrival_get_detail_service(db, arrival_id, current_user):

    arrival_data = arrival_find_by_id_repository(db, arrival_id=arrival_id)

    if arrival_data != None:
        json_str = convert_object_id(arrival_data)
        return get_response(True, "get arrival detail success", json_str)

    return get_response(False, "cannot get arrival detail", None)


def arrival_get_by_station_service(
    db: database.Database,
    station_id: str,
    start_date: str | None,
    end_date: str | None,
):
    arrival_datas = arrival_find_by_station_repository(
        db, station_id, start_date, end_date
    )

    if arrival_datas != None:
        datas = []
        for arrival_data in arrival_datas:
            arrival_data = convert_object_id(arrival_data)
            datas.append(arrival_data)
        return get_response(True, "get arrival detail success", datas)
    return get_response(False, "cannot get arrival detail", None)


def arrival_get_all_service(db, current_user):

    arrival_datas = arrival_find_all_repository(
        db,
    )
    if arrival_datas != None:

        # for x in user_datas:
        #     print(x)
        # print()
        datas = []
        for arrival_data in arrival_datas:
            arrival_data = convert_object_id(arrival_data)
            datas.append(arrival_data)
        return get_response(True, "get arrival all success", datas)

    return get_response(False, "cannot get user detail", None)


def arrival_update_service(
    db,
    arrival_id,
    timestamp,
):

    try:

        arrival_data = arrival_find_by_id_repository(db, arrival_id=arrival_id)

        if arrival_data == None:
            return get_response(False, "cannot update arrival data", None)
        arrival_update = arrival_update_by_id_repository(
            db,
            arrival_id=arrival_id,
            timestamp=timestamp,
        )

        if arrival_update:
            return get_response(True, "update arrival success", None)

        return get_response(False, "update arrival failed", None)
    except Exception as e:
        return get_response(False, "update arrival failed " + str(e), None)
