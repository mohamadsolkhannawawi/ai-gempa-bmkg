from bson.objectid import ObjectId
from pymongo import database


def user_register_repository(db, username, password, region):
    user_collection = db["user"]

    user_data = {
        "username": username,
        "password": password,
        "region": region,
        "role": "user",
        "modules": [],
        "stations": [],
        "disable_stations": [],
    }

    try:
        # Attempt to insert the user data
        result = user_collection.insert_one(user_data)
        # Assuming success if no exception is raised
        # Return True for success, and the inserted ID for reference if needed
        return True, result.inserted_id
    except Exception as e:
        # Return False and the error message if an exception occurred
        return False, str(e)


def user_update_by_id_repository(
    db, user_id, username, password, region, modules, stations, disable_stations
):
    user_collection = db["user"]
    document = user_collection.update_one(
        {"_id": ObjectId(user_id)},  # Query
        {
            "$set": {
                "username": username,
                "password": password,
                "region": region,
                "modules": modules,
                "stations": stations,
                "disable_stations": disable_stations,
            }
        },
    )  # Update
    return document


def user_find_by_username_repository(db, username):
    user_collection = db["user"]
    query = {"username": username}
    document = user_collection.find_one(query)
    return document


def user_find_by_id_repository(db, user_id):
    user_collection = db["user"]
    query = {"_id": ObjectId(user_id)}
    document = user_collection.find_one(query)
    return document


def user_find_all_repository(
    db: database.Database, page: int, limit: int, keyword: str | None
):
    skip = (page - 1) * limit

    # Select your collection
    user_collection = db["user"]
    query = {"role": {"$ne": "superadmin"}}

    if keyword != None:
        query["username"] = {"$regex": keyword, "$options": "i"}

    # Retrieve all documents in the collection except those with role 'superadmin'
    all_except_superadmin = user_collection.find(query).skip(skip).limit(limit)
    total = user_collection.count_documents(query)

    return all_except_superadmin, total
