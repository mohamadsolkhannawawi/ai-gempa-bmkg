
from repositories.cluster_repository import cluster_find_all_repository
from repositories.cluster_repository import cluster_find_by_id_repository
from repositories.cluster_repository import cluster_update_by_id_repository

from utils.util import get_response
from utils.util import convert_object_id

from bson.objectid import ObjectId
    
def cluster_get_detail_service(
        db, 
        cluster_id,
        current_user
    ):
        
    cluster_data = cluster_find_by_id_repository(db, cluster_id=cluster_id)
    
    if cluster_data != None:
        json_str = convert_object_id(cluster_data)
        return get_response(
            True,
            "get cluster detail success",
            json_str
        )
    
    return get_response(
        False,
        "cannot get cluster detail",
        None
    )

def cluster_get_all_service(
        db, 
        current_user
    ):

 
    cluster_datas = cluster_find_all_repository(db,)
    if cluster_datas != None:

        # for x in user_datas:
        #     print(x)
        # print()
        datas = []
        for cluster_data in cluster_datas:
            cluster_data = convert_object_id(cluster_data)
            datas.append(cluster_data)
        return get_response(
            True,
            "get cluster all success",
            datas
        )
    
    return get_response(
        False,
        "cannot get user detail",
        None
    )


def cluster_update_service(
        db, 
        cluster_id,
        origin_time, 
    ):

    try:

    
        
        cluster_data = cluster_find_by_id_repository(db, cluster_id=cluster_id)

        if cluster_data == None:
            return get_response(
                False,
                "cannot update cluster data",
                None
            )
        cluster_update = cluster_update_by_id_repository(
            db, 
            cluster_id=cluster_id,
            origin_time=origin_time,
            )

        if cluster_update:
            return get_response(
                True,
                "update cluster success",
                None
            )
        
        return get_response(
            False,
            "update cluster failed",
            None
        )
    except Exception as e:
        return get_response(
            False,
            "update cluster failed "+str(e),
            None
        )