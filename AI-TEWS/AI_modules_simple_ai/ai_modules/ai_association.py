import os, redis, pymongo, threading, time, json
import numpy as np
import pandas as pd
import tensorflow as tf
from obspy import UTCDateTime, Trace
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer

from utils.messaging import json_serializer
from utils.preprocessing import associate_preparation, packing_to_kafka

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
CLUSTER_TOPIC = os.getenv("cluster_topic")

# Other constant
MIN_STATION = 5
SAMPLE_RATE = 20
BUFFER_SIZE_SEC = 20
BUFFER_SIZE = BUFFER_SIZE_SEC * SAMPLE_RATE 
MAX_WORKER = 1000

# Instantiate some clients
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
pick_consumer = KafkaConsumer(PICK_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
cluster_col = db['cluster']
    
def task(message):
    data = json_serializer(message)
    print(data)
    outputs = associate_preparation(data, MIN_STATION, BUFFER_SIZE_SEC, redis_client)
    if outputs:
        packing_to_kafka(outputs, producer, CLUSTER_TOPIC)
    print(outputs)
    return 0

if __name__ == "__main__":
    print("Processing association")
    # Delete Redis
    i = 0

    for message in pick_consumer:
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKER:
            print("System Overhead: Forced Stop!!!...............")
            break

        # # Counter Check
        # if i==MAX_WORKER:
        #     break
        # i+=1