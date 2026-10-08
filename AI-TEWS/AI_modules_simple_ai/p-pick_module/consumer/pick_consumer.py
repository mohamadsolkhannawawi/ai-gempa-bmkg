from datetime import datetime
import os, pymongo, requests, json
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

# Limit thread creation - prevent RuntimeError: can't start new thread in DinD
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

print(f"[PickConsumer] Kafka: {KAFKA_HOST}:{KAFKA_PORT}, MongoDB: {MONGO_HOST}:{MONGO_PORT}")
print(f"[PickConsumer] nginx: {NGINX_HOST}:{NGINX_PORT}, topic: {WAVEFORM_TOPIC}")
# Use directConnection to avoid SDAM background monitor threads
mongodb_client = pymongo.MongoClient(
    host=MONGO_HOST,
    port=int(MONGO_PORT),
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    directConnection=True,
)
waveform_consumer = KafkaConsumer(
    WAVEFORM_TOPIC,
    bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"],
    request_timeout_ms=30000,
    api_version_auto_timeout_ms=30000,
)
db = mongodb_client[DB_NAME]
pick_col = db['pick']
station_col = db['station']

def send_to_service(url, data):
    try:
        resp = requests.post(url, json=data, timeout=120)
        if resp.status_code == 200:
            print(f"  → Predict OK: {resp.status_code}")
        else:
            print(f"  → Predict FAILED: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"  → Predict ERROR: {e}")

if __name__ == "__main__":
    for message in waveform_consumer:
        try:
            print(f"{datetime.now()}: New message received!")
            data = json.loads(message.value.decode())
            # Synchronous send to avoid thread pool exhaustion in DinD
            send_to_service(f"http://{NGINX_HOST}:{NGINX_PORT}/predict", data)
        except Exception as e:
            print(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()