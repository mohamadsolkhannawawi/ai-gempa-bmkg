
from bson.objectid import ObjectId

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
        server_fdsn):
    station_collection = db['station']

    station_data = {
        "name" : name,
        "code" : code,
        "network" : network,
        "channel" : channel,
        "longitude" : longitude,
        "latitude" : latitude,
        "elevation" : elevation,
        "server_seedlink" : server_seedlink, 
        "server_fdsn" : server_fdsn

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
        server_fdsn):
    station_collection = db['station']
    document = station_collection.update_one(
        {"_id": ObjectId(station_id)},  # Query
        {"$set": {
            "name" : name,
            "code" : code,
            "network" : network,
            "channel" : channel,
            "longitude" : longitude,
            "latitude" : latitude,
            "elevation" : elevation,
            "server_seedlink" : server_seedlink, 
            "server_fdsn" : server_fdsn
        }
    })  # Update
    return document

def station_find_by_code_and_network_repository(db, code, network):
    station_collection = db['station']

    query = {
        'code': code,
        'network': network
        }

    document = station_collection.find_one(query)
    return document

def station_find_all_repository(db):
    # Select your collection
    station_collection = db['station']
    
    
    # Retrieve all documents in the collection except those with role 'superadmin'
    stations = station_collection.find()
    
    return stations


def station_delete_by_id_repository(db, station_id):
    # Select your collection
    station_collection = db['station']
    
    
    query = {
        '_id': ObjectId(station_id)}

    stations = station_collection.delete_one(query)
    
    return stations

