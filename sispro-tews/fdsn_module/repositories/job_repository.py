

def job_find_by_name_repository(db, name):
    job_collection = db['job']

    query = {
        'name': name,
        }

    document = job_collection.find_one(query)
    return document