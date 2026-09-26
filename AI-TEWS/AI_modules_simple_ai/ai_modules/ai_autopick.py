import os, redis, pymongo, threading, time, json
import numpy as np
import tensorflow as tf
from obspy import UTCDateTime, Trace
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer

from utils.messaging import json_serializer
from utils.preprocessing import trace_processing, single_channel_processing, multi_channel_processing, packing_to_kafka

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
WAVEFORM_TOPIC = os.getenv("waveform_topic")
PICK_TOPIC = os.getenv("pick_topic")
ARRIVAL_WAVEFORM_TOPIC = os.getenv("arrival_waveform_topic")

# Other constant
SAMPLE_RATE = 20
WINDOW_SIZE_SEC = 60
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE
CENTER = WINDOW_SIZE//2
STALTA_WINDOW = 80
STALTA_CHANNEL = 'Z'
THRESHOLD = 0.5
NORM_CONST = 1000
NCHECK = 4
MAX_WORKER = 1000

# Instantiate some clients
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
waveform_consumer = KafkaConsumer(WAVEFORM_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
pick_col = db['pick']
station_col = db['station']

STATION_CHANNELS = {
    # 'AAI': ['SHE', 'SHN', 'SHZ'], }
    'AAI': ['SHE', 'SHN', 'SHZ'], 'ALKI': ['SHE', 'SHN', 'SHZ'],
    'ATNI': ['SHE', 'SHN', 'SHZ'], 'BAKI': ['HHE', 'HHN', 'HHZ'],
    'BASI': ['SHE', 'SHN', 'SHZ'], 'BATI': ['SHE', 'SHN', 'SHZ'],
    'BBJI': ['SHE', 'SHN', 'SHZ'], 'BKB': ['SHE', 'SHN', 'SHZ'],
    # 'BKNI': ['SHE', 'SHN', 'SHZ'], 'BLSI': ['SHE', 'SHN', 'SHZ'],
    # 'BNDI': ['SHE', 'SHN', 'SHZ'], 'BSSI': ['SHE', 'SHN', 'SHZ'],
    # 'BWJI': ['SHE', 'SHN', 'SHZ'], 'BYJI': ['SHE', 'SHN', 'SHZ'],
    # 'CGJI': ['SHE', 'SHN', 'SHZ'], 'CTJI': ['SHE', 'SHN', 'SHZ'],
    # 'DBJI': ['SHE', 'SHN', 'SHZ'], 'EGSI': ['SHE', 'SHN', 'SHZ'],
    # 'FAKI': ['SHE', 'SHN', 'SHZ'], 'GENI': ['SHE', 'SHN', 'SHZ'],
    # 'GLMI': ['SHE', 'SHN', 'SHZ'], 'GRJI': ['SHE', 'SHN', 'SHZ'],
    # 'JCJI': ['SHE', 'SHN', 'SHZ'], 'KASI': ['SHE', 'SHN', 'SHZ'],
    # 'KLI': ['SHE', 'SHN', 'SHZ'], 'KMMI': ['SHE', 'SHN', 'SHZ'],
    # 'KMPI': ['SHE', 'SHN', 'SHZ'], 'KMSI': ['SHE', 'SHN', 'SHZ'],
    # 'KRAI': ['SHE', 'SHN', 'SHZ'], 'KSI': ['HHE', 'HHN', 'HHZ'],
    # 'LHSI': ['SHE', 'SHN', 'SHZ'], 'LUWI': ['SHE', 'SHN', 'SHZ'],
    # 'LWLI': ['SHE', 'SHN', 'SHZ'], 'MBJI': ['HHE', 'HHN', 'HHZ'],
    # 'MGAI': ['SHE', 'SHN', 'SHZ'], 'MKS': ['SHE', 'SHN', 'SHZ'],
    # 'MMRI': ['SHE', 'SHN', 'SHZ'], 'MNAI': ['SHE', 'SHN', 'SHZ'],
    # 'MNI': ['HHE', 'HHN', 'HHZ'], 'MPSI': ['SHE', 'SHN', 'SHZ'],
    # 'MRSI': ['SHE', 'SHN', 'SHZ'], 'MTAI': ['HHE', 'HHN', 'HHZ'],
    # 'NGJI': ['SHE', 'SHN', 'SHZ'], 'NLAI': ['SHE', 'SHN', 'SHZ'],
    # 'PCI': ['HHE', 'HHN', 'HHZ'], 'PCJI': ['SHE', 'SHN', 'SHZ'],
    # 'PMBI': ['SHE', 'SHN', 'SHZ'], 'PMSI': ['SHE', 'SHN', 'SHZ'],
    'PPJI': ['HHE', 'HHN', 'HHZ'], 'PSSI': ['SHE', 'SHN', 'SHZ'],
    'RAPI': ['SHE', 'SHN', 'SHZ'], 'RKPI': ['SHE', 'SHN', 'SHZ'],
    'SANI': ['SHE', 'SHN', 'SHZ'], 'SAUI': ['SHE', 'SHN', 'SHZ'],
    'SBJI': ['SHE', 'SHN', 'SHZ'], 'SCJI': ['SHE', 'SHN', 'SHZ'],
    'SGSI': ['SHE', 'SHN', 'SHZ'], 'SKJI': ['SHE', 'SHN', 'SHZ'],
    'SMKI': ['SHE', 'SHN', 'SHZ'], 'SMPI': ['SHE', 'SHN', 'SHZ'],
    'SMRI': ['SHE', 'SHN', 'SHZ'], 'SOEI': ['SHE', 'SHN', 'SHZ'],
    'SRPI': ['SHE', 'SHN', 'SHZ'], 'SRSI': ['SHE', 'SHN', 'SHZ'],
    'STKI': ['SHE', 'SHN', 'SHZ'], 'SWI': ['SHE', 'SHN', 'SHZ'],
    'SWJI': ['SHE', 'SHN', 'SHZ'], 'TARAI': ['HHE', 'HHN', 'HHZ'],
    'TBJI': ['SHE', 'SHN', 'SHZ'], 'TNTI': ['SHE', 'SHN', 'SHZ'],
    'TOLI2': ['SHE', 'SHN', 'SHZ'], 'TPI': ['HHE', 'HHN', 'HHZ'],
    'TTSI': ['SHE', 'SHN', 'SHZ'], 'UGM': ['SHE', 'SHN', 'SHZ'],
    'WAMI': ['HHE', 'HHN', 'HHZ'], 'WOJI': ['SHE', 'SHN', 'SHZ']}

def task(message):
    data = json_serializer(message)
    if data['station'] in STATION_CHANNELS.keys():
        trace = trace_processing(data, SAMPLE_RATE)
        station_channels = STATION_CHANNELS[trace.stats.station]
        outputs = single_channel_processing(trace, WINDOW_SIZE, CENTER, NCHECK, redis_client)
        # outputs = multi_channel_processing(trace, station_channels, station_channels[-1], WINDOW_SIZE, CENTER, NCHECK, redis_client)
        if outputs:
            packing_to_kafka(outputs, producer, PICK_TOPIC)
        print(trace.id, trace.stats.endtime, outputs)


if __name__ == "__main__":
    print("Processing picking")
    
    # Delete Redis
    i = 0
    for key in STATION_CHANNELS.keys():
        location = ""
        if key in ['BAKI', 'KSI', 'MBJI', 'MNI', 'MTAI', 'PCI', 'PPJI', 'TARAI', 'TPI', 'WAMI']:
            location = "00"
        for key2 in STATION_CHANNELS[key]:
            station_id = f"IA.{key}.{location}.{key2}"
            print(station_id, redis_client.delete("ai_pick_"+station_id))


    for message in waveform_consumer:
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