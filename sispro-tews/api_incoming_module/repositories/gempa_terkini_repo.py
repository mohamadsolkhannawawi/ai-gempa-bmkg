



def get_gempa_terkini_repo(db):
  
    event_data = db.event.aggregate([
        {
            "$lookup": {
                "from": "origin",
                "localField": "preferred_origin_id",
                "foreignField": "_id",
                "as": "origin_data"
            }
        },
        {
            "$unwind": "$origin_data"
        },
        {
            "$sort": {
                "origin_data.origin_time": -1
            }
        },
        {
            "$lookup": {
                "from": "magnitude",
                "localField": "origin_data.magnitude_ids",
                "foreignField": "_id",
                "as": "magnitude_data"
            }
        },
        {
            "$unwind": "$magnitude_data"
        },
        {
            "$match": {
                "magnitude_data.value": { "$gt": 5.0 },
                "magnitude_data.type": "MLv"
            }
        },
        {
            "$limit": 15
        },
    
        # {
        #     "$project": {
        #         "_id": 0,
        #         "event_id": "$_id",
        #         "origin_time": "$origin_data.origin_time",
        #         "magnitude_id": "$magnitude_data._id",
        #         "magnitude_value": "$magnitude_data.value",
        #         "magnitude_type": "$magnitude_data.type"
        #     }
        # }
    ])



    return event_data