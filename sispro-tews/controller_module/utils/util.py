import uuid
import numpy as np
from bson.objectid import ObjectId
from datetime import datetime
import bcrypt

def verify_password(pwd_context, plain_password, hashed_password):
    # return pwd_context.verify(plain_password, hashed_password)

    return bcrypt.checkpw(
        bytes(plain_password, encoding="utf-8"),
        bytes(hashed_password, encoding="utf-8"),
    )
   
def get_password_hash(pwd_context, password):
    # return pwd_context.hash(password)

    return bcrypt.hashpw(
        bytes(password, encoding="utf-8"),
        bcrypt.gensalt(),
    )

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
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                doc[k] = str(v)  # Convert ObjectId to string
            elif isinstance(v, list):
                doc[k] = [str(item) if isinstance(item, ObjectId) else item for item in v]
            elif isinstance(v, dict):
                doc[k] = convert_object_id(v)  # Recursively process nested documents
    return doc

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
