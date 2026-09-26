import os, json, time
import numpy as np
import pandas as pd
from obspy import UTCDateTime
from kafka import KafkaConsumer
from dotenv import load_dotenv

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

consumer = KafkaConsumer("waveform_player", bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])

print("Processing...")
for message in consumer:
    data = json.loads(message.value.decode('utf-8'))
    print(data,"\n")

