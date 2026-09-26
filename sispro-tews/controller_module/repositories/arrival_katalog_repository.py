from bson.objectid import ObjectId
from pymongo import database


def get_arrival_katalog_repo(
    db,
    origin_id
):
    origin_collection = db["origin"]
    arrival_collection = db["arrival"]
    
    # pipeline = [
    # # Match the specific origin document using _id
    #     {
    #         "$match": {
    #             "_id": ObjectId(origin_id)
    #         }
    #     },
    #     # Lookup stage to join with the arrival collection
    #     {
    #         "$lookup": {
    #             "from": "magnitude",
    #             "localField": "magnitude_ids",
    #             "foreignField": "_id",
    #             "as": "magnitudes"
    #         }
    #     },
    #     #  {
    #     #     "$unwind": {
    #     #         "path": "$magnitudes",
    #     #         "preserveNullAndEmptyArrays": True  # In case some arrivals do not match
    #     #     }
    #     # },
    #     {
    #         "$lookup": {
    #             "from": "arrival",
    #             "localField": "arrival_ids",
    #             "foreignField": "_id",
    #             "as": "arrivals"
    #         }
    #     },
    #     # Unwind the arrivals array so we can lookup station information for each arrival
    #     {
    #         "$unwind": {
    #             "path": "$arrivals",
    #             "preserveNullAndEmptyArrays": True  # In case some arrivals do not match
    #         }
    #     },
    #     # Lookup stage to join with the station collection for each arrival
    #     {
    #         "$lookup": {
    #             "from": "station",
    #             "localField": "arrivals.station_id",
    #             "foreignField": "_id",
    #             "as": "arrivals.station"
    #         }
    #     },
    #     # Unwind the station array to simplify the nested data structure
    #     {
    #         "$unwind": {
    #             "path": "$arrivals.station",
    #             "preserveNullAndEmptyArrays": True  # In case some stations do not match
    #         }
    #     },
    #     # Group back the arrivals array to create a structured output
    #     {
    #         "$group": {
    #             "_id": "$_id",
    #             "name": {"$first": "$name"},
    #             "origin_time": {"$first": "$origin_time"},
    #             "longitude": {"$first": "$longitude"},
    #             "latitude": {"$first": "$latitude"},
    #             "depth": {"$first": "$depth"},
    #             "region": {"$first": "$region"},
    #             "sub_region": {"$first": "$sub_region"},
    #             "country": {"$first": "$country"},
    #             "magnitudes": {"$push": "$magnitudes"},
    #             "arrivals": {"$push": "$arrivals"},
    #             # Include other fields as needed
    #         }
    #     }
    # ]

    # pipeline = [
    #     # Filter dokumen asal berdasarkan _id
    #     {
    #         "$match": {
    #             "_id": ObjectId(origin_id)
    #         }
    #     },
    #     # Join dengan collection magnitude
    #     {
    #         "$lookup": {
    #             "from": "magnitude",
    #             "localField": "magnitude_ids",
    #             "foreignField": "_id",
    #             "as": "magnitudes"
    #         }
    #     },
    #     # Join dengan collection arrival
    #     {
    #         "$lookup": {
    #             "from": "arrival",
    #             "localField": "arrival_ids",
    #             "foreignField": "_id",
    #             "as": "arrivals"
    #         }
    #     },
    #     # Unwind array arrivals agar dapat dilakukan lookup ke station untuk tiap arrival
    #     {
    #         "$unwind": {
    #             "path": "$arrivals",
    #             "preserveNullAndEmptyArrays": True
    #         }
    #     },
    #     # Join dengan collection station berdasarkan station_id pada arrival
    #     {
    #         "$lookup": {
    #             "from": "station",
    #             "localField": "arrivals.station_id",
    #             "foreignField": "_id",
    #             "as": "arrivals.station"
    #         }
    #     },
    #     # Unwind array station untuk menyederhanakan struktur data
    #     {
    #         "$unwind": {
    #             "path": "$arrivals.station",
    #             "preserveNullAndEmptyArrays": True
    #         }
    #     },
    #     # Group kembali untuk membentuk output akhir, gunakan $first untuk menghindari duplikasi pada magnitudes
    #     {
    #         "$group": {
    #             "_id": "$_id",
    #             "name": {"$first": "$name"},
    #             "origin_time": {"$first": "$origin_time"},
    #             "longitude": {"$first": "$longitude"},
    #             "latitude": {"$first": "$latitude"},
    #             "depth": {"$first": "$depth"},
    #             "region": {"$first": "$region"},
    #             "sub_region": {"$first": "$sub_region"},
    #             "country": {"$first": "$country"},
    #             "magnitudes": {"$first": "$magnitudes"},
    #             "arrivals": {"$push": "$arrivals"}
    #         }
    #     }
    # ]

    pipeline = [
        # Filter dokumen asal berdasarkan _id
        {
            "$match": {
                "_id": ObjectId(origin_id)
            }
        },
        # Join dengan collection magnitude
        {
            "$lookup": {
                "from": "magnitude",
                "localField": "magnitude_ids",
                "foreignField": "_id",
                "as": "magnitudes"
            }
        },
        # Join dengan collection arrival
        {
            "$lookup": {
                "from": "arrival",
                "localField": "arrival_ids",
                "foreignField": "_id",
                "as": "arrivals"
            }
        },
        # Unwind array arrivals agar dapat dilakukan lookup ke station untuk tiap arrival
        {
            "$unwind": {
                "path": "$arrivals",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Join dengan collection station berdasarkan station_id pada arrival
        {
            "$lookup": {
                "from": "station",
                "localField": "arrivals.station_id",
                "foreignField": "_id",
                "as": "arrivals.station"
            }
        },
        # Unwind array station untuk menyederhanakan struktur data
        {
            "$unwind": {
                "path": "$arrivals.station",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Unwind array station_magnitude_ids_per_type untuk lookup ke station_magnitude
        {
            "$unwind": {
                "path": "$station_magnitude_ids_per_type",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Lookup ke station_magnitude menggunakan station_magnitude_ids_per_type.station_magnitude_ids
        {
            "$lookup": {
                "from": "station_magnitude",
                "localField": "station_magnitude_ids_per_type.station_magnitude_ids",
                "foreignField": "_id",
                "as": "station_magnitudes"
            }
        },
        # Unwind station_magnitudes agar bisa lookup ke station dan pick
        {
            "$unwind": {
                "path": "$station_magnitudes",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Lookup ke station menggunakan station_id dari station_magnitude
        {
            "$lookup": {
                "from": "station",
                "localField": "station_magnitudes.station_id",
                "foreignField": "_id",
                "as": "station_magnitudes.station"
            }
        },
        # Unwind station agar tidak nested
        {
            "$unwind": {
                "path": "$station_magnitudes.station",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Lookup ke pick menggunakan pick_source_id dari station_magnitude
        {
            "$lookup": {
                "from": "pick",
                "localField": "station_magnitudes.pick_source_id",
                "foreignField": "_id",
                "as": "station_magnitudes.pick"
            }
        },
        # Unwind pick agar tidak nested
        {
            "$unwind": {
                "path": "$station_magnitudes.pick",
                "preserveNullAndEmptyArrays": True
            }
        },
        # Group kembali untuk membentuk output akhir, gunakan $first untuk menghindari duplikasi pada magnitudes
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
                "magnitudes": {"$first": "$magnitudes"},
                "arrivals": {"$addToSet": "$arrivals"},
                "station_magnitudes_per_type": {
                    "$addToSet": {
                        "type": "$station_magnitude_ids_per_type.type",
                        "station_magnitudes": {
                            "_id": "$station_magnitudes._id",
                            "value": "$station_magnitudes.value",
                            "created_at": "$station_magnitudes.created_at",
                            "station": "$station_magnitudes.station",
                            "pick": "$station_magnitudes.pick",
                            "magnitude_value": "$station_magnitudes.magnitude_value"
                        }
                    }
                }
            }
        }

    ]




    # Run the aggregation pipeline
    result = list(origin_collection.aggregate(pipeline))
    
    return result

