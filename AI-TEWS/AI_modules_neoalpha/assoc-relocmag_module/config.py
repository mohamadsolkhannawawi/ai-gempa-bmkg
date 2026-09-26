import os
import obspy
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

FDSN_SERVER_HOST = os.getenv("fdsn_server_host")
RECORDSTREAM_SERVER_HOST = os.getenv("recordstream_server_host")

USER_NAME = os.getenv("regional")

# TODO: add logic to convert DB station to stations.xml
station_xml = obspy.read_inventory('./data/stations.xml')

# Kafka topics
ORIGIN_TOPIC = os.getenv("origin_topic")

# Other constants
SAMPLE_RATE = int(os.getenv("sample_rate"))
WINDOW_SIZE_SEC = int(os.getenv("window_size_sec"))
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE
OVERLAPS_SEC = int(os.getenv("overlap_sec"))
OVERLAPS = OVERLAPS_SEC * SAMPLE_RATE
ASSOCIATION_EXPIRED_SEC = 300
N_STATION = 4
MAX_WORKERS = 300

M100_CALC_TIME_INTERVAL_SEC = 30
M100_CALC_TIME_LIMIT_SEC = 5 * 60
M100_WAVEFORM_MAX_DIFF = 10