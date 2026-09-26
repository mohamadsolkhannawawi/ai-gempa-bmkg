import os
from sshtunnel import SSHTunnelForwarder
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("../.env")

def get_database_connection(SSH_HOST,
    SSH_PORT,
    SSH_USERNAME,
    SSH_PASSWORD,
    MONGO_HOST,
    MONGO_DB,
    LOCAL_BIND_PORT,
    REMOTE_BIND_PORT,):

    client = MongoClient(host=MONGO_HOST, port=REMOTE_BIND_PORT)
    db = client[MONGO_DB]
    return db