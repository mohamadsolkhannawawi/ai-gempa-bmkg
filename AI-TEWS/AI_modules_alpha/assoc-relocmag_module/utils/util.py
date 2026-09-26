from bson.objectid import ObjectId
from datetime import datetime

def convert_object_ids(docs):
    if isinstance(docs, list):
        for doc in docs:
            convert_object_ids(doc)
    elif isinstance(docs, dict):
        for k, v in docs.items():
            if isinstance(v, ObjectId):
                docs[k] = str(v)  # Convert ObjectId to string
            elif isinstance(v, datetime):
                docs[k] = v.isoformat()  # Convert datetime to string
            elif isinstance(v, list):
                docs[k] = [str(item) if isinstance(item, ObjectId) else convert_object_ids(item) if isinstance(item, dict) else item for item in v]
            elif isinstance(v, dict):
                convert_object_ids(v)  # Recursively process nested documents
    return docs
