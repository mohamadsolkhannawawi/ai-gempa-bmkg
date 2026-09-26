import numpy as np
import pandas as pd
import os, json, redis
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer
import asyncio
import traceback
from obspy import UTCDateTime
import tensorflow as tf
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
import pymongo
from bson import ObjectId
from joblib import load


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
CLUSTER_TOPIC = os.getenv("cluster_topic")
ARRIVAL_PICK_TOPIC = os.getenv("arrival_pick_topic")
EVENT_TOPIC = os.getenv("event_topic")

# Other constant
SAMPLE_RATE = 20
BUFFER_SIZE_SEC = 60
BUFFER_SIZE = BUFFER_SIZE_SEC * SAMPLE_RATE # 100 second
MODEL_PATH = "./models/cnnset_locmag_new.h5"
SCALER_PATH = "./models/minmax_scaler_new.joblib"
THMAG_PATH = "./models/th_mag.joblib"
DEGRE_CONVERSION = 111.139
MAX_WORKERS = 100

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
event_col = db['event']
magnitude_col = db['magnitude']

producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
cluster_consumer = KafkaConsumer(CLUSTER_TOPIC, 
                                    bootstrap_servers=f"{KAFKA_HOST}:{KAFKA_PORT}",
                                    auto_offset_reset='latest',
                                    enable_auto_commit=True)

# Logging DEBUG
TEXT = ""
datestring_insr = lambda t: t.strftime("%Y%m%d%H%M%S") + f"{int(t.microsecond//(1e+4) - (t.microsecond//(1e+4))%(100/SAMPLE_RATE)):02d}"
datestring = lambda t: t.strftime("%Y%m%d%H%M%S") + f"{int(t.microsecond//(1e+4)):02d}"

def run_async_func_in_thread(async_func, message):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_func(message))
    loop.close()

# Open a file in write mode then closed
def write(text, TEXT, filename='detection_logging'):
    TEXT += text+'\n'
    file = open(filename+".txt", "w")
    file.write(TEXT)
    file.close()
    return TEXT

def preprocessing(data):
    return data

# TODO: currently only handles modeling algorithm
def modeling(cluster, arrivals):
    # TODO: handle data.value()
    waveform = np.array([waveform for waveform in arrivals["waveform"].values()]).T
    print(waveform.shape)
    if len(waveform.shape)==1:
        waveform = np.expand_dims(waveform, axis=-1)
    if waveform.shape[-1]!=3:
        waveform = np.concatenate([waveform, waveform, waveform], axis=-1)
    
    ## Normalization
    normalize = lambda x: (x - x[0]) / 1000
    waveform = normalize(waveform)

    waveform = np.expand_dims(waveform, axis=0)
    print("waveform shape:", waveform.shape)
    
    model = tf.keras.models.load_model(MODEL_PATH)
    
    """
    prediction = model.predict(waveform)[0]
    denorm = lambda x, min_val, max_val: x * (max_val - min_val) + min_val

    # Define the minimum and maximum values as dictionaries
    min_values = {
        'longitude': 111.5,
        'latitude': -11.76,
        'depth': 10,
        'magnitude': 3
    }

    max_values = {
        'longitude': 115,
        'latitude': -5.5,
        'depth': 11,
        'magnitude': 6.5
    }

    # Convert dictionaries to arrays
    min_values = np.array([min_values['longitude'], min_values['latitude'], min_values['depth'], min_values['magnitude']])
    max_values = np.array([max_values['longitude'], max_values['latitude'], max_values['depth'], max_values['magnitude']])

    denorm_value = denorm(prediction, min_values, max_values)
    """

    # Scaler load
    scaler = load(SCALER_PATH)
    prediction = model.predict(waveform)
    denorm_value = scaler.inverse_transform(prediction)[0]

    prediction = [round(float(pred), 4) for pred in denorm_value]
    
    db_station = db["station"]

    station_data = db_station.find_one({'code': cluster['station']})
    print("station_datas", station_data)

    print("prediction", prediction)
    cluster['origin_time'] = str(UTCDateTime(cluster['timestamp']) - prediction[4]) 
    
    reg_th_mag = load(THMAG_PATH)

    event = {
        'cluster': cluster,
        'arrivals': arrivals['picks'],
        'longitude': round(station_data['longitude'] + (prediction[0] / DEGRE_CONVERSION), 6),
        'latitude': round(station_data['latitude'] + (prediction[1] / DEGRE_CONVERSION), 6),
        'depth': prediction[2],
        'magnitudes': [
            {
                'type': 'Mw',
                # 'value': prediction[3] if prediction[3]>=5 else reg_th_mag.predict(waveform.reshape((-1, 160*3)))[0],  
                'value': prediction[3],  
                'modified_by': None,
            }
        ],
        'modified_by': None,
    }
    return event


def get_locmag(cluster_data):
    try: 
        while True: # Loop check picks with delay
            for pick in cluster_data['picks']: 
                # Get pick ID
                pick_id = pick['_id']

                if redis_client.exists(f'arrival_pick:{pick_id}'): # P and S exists
                    # Get other data
                    network = pick['network']
                    station = pick['station']
                    timestamp = pick['timestamp']
                    origin_time = cluster_data['origin_time']

                    # Load arrival data and preprocess the waveform
                    arrival_data = json.loads(redis_client.get(f'arrival_pick:{pick_id}')) 
                    print("_id", cluster_data['_id'], "pick", pick_id, ": arrival exists!")
                    arrivals = preprocessing(arrival_data)
                    cluster = {
                        "_id": cluster_data['_id'],
                        "pick_ids": [pick_id],
                        "network": network,
                        "station": station,
                        "timestamp": timestamp,
                        "origin_time": origin_time
                    }
                    event = modeling(cluster, arrivals)
                    
                    # Insert magnitude to DB
                    db_magnitude_data = [
                        {
                            **magnitude_data,
                            "created_at": UTCDateTime().now().datetime
                        }
                        for magnitude_data in event['magnitudes']
                    ]
                    magnitude_ids = magnitude_col.insert_many(db_magnitude_data).inserted_ids

                    # Insert event to DB
                    db_event_data = {
                        # "name": geocoder.osm([event["latitude"], event["longitude"]], method='reverse'),
                        "name": "Earthquake " + str(UTCDateTime(timestamp) - 10),
                        **event,
                        "created_at": UTCDateTime().now().datetime
                    }

                    db_event_data['cluster'] = ObjectId(cluster_data['id'])
                    db_event_data['arrival_ids'] = [
                        ObjectId(arrival_pick['_id'])
                        for arrival_pick in arrivals['picks']
                    ]
                    db_event_data['magnitude_ids'] = magnitude_ids
                    del db_event_data['magnitudes']

                    event_id = event_col.insert_one(db_event_data).inserted_id

                    # Insert id to kafka data
                    event['_id'] = str(event_id)
                    for i, magnitude_id in enumerate(magnitude_ids):
                        event['magnitudes'][i]['_id'] = str(magnitude_id)

                    # Send data to kafka
                    print(event)
                    print("Sending to kafka...")
                    print("Done")
                    redis_client.delete(f"cluster:{cluster_data['_id']}")
                    redis_client.delete(f"arrival_pick:{pick_id}")

                    return event
                else:
                    pass
                    # print("id", cluster_data['id'], "pick", pick_id,": no arrival")
            if not redis_client.exists(f"cluster:{cluster_data['_id']}"):
                print(f"Exiting cluster {cluster_data['_id']}")
                break

    except Exception as e:
        print("Error get_locmag:", e)
        traceback.print_exc()

                    
def check_cluster(cluster_id=None):
    try:
        print(f"Cluster: Checking cluster {cluster_id}")
        cache_data = redis_client.get(f"cluster:{cluster_id}")
        if cache_data != None:
            cluster_data = json.loads(cache_data)
        event = get_locmag(cluster_data)
        
        if event != None:
            producer.send(EVENT_TOPIC, json.dumps(event).encode())

    except Exception as e:
        print("Error check_cluster:", e)
        traceback.print_exc()
        
# async def process_phase_arrival(message):
#     # Now only inserts the phase arrival to redis
#     data = json.loads(message.value.decode('utf-8'))
#     print(f"Phase {data['pick_source']}")

#     redis_client.set(f"arrival_pick:{data['pick_source']}", message.value, BUFFER_SIZE_SEC)

def process_cluster(message):
    data = json.loads(message.value.decode('utf-8'))
    for cluster_data in data:
        print(f"Cluster {cluster_data['id']}")
        redis_client.set(f"cluster:{cluster_data['id']}", json.dumps(cluster_data), ex=BUFFER_SIZE_SEC)
        check_cluster(cluster_id=cluster_data['id'])        
   

if __name__ == "__main__":
    print("Processing locmag")
   
    try:
        jobs = []
        with ThreadPoolExecutor(MAX_WORKERS) as executor:
            for message in cluster_consumer:
                job = executor.submit(process_cluster, message)
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
        print("Error consume_clusters:", e)
        traceback.print_exc()
    finally:
        if job != None:
            job.result()