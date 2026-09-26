from bson.objectid import ObjectId
from pymongo import database


def get_wadati_data_repo(
    db,
    origin_id
):
    origin_collection = db["origin"]
    arrival_collection = db["arrival"]
    
    pipeline = [
    # Match the specific origin document using _id
        {
            "$match": {
                "_id": ObjectId(origin_id)
            }
        },
        # Lookup stage to join with the arrival collection
        {
            "$lookup": {
                "from": "arrival",
                "localField": "arrival_ids",
                "foreignField": "_id",
                "as": "arrivals"
            }
        },
        # Unwind the arrivals array so we can lookup station information for each arrival
        {
            "$unwind": {
                "path": "$arrivals",
                "preserveNullAndEmptyArrays": True  # In case some arrivals do not match
            }
        },
        # Lookup stage to join with the station collection for each arrival
        {
            "$lookup": {
                "from": "station",
                "localField": "arrivals.station_id",
                "foreignField": "_id",
                "as": "arrivals.station"
            }
        },
        # Unwind the station array to simplify the nested data structure
        {
            "$unwind": {
                "path": "$arrivals.station",
                "preserveNullAndEmptyArrays": True  # In case some stations do not match
            }
        },
        # Group back the arrivals array to create a structured output
        {
            "$group": {
                "_id": "$_id",
                "name": {"$first": "$name"},
                "origin_time": {"$first": "$origin_time"},
                "longitude": {"$first": "$longitude"},
                "latitude": {"$first": "$latitude"},
                "depth": {"$first": "$depth"},
                "region": {"$first": "$region"},
                "sub_region": {"$first": "$sub_region"},
                "country": {"$first": "$country"},
                "arrivals": {"$push": "$arrivals"},
                # Include other fields as needed
            }
        }
    ]

    # Run the aggregation pipeline
    result = list(origin_collection.aggregate(pipeline))
    
    return result

