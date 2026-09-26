
from bson.objectid import ObjectId

def config_create_repository(db, name, config_value, type_data):
    module_collection = db['module']

    config_data = {
        "name": name, 
        "config": config_value, 
        "type": type_data,
    }

    try:
        # Attempt to insert the user data
        result = module_collection.insert_one(config_data)
        # Assuming success if no exception is raised
        # Return True for success, and the inserted ID for reference if needed
        return True, result.inserted_id
    except Exception as e:
        # Return False and the error message if an exception occurred
        return False, str(e)

def config_by_name_repository(db, name):
    module_collection = db['module']
    query = {"name": name}
    document = module_collection.find_one(query)
    return document


def config_find_all_repository(db):
    # Select your collection
    module_collection = db['module']
    # Retrieve all documents in the collection except those with role 'superadmin'
    all_except_superadmin = module_collection.find()
    
    return all_except_superadmin

def config_update_by_id_repository(db, 
                                 config_id, 
                                 name, 
                                 config_value, 
                                 type_data):
    module_collection = db['module']
    document = module_collection.update_one(
        {"_id": ObjectId(config_id)},  # Query
        {
            "$set": {
                "name": name, 
                "config": config_value, 
                "type": type_data,
            }
        }
    )  # Update
    return document