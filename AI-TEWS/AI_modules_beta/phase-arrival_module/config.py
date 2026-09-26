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

USER_NAME = os.getenv("regional")

# Kafka topics
ARRIVAL_PICK_TOPIC = os.getenv("arrival_pick_topic")
PICK_TOPIC = os.getenv("pick_topic")

# Other constants
SAMPLE_RATE = int(os.getenv("sample_rate"))
WINDOW_SIZE_SEC = int(os.getenv("window_size_sec"))
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE
OVERLAPS_SEC = int(os.getenv("overlap_sec"))
OVERLAPS = OVERLAPS_SEC * SAMPLE_RATE
PADDING_FIRST_WINDOW = 5
MAX_WORKERS = 6