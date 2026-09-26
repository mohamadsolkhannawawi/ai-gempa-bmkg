import numpy as np
import pandas as pd
import os, json, time, redis
from obspy import UTCDateTime
from kafka import KafkaConsumer, KafkaProducer
from dotenv import load_dotenv
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder
import random
import pymongo
import datetime
from bson import ObjectId
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc

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
MIN_STATION = 1
MIN_PICKS = 1
SAMPLE_RATE = 20
BUFFER_SIZE_SEC = 10
BUFFER_SIZE = BUFFER_SIZE_SEC * SAMPLE_RATE # 100 second
MAX_WORKERS = 10

# Instantiate some clients
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
pick_consumer = KafkaConsumer(PICK_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
db = mongodb_client[DB_NAME]
cluster_col = db['cluster']

# Logging DEBUG
TEXT = ""
datestring_insr = lambda t: t.strftime("%Y%m%d%H%M%S") + f"{int(t.microsecond//(1e+4) - (t.microsecond//(1e+4))%(100/SAMPLE_RATE)):02d}"
datestring = lambda t: t.strftime("%Y%m%d%H%M%S") + f"{int(t.microsecond//(1e+4)):02d}"

# Open a file in write mode then closed
def write(text, TEXT, filename='detection_logging'):
    TEXT += text+'\n'
    file = open(filename+".txt", "w")
    file.write(TEXT)
    file.close()
    return TEXT

def preprocessing(data):
    df = data.copy()
    # Convert timestamps to numerical values (e.g., seconds since the epoch)
    df['timestamp_numeric'] = df['timestamp'].apply(lambda x: UTCDateTime(x).timestamp).astype(int)
    df['station_id'] = df.apply(lambda x: x['network']+'_'+x['station'], axis=1)

    # Label encoding using scikit-learn
    label_encoder = LabelEncoder()
    df['station_id'] = label_encoder.fit_transform(df['station_id'])

    # Select processed features
    df = df[['station_id','timestamp_numeric']]
    return df.values

# TODO: currently only handles modeling algorithm
def modeling(data) -> np.ndarray:
    # TODO: handle data.value()

    # Standardize the data (important for DBSCAN)
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(data)

    # Perform DBSCAN clustering
    dbscan = DBSCAN(eps=0.5, min_samples=3)
    clusters = dbscan.fit_predict(scaled_data)

    return clusters

# TODO:  currently only handles cluster selection algorithm
def cluster_selection(data):
    clusters = data.groupby('cluster').agg(list)
    clusters = clusters[clusters['timestamp'].apply(lambda x: len(x)) >= MIN_PICKS].reset_index().to_dict('records')
    return clusters
        
def consume_pick(message):
    # Json load
    try:
        data = json.loads(message.value.decode('utf-8'))
        print(data)
    except:
        print("Redist is empty!")
        return

    # Store the data into buffer
    for picks in data['picks']:
        # t = UTCDateTime.now()
        index = "association:" + picks['_id']

        # TODO: this code is used to bypass the cluster without doing any other clustering algorithm
        # Save cluster to database
        db_cluster_data = {
            'pick_ids': [ObjectId(picks['_id'])],
            'origin_time': (UTCDateTime(picks['timestamp']) - 10).datetime,
            'rank': 1,
            'modified_by': None,
            'created_at': UTCDateTime().now().datetime
        }

        cluster_id = cluster_col.insert_one(db_cluster_data).inserted_id

        clusters = [
            {
                '_id': str(cluster_id), 
                'origin_time': [str(UTCDateTime(picks['timestamp']) - 10)],
                'rank': 1,
                'picks': [
                    {
                        '_id': picks['_id'],
                        'network': data['network'],
                        'station': data['station'],
                        'timestamp': picks['timestamp'],
                    }
                ],
                'modified_by': None,
            }
        ]
    
        producer.send(CLUSTER_TOPIC, json.dumps(clusters).encode())
        # redis_client.set(index, json.dumps(data), ex=BUFFER_SIZE_SEC)
    
    # Use SCAN command to iterate over all keys
    list_pick = []
    for key in redis_client.scan_iter("association:*"):
        cache : dict = json.loads(redis_client.get(key).decode())
        list_pick.append(cache)

    num_station = np.unique([p['network']+'.'+p['station'] for p in list_pick]).shape[0]
    
    print('num_station:', num_station)
    
    # Check for processing
    if num_station >= MIN_STATION:
        
        # Preprocessing from dataframe vectorization into clustering or prediction modeling
        df_pick = pd.DataFrame(list_pick)
        data = preprocessing(df_pick)
        labels = modeling(data).tolist()
        
        # Store cluster labels into dataframe
        df_pick['cluster'] = labels
        df_pick = df_pick[df_pick['cluster']>=0]

        print(df_pick.groupby('cluster').agg('count')[['timestamp']])
        
        # Cluster selection
        clusters = cluster_selection(df_pick)
        
        print("Produce clusters", clusters)

        producer.send(CLUSTER_TOPIC, json.dumps(clusters).encode())
    

if __name__ == "__main__":
    print("Processing association")
    jobs = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for message in pick_consumer:
            job = executor.submit(consume_pick, message)
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