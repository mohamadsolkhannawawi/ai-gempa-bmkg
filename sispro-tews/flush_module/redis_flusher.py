import os
import redis
import time
import json
import logging
from dotenv import load_dotenv
from repositories.station_repository import station_find_all_repository
from tqdm import tqdm
from sshtunnel import SSHTunnelForwarder
from pymongo import MongoClient
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

def get_database_connection():
    client = MongoClient(host=MONGO_HOST, port=REMOTE_BIND_PORT)
    db = client[MONGO_DB]
    return db

def delete_expired_messages(channel: str):
    current_timestamp = int(time.time())
    messages = redis_client.lrange(f'{channel}_history', 0, -1)
    for msg in messages:
        msg_data = json.loads(msg)
        if msg_data.get('expiration_timestamp', 0) < current_timestamp:
            redis_client.lrem(f'{channel}_history', 0, msg)
            logger.info(f"Deleted expired message from {channel}_history: {msg_data}")

def process_station(station_data):
    channels = station_data.get("channel", [])
    for channel in tqdm(channels, desc=f"Processing channels for {station_data.get('code', '')}", leave=False, unit="channel"):
        station_name = station_data.get("network", "") + "." + station_data.get("code", "") + ".." + channel
        delete_expired_messages(station_name)

def delete_redis():
    try:
        db = get_database_connection()
        station_datas = station_find_all_repository(db)
        
        with ThreadPoolExecutor(max_workers=200) as executor:  # Adjust the number of threads as needed
            for station_data in tqdm(station_datas, desc="Processing stations", unit="station"):
                executor.submit(process_station, station_data)

    except Exception as e:
        logger.error("Error: %s", str(e))

if __name__ == "__main__":
    delete_redis()
