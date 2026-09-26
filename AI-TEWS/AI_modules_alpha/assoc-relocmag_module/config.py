import os
from dotenv import load_dotenv

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

REDIS_HOST = os.getenv("redis_host")
REDIS_PORT = os.getenv("redis_port")

MONGO_HOST = os.getenv("database_host")
MONGO_PORT = os.getenv("database_port")

DB_NAME = os.getenv("database_name")

# Kafka topics
PICK_TOPIC = os.getenv("pick_topic")
ARRIVAL_PICK_TOPIC = os.getenv("arrival_pick_topic")
CLUSTER_TOPIC = os.getenv("cluster_topic")
EVENT_TOPIC = os.getenv("event_topic")
RELOCATION_TOPIC = os.getenv("relocation_topic")
RELOCATION_FEEDBACK_TOPIC = os.getenv("relocation_feedback_topic")

WINDOW_SIZE_SEC = 300
OVERLAPS_SEC = 180
MAX_WORKER = 1000
ORIGIN_TIME_OFFSET_SEC = 3