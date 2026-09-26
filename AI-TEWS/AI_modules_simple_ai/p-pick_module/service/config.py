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
WAVEFORM_TOPIC = os.getenv("waveform_topic")
PICK_TOPIC = os.getenv("pick_topic")
ARRIVAL_WAVEFORM_TOPIC = os.getenv("arrival_waveform_topic")

# Other constants
SAMPLE_RATE = 20
WINDOW_SIZE_SEC = 10
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE
CENTER = WINDOW_SIZE // 2
STALTA_WINDOW = 80
STALTA_CHANNEL = 'Z'
# THRESHOLD = 0.5
THRESHOLD = 500
NORM_CONST = 1000
NCHECK = 4
MAX_WORKERS = 300