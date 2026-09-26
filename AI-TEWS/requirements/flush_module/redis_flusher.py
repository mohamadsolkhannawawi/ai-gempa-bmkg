# Connect to Redis
import os, redis, time, json, logging
from dotenv import load_dotenv
# from configuration.database import get_database_connection
from repositories.station_repository import station_find_all_repository
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# env constant
load_dotenv("./.env")
redis_host = os.getenv('redis_host')
redis_port = os.getenv('redis_port')
kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
seedlink_url = os.getenv('seedlink_url')
regional = os.getenv('regional')
SSH_HOST = os.getenv('ssh_host')
SSH_PORT = int(os.getenv('ssh_port'))
SSH_USERNAME = os.getenv('ssh_username')
SSH_PASSWORD = os.getenv('ssh_password')
MONGO_HOST = os.getenv('database_host')
MONGO_DB = os.getenv('database_name')
LOCAL_BIND_PORT = int(os.getenv('database_port'))
REMOTE_BIND_PORT = int(os.getenv('database_port'))
                       

redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

import os
from sshtunnel import SSHTunnelForwarder
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("../.env")

MAX_WORKER = 10

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


def delete_expired_messages(channel: str):
    current_timestamp = int(time.time())
    messages = redis_client.lrange(channel, 0, -1)
    with redis_client.pipeline() as pipe:
        for msg in messages:
            msg_data = json.loads(msg)
            if msg_data.get('expiration_timestamp', 0) < current_timestamp:
                pipe.lrem(channel, 0, msg)
                # logger.info(f"Deleted expired message from {channel}_history: {msg_data}")
        pipe.execute()            

def delete_redis():
    # Clear all data
    try:
        print("masuk")
        history_data = redis_client.scan_iter("*_history")
        with ThreadPoolExecutor(max_workers=MAX_WORKER) as executor:  
            for station_as_key in tqdm(history_data, desc="Processing stations", unit="channel"):
                executor.submit(delete_expired_messages, station_as_key)
    except Exception as e:
        print("Error ", str(e))
    # r.flushall()