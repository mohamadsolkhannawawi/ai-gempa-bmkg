from datetime import datetime
import os, pymongo, requests, json, threading
from dotenv import load_dotenv
from kafka import KafkaConsumer

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

MONGO_HOST = os.getenv("database_host")
MONGO_PORT = os.getenv("database_port")

NGINX_HOST = os.getenv("nginx_host")
NGINX_PORT = os.getenv("nginx_port")

DB_NAME = os.getenv("database_name")

# Kafka topics
WAVEFORM_TOPIC = os.getenv("waveform_topic")

print(f"{KAFKA_HOST}:{KAFKA_PORT}")
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
waveform_consumer = KafkaConsumer(WAVEFORM_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
db = mongodb_client[DB_NAME]
pick_col = db['pick']
station_col = db['station']

def send_to_service(url, data):
    requests.post(url, json=data)

if __name__ == "__main__":
    for message in waveform_consumer:
        print(f"{datetime.now()}: New message received!")
        data = json.loads(message.value.decode())
        thread = threading.Thread(target=send_to_service, args=(f"http://{NGINX_HOST}:{NGINX_PORT}/predict", data)).start()