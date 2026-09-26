import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("./.env")

# Kafka configurations
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

# Redis configurations
REDIS_HOST = os.getenv("redis_host")
REDIS_PORT = os.getenv("redis_port")

# MongoDB configurations
MONGO_HOST = os.getenv("database_host")
MONGO_PORT = os.getenv("database_port")
DB_NAME = os.getenv("database_name")

# Kafka topics
PICK_TOPIC = os.getenv("pick_topic")
ARRIVAL_PICK_TOPIC = os.getenv('arrival_pick_topic')

USER_NAME = os.getenv("regional")

# Other constants
SAMPLE_RATE = int(os.getenv("sample_rate"))
WINDOW_SIZE_SEC = int(os.getenv("window_size_sec"))
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE
OVERLAPS_SEC = int(os.getenv("overlap_sec"))
OVERLAPS = OVERLAPS_SEC * SAMPLE_RATE
MIN_PICK_DIFF = 60
AIC_THRESHOLD = 200
MAX_WORKERS = 300