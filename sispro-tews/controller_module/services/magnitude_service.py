
from repositories.magnitude_repository import magnitude_find_all_repository
from repositories.magnitude_repository import magnitude_find_by_id_repository

from utils.util import get_response
from utils.util import convert_object_id

from bson.objectid import ObjectId
    
def magnitude_get_detail_service(
        db, 
        magnitude_id,
        current_user
    ):
        
    magnitude_data = magnitude_find_by_id_repository(db, magnitude_id=magnitude_id)
    
    if magnitude_data != None:
        json_str = convert_object_id(magnitude_data)
        return get_response(
            True,
            "get magnitude detail success",
            json_str
        )
    
    return get_response(
        False,
        "cannot get magnitude detail",
        None
    )

def magnitude_get_all_service(
        db, 
        current_user
    ):

    magnitude_datas = magnitude_find_all_repository(db,)
    if magnitude_datas != None:

        # for x in user_datas:
        #     print(x)
        # print()
        datas = []
        for magnitude_data in magnitude_datas:
            magnitude_data = convert_object_id(magnitude_data)
            datas.append(magnitude_data)
        return get_response(
            True,
            "get magnitude all success",
            datas
        )
    
    return get_response(
        False,
        "cannot get user detail",
        None
    )