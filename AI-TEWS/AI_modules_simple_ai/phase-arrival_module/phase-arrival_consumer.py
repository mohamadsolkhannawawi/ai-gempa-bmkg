from obspy import UTCDateTime
import os
from kafka import KafkaConsumer, KafkaProducer
from dotenv import load_dotenv
import redis
import numpy as np
import json
import pymongo
from bson import ObjectId
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
import traceback

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

REDIS_HOST = os.getenv("redis_host")
REDIS_PORT = os.getenv("redis_port")

MONGO_HOST = os.getenv("database_host")
MONGO_PORT = os.getenv("database_port")

DB_NAME = os.getenv("database_name")

ARRIVAL_WAVEFORM_TOPIC = os.getenv("arrival_waveform_topic")
ARRIVAL_PICK_TOPIC = os.getenv("arrival_pick_topic")

# Other constant
SAMPLE_RATE = 20
BUFFER_TIME_LIMIT = 60
WINDOW_SIZE_SEC = 8
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE
THRESHOLD = 0.9
MAX_WORKERS = 10

# Instantiate some clients
arrival_waveform_consumer = KafkaConsumer(ARRIVAL_WAVEFORM_TOPIC, bootstrap_servers=f"{KAFKA_HOST}:{KAFKA_PORT}")
producer = KafkaProducer(bootstrap_servers=f"{KAFKA_HOST}:{KAFKA_PORT}")
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
arrival_col = db['arrival']

def dummy_gen(length):
    # (data exponentially increases from 0 to 1)
    # Generate linearly spaced values in the logarithmic scale
    log_start = np.log(1e-8) # log 0 error
    log_stop = np.log(1)
    log_space = np.linspace(log_start, log_stop, length)

    # Convert back to the original scale using the exponential function
    exp_space = np.exp(log_space)
    return exp_space

def phase_pick(pick_id, station_as_key, data):
    arrival_waveform = data['waveform']
    starttime = UTCDateTime(data['starttime'])
    delta = data['delta']
    
    # Check if all channel match window size
    valid = True
    for waveform_value in arrival_waveform.values():
        print(f"Pick {pick_id}: {len(waveform_value)=}")
        if (len(waveform_value) < WINDOW_SIZE):
            valid = False    
            break

    if valid:
        for channel, waveform_value in arrival_waveform.items():
            arrival_waveform[channel[-1]] = waveform_value[:WINDOW_SIZE]

        # TODO: dummy data 
        p_result = np.concatenate([dummy_gen(40), dummy_gen(WINDOW_SIZE - 40)[::-1]])
        s_result = np.concatenate([dummy_gen(40), dummy_gen(WINDOW_SIZE - 40)[::-1]])
        
        thresholded_p = p_result >= THRESHOLD
        thresholded_s = s_result >= THRESHOLD

        p_idx = np.where(thresholded_p)[0][0]
        s_idx = np.where(thresholded_s)[0][0]

        p_timestamp = starttime + p_idx * delta
        s_timestamp = starttime + s_idx * delta

        print(f"arrival_waveform:{station_as_key}_{pick_id}")
        redis_client.delete(f"arrival_waveform:{station_as_key}_{pick_id}")
        print(list(redis_client.scan_iter(f"arrival_waveform:{station_as_key}*")))
        if len(list(redis_client.scan_iter(f"arrival_waveform:{station_as_key}*"))) == 0:
            print(f"Station {station_as_key} not picked, removing...")
            # redis_client.srem(f"picked_station", station) # TODO: uncomment this, debug as well

        return arrival_waveform, p_timestamp, s_timestamp
    else:
        print("Window not fit")
        return arrival_waveform, None, None

def send_to_kafka(pick_id, arrival_waveform, p_timestamp, s_timestamp):
    if p_timestamp != None and s_timestamp != None:
        print(arrival_waveform)
        # Insert arrivals to DB 
        db_p_data = {
            "pick_source_id": ObjectId(pick_id),
            "station_id": ObjectId(arrival_waveform['station_id']),
            "timestamp": p_timestamp.datetime,
            "phase_type": "P",
            "modified_by": None,
            "created_at": UTCDateTime().now().datetime
        }

        db_s_data = {
            "pick_source_id": ObjectId(pick_id),
            "station_id": ObjectId(arrival_waveform['station_id']),
            "timestamp": s_timestamp.datetime,
            "phase_type": "S",
            "modified_by": None,
            "created_at": UTCDateTime().now().datetime
        }

        p_arrival_id = arrival_col.insert_one(db_p_data).inserted_id
        s_arrival_id = arrival_col.insert_one(db_s_data).inserted_id

        # Send arrivals to kafka
        kafka_data = {
            'pick_source_id': pick_id,
            'waveform': arrival_waveform['waveform'],
            'station_id': arrival_waveform['station_id'],
            'network': arrival_waveform['network'],
            'station': arrival_waveform['station'],
            'picks': [
                {
                    '_id': str(p_arrival_id),
                    'timestamp': str(p_timestamp),
                    'type': 'P',
                    "modified_by": None,
                },
                {
                    '_id': str(s_arrival_id),
                    'timestamp': str(s_timestamp),
                    'type': 'S',
                    "modified_by": None,
                },
            ],
        }

        # Set pick arrival to buffer
        redis_client.set(f"arrival_pick:{pick_id}", json.dumps(kafka_data), BUFFER_TIME_LIMIT)

        producer.send(ARRIVAL_PICK_TOPIC, json.dumps(kafka_data).encode())
        print(f"Phase send for pick {pick_id}")

def consume_arrival_waveform(message):
    data = json.loads(message.value.decode())
    station_as_key = f"{data['network']}.{data['station']}"
    cache_data_key = redis_client.scan_iter(f"arrival_waveform:{station_as_key}*")

    # Push arrival waveform data to cache
    if 'pick_id' in data:
        # Initialize if new picking
        pick_id = data['pick_id']
        del data['pick_id']
        redis_client.set(f"arrival_waveform:{station_as_key}_{pick_id}", 
                            json.dumps(data),
                            ex=BUFFER_TIME_LIMIT)
                    
        # Get phase arrival picks and trimmed arrival waveform
        trimmed_arrival_waveform, p_timestamp, s_timestamp = phase_pick(pick_id, station_as_key, data)
        data['waveform'] = trimmed_arrival_waveform
        send_to_kafka(pick_id, data, p_timestamp, s_timestamp)
        
    else:
        # Push new waveform to cache if pick already exists
        for key in cache_data_key:
            cache_data = redis_client.get(key)
            if (cache_data != None):
                cache_data = json.loads(cache_data)
                
                channel = data['channel'][-1]
                cache_data['waveform'][channel] = cache_data['waveform'][channel] + cache_data['waveform'][channel]
                
                # if (cache_data['station_key'] == 'GE.JAGI.BHE'):
                #     print("*" *10)
                #     print(len(cache_data['waveform']))
                #     print("*" *10)

                # Get phase arrival picks and trimmed arrival waveform
                pick_id = key.decode().split('_')[-1]
                trimmed_arrival_waveform, p_timestamp, s_timestamp = phase_pick(pick_id, station_as_key, cache_data)
                cache_data['waveform'] = trimmed_arrival_waveform

                # Continue saving data if no picks yet
                if p_timestamp == None or s_timestamp == None:    
                    redis_client.set(key, json.dumps(cache_data), keepttl=True)

                send_to_kafka(pick_id, cache_data, p_timestamp, s_timestamp)
                
if __name__ == "__main__":
    print("Processing arrival")
    
    jobs = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for message in arrival_waveform_consumer:
            try:
                job = executor.submit(consume_arrival_waveform, message)
                jobs.append(job)

                if len(jobs) >= MAX_WORKERS:
                    # Using as_completed still produce memory leak because it copies the tasks in its process
                    # Would rather just wait all the available jobs in the workers instead
                    for job in jobs:
                        print("Deleting JOBS")
                        # Ensure job is finished
                        job.result()
                        jobs.remove(job)

                    # Delete all references to job
                    del jobs
                    jobs = []

                    # Collect garbages
                    gc.collect()
            except Exception as e:
                print("Error arrival consumer: ", e)
                traceback.print_exc()
