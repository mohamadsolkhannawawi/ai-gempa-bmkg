from bson.objectid import ObjectId
from pymongo import database
from dateutil import parser


def arrival_find_by_id_repository(db, arrival_id):
    arrival_collection = db["arrival"]

    query = {"_id": ObjectId(arrival_id)}

    document = arrival_collection.find_one(query)
    return document


def arrival_find_by_station_repository(
    db: database.Database, station_id: str, start_date: str | None, end_date: str | None
):
    arrival_collection = db["arrival"]

    query = {"station_id": ObjectId(station_id)}

    if start_date != None or end_date != None:
        query["timestamp"] = {}

        if start_date != None:
            query["timestamp"]["$gte"] = parser.parse(start_date)
        if end_date != None:
            query["timestamp"]["$lte"] = parser.parse(end_date)

    document = arrival_collection.find(query)

    return document


def arrival_find_all_repository(db):
    # Select your collection
    arrival_collection = db["arrival"]

    # Retrieve all documents in the collection except those with role 'superadmin'
    arrivals = arrival_collection.find()

    return arrivals


def arrival_update_by_id_repository(db, arrival_id, timestamp):
    arrival_collection = db["arrival"]
    document = arrival_collection.update_one(
        {"_id": ObjectId(arrival_id)},  # Query
        {
            "$set": {
                "timestamp": timestamp,
            }
        },
    )  # Update
    return document
