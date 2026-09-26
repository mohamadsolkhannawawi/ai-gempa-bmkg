
from bson.objectid import ObjectId

def cluster_find_by_id_repository(db, cluster_id):
    cluster_collection = db['cluster']

    query = {
        '_id': ObjectId(cluster_id)}

    document = cluster_collection.find_one(query)
    return document

def cluster_find_all_repository(db):
    # Select your collection
    cluster_collection = db['cluster']
    
    
    # Retrieve all documents in the collection except those with role 'superadmin'
    clusters = cluster_collection.find()
    
    return clusters


def cluster_update_by_id_repository(db, pick_id, origin_time):
    cluster_collection = db['cluster']
    document = cluster_collection.update_one(
        {"_id": ObjectId(pick_id)},  # Query
        {
            "$set": {
                "origin_time": origin_time,
            }
        }
    )  # Update
    return document
