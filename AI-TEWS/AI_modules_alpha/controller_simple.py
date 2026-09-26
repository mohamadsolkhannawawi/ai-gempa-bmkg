import numpy as np
import pandas as pd
import os, json, time, redis
from obspy import UTCDateTime
from kafka import KafkaConsumer, KafkaProducer
from dotenv import load_dotenv

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")
REDIS_HOST = os.getenv("redis_host")
REDIS_PORT = os.getenv("redis_port")

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

consumer = KafkaConsumer("event", bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])

print("Processing...")
for message in consumer:
    # Json load
    data = json.loads(message.value.decode('utf-8'))
    print(data)
