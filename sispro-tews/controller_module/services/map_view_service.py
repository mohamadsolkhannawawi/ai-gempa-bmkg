from repositories.map_view_repository import map_view_add_repository
from repositories.map_view_repository import map_view_find_all_repository
from repositories.map_view_repository import map_view_find_by_id_repository
from repositories.map_view_repository import map_view_update_by_id_repository
from repositories.map_view_repository import map_view_delete_by_id_repository

from repositories.user_repository import user_find_by_id_repository
from repositories.user_repository import user_update_by_id_repository

from utils.util import get_response
from utils.util import convert_object_id

import geopandas as gpd

def map_view_add_service(
        db,
        map_view_name, 
        map_view_type,
        map_view_type_data,
        value,
        current_user):
    
    if current_user["role"] != "superadmin":
        return get_response(
            False,
            "cannot add new map_view",
            None
        )
    
    # user_data = user_find_by_username_repository(db, username)
    # if user_data != None:
    #     return get_response(
    #         False,
    #         "user already exist",
    #         None
    #     
    # )
    # Load the Shapefile
    gdf = gpd.read_file(value.file)

    # Convert to GeoJSON
    geojson = gdf.to_json()
    # password = get_password_hash(pwd_context, password)
    map_view_register_status, map_view_register_data = map_view_add_repository(
        db,
        map_view_name, 
        map_view_type,
        map_view_type_data,
        geojson,)

    if map_view_register_status:
        return get_response(
            True,
            "add map_view successfully",
            None
        )
    
    return get_response(
        False,
        "user register failed",
        None
    )

def map_view_update_service(
        db, 
        map_view_id,
        map_view_name, 
        map_view_type,
        map_view_type_data,
        value,
        current_user
    ):

    try:

        if str(current_user["role"] )!= "superadmin":
            return get_response(
                False,
                "cannot update map_view",
                None
                    # user_register_data
            )
        
        map_view_data = map_view_find_by_id_repository(db, map_view_id=map_view_id)

        if map_view_data == None:
            return get_response(
                False,
                "cannot update map_view",
                None
            )
        
        gdf = gpd.read_file(value.file)

        # Convert to GeoJSON
        geojson = gdf.to_json()
        
        
        map_view_update = map_view_update_by_id_repository(
                db, 
                str(map_view_data["_id"]),
                map_view_name, 
                map_view_type,
                map_view_type_data,
                geojson,
            )

        if map_view_update:
            return get_response(
                True,
                "update map_view success",
                None
            )
        
        return get_response(
            False,
            "update map_view failed",
            None
        )
    except Exception as e:
        return get_response(
            False,
            "update password failed "+str(e),
            None
        )
    
def map_view_get_detail_service(
        db, 
        map_view_id,
        current_user
    ):
        
    map_view_data = map_view_find_by_id_repository(db, map_view_id=map_view_id)
    
    if map_view_data != None:
        json_str = convert_object_id(map_view_data)
        return get_response(
            True,
            "get map_view detail success",
            json_str
        )
    
    return get_response(
        False,
        "cannot get map_view detail",
        None
    )

def map_view_get_all_service(
        db, 
        current_user
    ):

    if current_user["role"] != "superadmin":
        return get_response(
            False,
            "get map_view all failed",
            None
        )
    map_view_datas = map_view_find_all_repository(db,)
    if map_view_datas != None:

        # for x in user_datas:
        #     print(x)
        # print()
        datas = []
        for map_view_data in map_view_datas:
            map_view_data = convert_object_id(map_view_data)
            datas.append(map_view_data)
        return get_response(
            True,
            "get map_view all success",
            datas
        )
    
    return get_response(
        False,
        "cannot get user detail",
        None
    )

def map_view_delete_service(
        db, 
        map_view_id,
        current_user
    ):

    if current_user["role"] != "superadmin":
        return get_response(
            False,
            "delete map_view failed",
            None
        )
        
    map_view_data = map_view_delete_by_id_repository(db, map_view_id=map_view_id)
    
    if map_view_data != None:
        return get_response(
            True,
            "delete map_view success",
            None
        )
    
    return get_response(
        False,
        "delete map_view detail",
        None
    )
