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
    # Configuration
    # tunnel = SSHTunnelForwarder(
    #     (SSH_HOST, 22),  # Remote SSH server configuration
    #     ssh_username=SSH_USERNAME,
    #     ssh_password=SSH_PASSWORD,  # or use ssh_private_key='path/to/private/key'
    #     remote_bind_address=(MONGO_HOST, REMOTE_BIND_PORT),
    #     local_bind_address=('0.0.0.0', LOCAL_BIND_PORT)
    # )
    # tunnel.start()
    client = MongoClient(host=MONGO_HOST, port=REMOTE_BIND_PORT)
    # Access the specific database
    db = client[MONGO_DB]
    return db