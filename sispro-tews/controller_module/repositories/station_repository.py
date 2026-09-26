from bson.objectid import ObjectId
from pymongo import database


def station_add_repository(
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
):
    station_collection = db["station"]

    station_data = {
        "name": name,
        "code": code,
        "network": network,
        "channel": channel,
        "longitude": longitude,
        "latitude": latitude,
        "elevation": elevation,
        "server_seedlink": server_seedlink,
        "server_fdsn": server_fdsn,
    }

    try:
        # Attempt to insert the user data
        result = station_collection.insert_one(station_data)
        # Assuming success if no exception is raised
        # Return True for success, and the inserted ID for reference if needed
        return True, result.inserted_id
    except Exception as e:
        # Return False and the error message if an exception occurred
        return False, str(e)


def station_update_by_id_repository(
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
):
    station_collection = db["station"]
    document = station_collection.update_one(
        {"_id": ObjectId(station_id)},  # Query
        {
            "$set": {
                "name": name,
                "code": code,
                "network": network,
                "channel": channel,
                "longitude": longitude,
                "latitude": latitude,
                "elevation": elevation,
                "server_seedlink": server_seedlink,
                "server_fdsn": server_fdsn,
            }
        },
    )  # Update
    return document


def station_update_status_by_id_repository(db, station_id, status):
    station_collection = db["station"]
    document = station_collection.update_one(
        {"_id": ObjectId(station_id)},  # Query
        {
            "$set": {
                "status": status,
            }
        },
    )  # Update
    return document


def station_find_by_id_repository(db, station_id):
    station_collection = db["station"]

    query = {"_id": ObjectId(station_id)}

    document = station_collection.find_one(query)
    return document


def station_find_all_repository(
    db: database.Database,
    page: int | None,
    limit: int | None,
    keyword: str | None,
    station_ids: list[ObjectId] | None,
):
    station_collection = db["station"]
    query = {}

    if keyword != None:
        query["name"] = {"$regex": keyword, "$options": "i"}

    # if station_ids != None:
    #     query["_id"] = {"$in": station_ids}

    # # Retrieve all documents in the collection except those with role 'superadmin'
    # if page is None or limit is None:
    #     stations = station_collection.find(query)
    # else:
    #     skip = (page - 1) * limit
    #     stations = station_collection.find(query).skip(skip).limit(limit)
    
    # If station_ids is provided, construct a pipeline to match and sort by `station_ids` order
    if station_ids is not None:
        # Convert station_ids to ObjectId if they are not already
        station_ids = [ObjectId(id) if isinstance(id, str) else id for id in station_ids]

        # Build the aggregation pipeline
        pipeline = [
            {"$match": query},
            {"$match": {"_id": {"$in": station_ids}}},
            {"$addFields": {"sort_index": {"$indexOfArray": [station_ids, "$_id"]}}},
            {"$sort": {"sort_index": 1}}
        ]

        # Apply pagination if page and limit are provided
        if page is not None and limit is not None:
            skip = (page - 1) * limit
            pipeline.extend([{"$skip": skip}, {"$limit": limit}])

        # Run the aggregation
        stations = list(station_collection.aggregate(pipeline))

    else:
        # Default behavior if station_ids is not provided
        if page is None or limit is None:
            stations = list(station_collection.find(query))
        else:
            skip = (page - 1) * limit
            stations = list(station_collection.find(query).skip(skip).limit(limit))

    # Count total documents matching the query
    total = station_collection.count_documents(query)

    total = station_collection.count_documents(query)

    return stations, total


def station_delete_by_id_repository(db, station_id):
    # Select your collection
    station_collection = db["station"]

    query = {"_id": ObjectId(station_id)}

    stations = station_collection.delete_one(query)

    return stations
