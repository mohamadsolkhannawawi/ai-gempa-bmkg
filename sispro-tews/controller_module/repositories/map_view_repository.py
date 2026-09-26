
from bson.objectid import ObjectId

def map_view_add_repository(
        db, 
        map_view_name, 
        map_view_type,
        map_view_type_data,
        value,):
    map_view_collection = db['map_view']

    map_view_data = {
        "map_view_name" : map_view_name,
        "map_view_type" : map_view_type,
        "map_view_type_data" : map_view_type_data,
        "value" : value,

    }

    try:
        # Attempt to insert the user data
        result = map_view_collection.insert_one(map_view_data)
        # Assuming success if no exception is raised
        # Return True for success, and the inserted ID for reference if needed
        return True, result.inserted_id
    except Exception as e:
        # Return False and the error message if an exception occurred
        return False, str(e)


def map_view_update_by_id_repository(
        db, 
        map_view_id,
        map_view_name, 
        map_view_type,
        map_view_type_data,
        value,):
    map_view_collection = db['map_view']
    document = map_view_collection.update_one(
        {"_id": ObjectId(map_view_id)},  # Query
        {"$set": {
            "map_view_name" : map_view_name,
            "map_view_type" : map_view_type,
            "map_view_type_data" : map_view_type_data,
            "value" : value,

        }
    })  # Update
    return document

def map_view_find_by_id_repository(db, map_view_id):
    map_view_collection = db['map_view']

    query = {
        '_id': ObjectId(map_view_id)}

    document = map_view_collection.find_one(query)
    return document

def map_view_find_all_repository(db):
    # Select your collection
    map_view_collection = db['map_view']
    
    
    # Retrieve all documents in the collection except those with role 'superadmin'
    map_views = map_view_collection.find()
    
    return map_views


def map_view_delete_by_id_repository(db, map_view_id):
    # Select your collection
    map_view_collection = db['map_view']
    
    
    query = {
        '_id': ObjectId(map_view_id)}

    map_view = map_view_collection.delete_one(query)
    
    return map_view
