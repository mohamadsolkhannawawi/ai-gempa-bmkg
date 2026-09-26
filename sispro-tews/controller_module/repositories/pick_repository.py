from bson.objectid import ObjectId
from pymongo import database
from dateutil import parser


def pick_find_by_id_repository(db, pick_id):
    pick_collection = db["pick"]

    query = {"_id": ObjectId(pick_id)}

    document = pick_collection.find_one(query)
    return document


def pick_find_by_station_id_repository(
    db: database.Database, station_id: str, start_date: str | None, end_date: str | None
):
    pick_collection = db["pick"]

    query = {"station_id": ObjectId(station_id)}

    if start_date != None or end_date != None:
        query["timestamp"] = {}

        if start_date != None:
            query["timestamp"]["$gte"] = parser.parse(start_date)
        if end_date != None:
            query["timestamp"]["$lte"] = parser.parse(end_date)

    document = pick_collection.find(query).sort("timestamp", -1).limit(1)

    return document


def pick_find_all_repository(db):
    # Select your collection
    pick_collection = db["pick"]

    # Retrieve all documents in the collection except those with role 'superadmin'
    picks = pick_collection.find()

    return picks


def pick_update_by_id_repository(db, pick_id, timestamp):
    pick_collection = db["pick"]
    document = pick_collection.update_one(
        {"_id": ObjectId(pick_id)},  # Query
        {
            "$set": {
                "timestamp": timestamp,
            }
        },
    )  # Update
    return document
