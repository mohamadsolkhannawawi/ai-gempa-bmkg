from bson.objectid import ObjectId
from datetime import datetime
from dateutil import parser


def event_find_by_id_repository(db, event_id):
    event_collection = db["event"]

    # ID event yang ingin dicari
    event_id = ObjectId(event_id)
    # Pipeline agregasi
    pipeline = [
        {"$match": {"_id": event_id}},
        {
            "$lookup": {
                "from": "origin",
                "localField": "origin_ids",
                "foreignField": "_id",
                "as": "origins",
            }
        },
        {"$unwind": {"path": "$origins", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "magnitude",
                "localField": "origins.magnitude_ids",
                "foreignField": "_id",
                "as": "origins.magnitudes",
            }
        },
        {
            "$lookup": {
                "from": "arrival",
                "localField": "origins.arrival_ids",
                "foreignField": "_id",
                "as": "origins.arrivals",
            }
        },
        {
            "$lookup": {
                "from": "origin",
                "localField": "preferred_origin_id",
                "foreignField": "_id",
                "as": "prefered_origins",
            }
        },
        {
            "$group": {
                "_id": "$_id",
                "name": {"$first": "$name"},
                "origin_ids": {"$first": "$origin_ids"},
                "created_at": {"$first": "$created_at"},
                "origins": {"$push": "$origins"},
            }
        },
    ]

    pipeline = [
        {"$match": {"_id": event_id}},
        {
            "$lookup": {
                "from": "origin",
                "localField": "origin_ids",
                "foreignField": "_id",
                "as": "origins",
            }
        },
        {"$unwind": {"path": "$origins", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "magnitude",
                "localField": "origins.magnitude_ids",
                "foreignField": "_id",
                "as": "origins.magnitudes",
            }
        },
        {
            "$lookup": {
                "from": "arrival",
                "localField": "origins.arrival_ids",
                "foreignField": "_id",
                "as": "origins.arrivals",
            }
        },
        {"$unwind": {"path": "$origins.arrivals", "preserveNullAndEmptyArrays": True}},
        {
            "$lookup": {
                "from": "pick",
                "localField": "origins.arrivals.pick_source_id",
                "foreignField": "_id",
                "as": "origins.arrivals.pick_details",
            }
        },
        {
            "$unwind": {
                "path": "$origins.arrivals.pick_details",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {
            "$lookup": {
                "from": "station",
                "localField": "origins.arrivals.station_id",
                "foreignField": "_id",
                "as": "origins.arrivals.station_details",
            }
        },
        {
            "$unwind": {
                "path": "$origins.arrivals.station_details",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {
            "$group": {
                "_id": {"event_id": "$_id", "origin_id": "$origins._id"},
                "name": {"$first": "$name"},
                "preferred_origin_id": {"$first": "$preferred_origin_id"},
                "origin_ids": {"$first": "$origin_ids"},
                "origin": {"$first": "$origins"},
                "arrivals": {"$push": "$origins.arrivals"},
            }
        },
        {
            "$group": {
                "_id": "$_id.event_id",
                "name": {"$first": "$name"},
                "preferred_origin_id": {"$first": "$preferred_origin_id"},
                "origin_ids": {"$first": "$origin_ids"},
                "origins": {
                    "$push": {"$mergeObjects": ["$origin", {"arrivals": "$arrivals"}]}
                },
            }
        },
    ]

    # Menjalankan pipeline agregasi
    try:
        event = list(event_collection.aggregate(pipeline))

        # Menampilkan hasil
        return event
    except TypeError as e:
        print(f"An error occurred: {e}")


def event_find_all_repository(db, page, page_size, start_date, end_date, user_id=None):
    # Select your collection
    event_collection = db["event"]

    skip = page_size * (page - 1)

    if isinstance(start_date, str):
        start_date = parser.parse(start_date)
    if isinstance(end_date, str):
        end_date = parser.parse(end_date)

    # Define pipeline to exclude auto event with user modified results
    user_modified_filter = [
        # Match documents where 'modified_by' is equal to the specified ObjectId
        {"$match": {"modified_by": ObjectId(user_id)}},
        # Project only the 'event_auto_ref_id' field in the result
        {
            "$project": {
                "event_auto_ref_id": 1,
                "_id": 0,  # Exclude the _id field from the output
            }
        },
    ]

    excluded_auto_events = event_collection.aggregate(user_modified_filter)
    if excluded_auto_events != None:
        excluded_auto_events = [
            ObjectId(event_id["event_auto_ref_id"]) for event_id in excluded_auto_events
        ]
    else:
        excluded_auto_events = []

    # Define the number of documents to skip and the page size
    skip = skip
    page_size = page_size

    # Aggregation pipeline
    pipeline = [
        {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
        {
            "$lookup": {
                "from": "origin",
                "localField": "preferred_origin_id",
                "foreignField": "_id",
                "as": "origins",
            }
        },
        {
            "$unwind": "$origins"  # Unwind the origins array to handle each element individually
        },
        {
            "$lookup": {
                "from": "magnitude",
                "localField": "origins.magnitude_ids",
                "foreignField": "_id",
                "as": "origins.magnitudes",
            }
        },
        {"$sort": {"created_at": -1}},  # Sort by created_at in descending order
        {"$skip": skip},  # Skip the first 'skip' records
        {"$limit": page_size},  # Limit the number of records
    ]

    # Execute the aggregation pipeline
    results = event_collection.aggregate(pipeline)

    return results


def event_find_all_between_date_repository(db, start_date, end_date):
    # Select your collection
    event_collection = db["event"]
    query = {"created_at": {"$gte": start_date, "$lte": end_date}}
    # skip = page_size * (page - 1)

    skip = 0
    page_size = 10
    # Combine the query with the aggregation pipeline
    pipeline = [
        {"$match": query},  # Apply the query as the first stage
        {
            "$lookup": {
                "from": "origin",
                "localField": "preferred_origin_id",
                "foreignField": "_id",
                "as": "origins",
            }
        },
        {
            "$unwind": "$origins"  # Unwind the origins array to handle each element individually
        },
        {
            "$lookup": {
                "from": "magnitude",
                "localField": "origins.magnitude_ids",
                "foreignField": "_id",
                "as": "origins.magnitudes",
            }
        },
        {"$sort": {"created_at": -1}},  # Sort by created_at in descending order
        {"$skip": skip},  # Skip the first 'skip' records
        {"$limit": page_size},  # Limit the number of records
    ]

    # Execute the aggregation pipeline
    results = event_collection.aggregate(pipeline)
    return results


def event_update_by_event_id_repository(db, event_id, station_id, phase, timestamp):
    event_collection = db["event"]
    document = event_collection.update_one(
        {"_id": ObjectId(event_id)},  # Query
        {"$set": {"station_id": station_id, "phase": phase, "timestamp": timestamp}},
    )  # Update
    return document
