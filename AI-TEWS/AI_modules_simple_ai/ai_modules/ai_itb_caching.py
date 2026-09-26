import os, redis, pymongo, threading, time, json
import numpy as np
import tensorflow as tf
from obspy import UTCDateTime, Trace
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer

from utils.messaging import json_serializer
from utils.preprocessing import trace_processing

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

REDIS_HOST = os.getenv("redis_host")
REDIS_PORT = os.getenv("redis_port")

# Kafka topics
WAVEFORM_TOPIC = os.getenv("waveform_topic")
PICK_TOPIC = os.getenv("pick_topic")
SAMPLE_RATE = 20
WINDOW_SIZE_SEC = 300
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE
OVERLAPS_SEC = 180
MAX_WORKER = 1000

# Instantiate some clients
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
waveform_consumer = KafkaConsumer(WAVEFORM_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])

def ai_itb_caching_process(trace, window_size, r):
    starttime = UTCDateTime(trace.stats.starttime)
    next_starttime = starttime + (trace.stats.delta*(trace.stats.npts))
    redis_key = f"ai_pick_{trace.stats.network}.{trace.stats.station}.{trace.stats.location}.{trace.stats.channel}" 
    redis_value = {"time": [str(starttime), str(next_starttime)],
                   "data": trace.data[:].tolist()
                   }
    # Store to redis
    r.xadd(redis_key, {"data": json.dumps(redis_value)})

    if r.get('flag_'+redis_key): return 0

    # Get all messages from the Redis stream
    messages = r.xrange(redis_key, "-", "+") 

    taken_starttime = starttime - (trace.stats.delta * (window_size))
    expired_time = starttime - int((trace.stats.delta * (window_size*5))) # expired in a day

    list_taken_time = []
    dict_taken_msg_id = {}
    dict_taken_data = {}
    
    for msg_id, fields in messages:
        # Extract the MiniSEED data and header from the message
        header_json = fields[b'data']
        
        # Decode the header information
        header = json.loads(header_json)
        _time = tuple(header['time'])
        _data = np.array(header['data'])

        # Take the needed data back selection
        if taken_starttime < UTCDateTime(_time[1]) or str(_time[1]) == str(next_starttime):
            # print("TAKEN =================", taken_starttime, _time)
            list_taken_time.append(_time)
            dict_taken_msg_id[_time] = msg_id
            dict_taken_data[_time] = _data
        
        elif expired_time > UTCDateTime(_time[1]):
            # print("DELETE =================", _time)
            r.xdel(redis_key, msg_id)

    segment_data = []

    if len(list_taken_time):
        # Check if missing then exit
        list_taken_time = sorted(list_taken_time)
        for lt,lr in zip(list_taken_time[:-1], list_taken_time[1:]):
            if abs(UTCDateTime(lt[1]) - UTCDateTime(lr[0])) > 1:
                return segment_data

        second_length = UTCDateTime(list_taken_time[-1][-1]) - UTCDateTime(list_taken_time[0][0])
        print(second_length)
        if second_length >= (trace.stats.delta * (window_size)):
            waveform_data = np.concatenate([dict_taken_data[key] for key in list_taken_time]).tolist()
            pick_waveform_data = {
                "starttime":str(list_taken_time[0][0]),
                "endtime":str(list_taken_time[-1][-1]),
                "sampling_rate": trace.stats.sampling_rate,
                "delta": trace.stats.delta,
                "location": trace.stats.location,
                "npts": len(waveform_data),
                "station": trace.stats.station,
                "network": trace.stats.network,
                "channel": trace.stats.channel,
                "waveform": waveform_data
            }
            print(trace.id, trace.stats.endtime)

            # TODO
            # producer.send(PICK_TOPIC, json.dumps(pick_waveform_data).encode())
            # diganti jadi hit API

            r.set('flag_'+redis_key, 1, ex=OVERLAPS_SEC)

def task(message):
    data = json_serializer(message)
    trace = trace_processing(data, SAMPLE_RATE)
    ai_itb_caching_process(trace, WINDOW_SIZE, redis_client)
    
if __name__ == "__main__":
    print("Store waveform")

    for key in redis_client.scan_iter('ai_pick_*'):
        redis_client.delete(key)

    for message in waveform_consumer:
        thread = threading.Thread(target=task, args=(message,))
        thread.start()
        thread.join(0)
        active_threads = threading.active_count()
        if active_threads > MAX_WORKER:
            print("System Overhead: Forced Stop!!!...............")
            break