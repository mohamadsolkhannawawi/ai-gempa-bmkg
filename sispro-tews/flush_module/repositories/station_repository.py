
from bson.objectid import ObjectId


def station_find_all_repository(db):
    # Select your collection
    station_collection = db['station']
    
    # Retrieve all documents in the collection except those with role 'superadmin'
    stations = station_collection.find()
    
    return stations