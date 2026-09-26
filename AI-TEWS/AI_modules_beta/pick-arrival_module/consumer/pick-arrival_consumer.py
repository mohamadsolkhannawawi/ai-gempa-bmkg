import os, redis, pymongo, threading, json, requests
import numpy as np
from obspy import UTCDateTime
from dotenv import load_dotenv
from kafka import KafkaConsumer, KafkaProducer
from datetime import datetime
from bson.objectid import ObjectId

from utils.messaging import json_serializer, store_trace_data, delete_temporary, ts_transform
from utils.preprocessing import trace_processing, waveform_preprocessing
      
from config import *

POOL = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=0)
redis_client = redis.StrictRedis(connection_pool=POOL)
mongodb_client = pymongo.MongoClient(host=MONGO_HOST, port=int(MONGO_PORT))
waveform_consumer = KafkaConsumer(WAVEFORM_TOPIC, bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"]) # TODO: currently listens to player
producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"], max_block_ms=120000)
db = mongodb_client[DB_NAME]
pick_col = db['pick']
station_col = db['station']

# TODO
### DUMMY
STADICT = {}
for sta in list(db['user'].find({"username":USER_NAME}))[0]['stations']:
    station = db['station'].find_one({"_id":ObjectId(sta)})
    try:
        # Filter channels (BH and SH)
        station['channel'] = sorted([ch for ch in station['channel'] if 'BH' in ch or 'SH' in ch])[0][:-1]
        code = station['network']+'_'+station['code']+'_'+str(station['channel'])
        STADICT[code] = 1
    except: pass
###

print(f"Nginx to: {NGINX_PREDICT_URL}")
print(f"Kafka to: {KAFKA_HOST}:{KAFKA_PORT}")
print(f"MongoDB to: {MONGO_HOST}:{MONGO_PORT}")

def task(message): 
    data = json_serializer(message)

    # TODO
    ### SPECIFIC USER
    try: STADICT[f"{data['network']}_{data['station']}_{data['channel'][:-1]}"]
    except: return 0 
    ###
    # if data['station'] not in ['MBBI','EGSI','BMSI','APSSI','ULSM','MKSM','PPSM','BOSM','UTSI','PPLI','CGJI','JBJI']: return 0
    if data['station'] not in ['MBBI','EGSI','BMSI','PPLI','CGJI','JBJI']: return 0

    trace = trace_processing(data, SAMPLE_RATE)
    trace = waveform_preprocessing(trace)
    store_trace_data(trace.id, trace.stats.starttime, trace.stats.endtime, trace.data.tolist(), redis_client)
    if trace.stats.channel[-1] == 'Z':
        if  not redis_client.get('flag_pick_'+trace.id):
            try: print(requests.post(NGINX_PREDICT_URL, json=data).json())
            except Exception as e: print('ERROR REQUEST or JSON! message:', e)
            redis_client.set('flag_pick_'+trace.id, 1, ex=OVERLAPS_SEC)
    if not redis_client.get("flag_delete_"+trace.id):
        redis_client.set("flag_delete_"+trace.id, 1, ex=EXPIRED_CACHE)
        try:
            true_delete, true_delete_ts = delete_temporary(trace.id, trace.stats.endtime, redis_client, expired=EXPIRED_CACHE-1)
            print("Delete temporary:", trace.id, true_delete, true_delete_ts)
        except: 
            pass

if __name__ == "__main__":
    for message in waveform_consumer:
        thread = threading.Thread(target=task, args=(message,)).start()