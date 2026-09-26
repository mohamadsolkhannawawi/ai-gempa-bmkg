
from bson.objectid import ObjectId

def magnitude_find_by_id_repository(db, magnitude_id):
    magnitude_collection = db['magnitude']

    query = {
        '_id': ObjectId(magnitude_id)}

    document = magnitude_collection.find_one(query)
    return document

def magnitude_find_all_repository(db):
    # Select your collection
    magnitude_collection = db['magnitude']
    
    
    # Retrieve all documents in the collection except those with role 'superadmin'
    magnitudes = magnitude_collection.find()
    
    return magnitudes

