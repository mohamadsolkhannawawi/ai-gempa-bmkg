from repositories.pick_repository import pick_find_all_repository
from repositories.pick_repository import pick_find_by_id_repository
from repositories.pick_repository import pick_update_by_id_repository
from repositories.pick_repository import pick_find_by_station_id_repository

from utils.util import get_response
from utils.util import convert_object_id

from pymongo import database


def pick_get_detail_service(db, pick_id, current_user):

    pick_data = pick_find_by_id_repository(db, pick_id=pick_id)

    if pick_data != None:
        json_str = convert_object_id(pick_data)
        return get_response(True, "get pick detail success", json_str)

    return get_response(False, "cannot get pick detail", None)


def pick_get_by_station_id_service(
    db: database.Database, station_id: str, start_date: str | None, end_date: str | None
):
    pick_datas = pick_find_by_station_id_repository(
        db, station_id, start_date, end_date
    )

    if pick_datas != None:
        datas = []
        for pick_data in pick_datas:
            pick_data = convert_object_id(pick_data)
            datas.append(pick_data)
        return get_response(True, "get pick detail by station success", datas)

    return get_response(False, "cannot get pick detail", None)


def pick_get_all_service(db, current_user):

    pick_datas = pick_find_all_repository(
        db,
    )
    if pick_datas != None:

        # for x in user_datas:
        #     print(x)
        # print()
        datas = []
        for pick_data in pick_datas:
            pick_data = convert_object_id(pick_data)
            datas.append(pick_data)
        return get_response(True, "get pick all success", datas)

    return get_response(False, "cannot get user detail", None)


def pick_update_service(
    db,
    arrival_list,
    event_id,
):

    try:
        # pick_data = pick_find_by_id_repository(db, pick_id=pick_id)

        # if pick_data == None:
        #     return get_response(
        #         False,
        #         "cannot update pick data",
        #         None
        #     )
        # pick_update = pick_update_by_id_repository(
        #     db,
        #     pick_id=pick_id,
        #     timestamp=timestamp,
        #     )

        # if pick_update:
        #     return get_response(
        #         True,
        #         "update pick success",
        #         None
        #     )

        return get_response(False, "update pick failed", None)
    except Exception as e:
        return get_response(False, "update pick failed " + str(e), None)
