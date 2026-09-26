import uuid
import numpy as np
from bson.objectid import ObjectId
from datetime import datetime

def verify_password(pwd_context, plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)
   
def get_password_hash(pwd_context, password):
    return pwd_context.hash(password)

def my_random_string(string_length=10):
    """Returns a random string of length string_length."""
    random = str(uuid.uuid4()) # Convert UUID format to a Python string.
    random = random.replace("-","") # Remove the UUID '-'.
    random = random.lower()
    return random[0:string_length] # Return the random string.

def get_response(status, message, data):
    response = {
        "status" : status,
        "message" : message,
        "data": data
    }
    return response

def convert_object_id(doc):
    if isinstance(doc, dict):
        new_doc = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                new_doc[k] = str(v)  # Convert ObjectId to string
            elif isinstance(v, list):
                new_doc[k] = [convert_object_id(item) if isinstance(item, (dict, list)) else str(item) if isinstance(item, ObjectId) else item for item in v]
            elif isinstance(v, dict):
                new_doc[k] = convert_object_id(v)  # Recursively process nested dictionaries
            else:
                new_doc[k] = v  # Keep other types unchanged
        return new_doc
    elif isinstance(doc, list):
        return [convert_object_id(item) if isinstance(item, (dict, list)) else str(item) if isinstance(item, ObjectId) else item for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)  # Convert ObjectId at the top level
    return doc  # Return the original value if it's not dict, list, or ObjectId

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
