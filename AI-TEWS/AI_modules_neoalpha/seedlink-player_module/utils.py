import os, json, time, glob, threading, csv, pymongo, redis
import numpy as np
import pandas as pd
from tqdm import tqdm
from obspy import UTCDateTime, Trace, read
from kafka import KafkaProducer
from pymongo import MongoClient
from obspy.clients.filesystem.sds import Client
from bson.objectid import ObjectId

# Main env filled with all similar env variables

kafka_host="10.68.11.21"
kafka_port="9999"
regional="user_player"

database_host="152.118.31.62"
database_port="23982"
database_name="sispro-tews_player"

redis_host="10.68.11.21"
redis_port="6380"

redis_host_fe="10.68.11.21"
redis_port_fe="6381"

waveform_topic="waveform_player"
arrival_waveform_topic='arrival_waveform'
pick_topic="pick"
cluster_topic="cluster"
origin_topic="origin"
arrival_pick_topic="arrival_pick"
event_topic="event"
relocation_topic="event_commit"
relocation_feedback_topic="event_commit_feedback"

DB_HOST = '152.118.31.62'
DB_PORT = 23982
client = MongoClient(DB_HOST, DB_PORT)
db = client['sispro-tews_player']

if regional:
    user_data = db["user"].find_one({"username": regional})
    station_ids = user_data["stations"]
    station_datas = pd.DataFrame([db["station"].find_one({'_id': ObjectId(station_id)}) for station_id in station_ids])


def get_local_data(stream_list):
    df_local = pd.DataFrame(stream_list, columns=['path'])
    df_local['key'] = df_local['path'].apply(lambda x: "_".join(x.split('/')[5].split('.')[:4])+'.csv')
    df_local['exist'] = df_local['key'].apply(lambda x: os.path.exists(f"{x}"))

    list_csv = glob.glob('sls/*_*_*_*.csv')
    for key in df_local[df_local['key'].isin(glob.glob('sls/*_*_*_*.csv'))]['key']:
        list_csv.remove(key)
    sampling_csv = pd.Series(list_csv).sample(df_local[df_local['exist']==False].shape[0], replace=True, random_state=42).tolist()

    df_local.loc[df_local['exist'] == False, 'key'] = sampling_csv

    return {k: pd.read_csv(v).apply(lambda x: (x['Starttime'], x['Endtime']), axis=1).tolist() for k,v in df_local.set_index('path')[['key']].to_dict('dict')['key'].items()}

def send_waveform(net, sta, cha, t0, t1, root):
    client = Client(sds_root=root)
    st = client.get_waveforms(net, sta, "*", cha, t0, t1).merge()
    print(net, sta, cha, t0, t1, UTCDateTime.now(), st[0].stats.starttime.strftime("%M:%S"), st[0].stats.npts)
    json_string = {
        "date": UTCDateTime.now().strftime("%Y-%m-%d"),
        "starttime": str(st[0].stats.starttime),
        "endtime": str(st[0].stats.endtime),
        "sampling_rate": st[0].stats.sampling_rate,
        "delta": st[0].stats.delta,
        "location": st[0].stats.location,
        "npts": st[0].stats.npts,
        "station": st[0].stats.station,
        "network": st[0].stats.network,
        "channel": st[0].stats.channel,
        "waveform": np.array(st[0].data[:]).tolist()
    }
    producer.send('waveform_player', json.dumps(json_string).encode())

def get_started_time(STARTTIME):
    # Get all data in this range
    while True:
        T_now = UTCDateTime.now()
        if T_now.strftime("%S") == "59":
            T_now = UTCDateTime(T_now.strftime("%Y-%m-%dT%H:%M:%S"))-30
            Delta_T = T_now - UTCDateTime(STARTTIME)
            break

    return Delta_T

def store(stream, r):

    trace = stream[0]
    # Convert the trace data to MiniSEED bytes
    mseed_data = trace.data.tobytes()

    # Convert the Stats object to a dictionary
    stats_dict = trace.stats.__dict__

    # Convert UTCDateTime objects to ISO 8601 strings
    stats_dict['starttime'] = str(stats_dict['starttime'])
    stats_dict['endtime'] = str(stats_dict['endtime'])
    stats_dict['mseed'] = ""

    # Serialize the header information to JSON
    header_json = json.dumps(stats_dict)

    # Add the MiniSEED data and header to Redis stream
    r.xadd("mseed_stream_"+trace.id, {"data": mseed_data})
    r.xadd("mseed_header_"+trace.id, {"data": header_json})

from datetime import datetime

def publish_redis_message(channel, message, redis_client):    
    # redis_client = redis.Redis(host=redis_host, port=int(redis_port), db=0)
    
    # Use a consistent key for storing messages
    list_key = f"{channel}_history"

    # Push the message to the list
    redis_client.rpush(list_key, message)
    
    # Set or reset the expiry time to 20 seconds
    redis_client.expire(list_key, 1800)
    
    # Publish the message to the channel
    redis_client.publish(channel, message)

def station_find_by_code_and_network_repository(db, code, network):
    station_collection = db['station']

    query = {
        'code': code,
        'network': network
        }

    document = station_collection.find_one(query)
    return document

def store_trace(trace, station_data, producer, r):
    today = datetime.utcnow().date()
    channel = trace.stats.network+"."+trace.stats.station+"."+trace.stats.location+"."+trace.stats.channel
    json_string = {
        "date":str(today),
        "starttime":str(trace.stats.starttime),
        "endtime":str(trace.stats.endtime),
        "sampling_rate": trace.stats.sampling_rate,
        "delta": trace.stats.delta,
        "location": trace.stats.location,
        "location_database":station_data["location"].values[0],
        "longitude":station_data["longitude"].values[0],
        "latitude":station_data["latitude"].values[0],
        "npts": trace.stats.npts,
        "station":trace.stats.station,
        "network":trace.stats.network,
        "channel":trace.stats.channel,
        "expiration_timestamp":int(time.time()) + 1800,
        "waveform":trace.data.tolist()
    }

    # Send a message to kafka
    producer.send(waveform_topic, json.dumps(json_string).encode())
    # Ensure all messages are sent and then close the producer
    producer.flush()
    
    print(f"Sent to kafka to {waveform_topic}", trace, UTCDateTime.now())
    
    # Downsample for frontend
    trace = trace.interpolate(sampling_rate=5) 
    
    # Send a message to FE redis
    json_string = {
        "date":str(today),
        "starttime":str(trace.stats.starttime),
        "endtime":str(trace.stats.endtime),
        "sampling_rate": trace.stats.sampling_rate,
        "delta": trace.stats.delta,
        "location": trace.stats.location,
        "location_database":station_data["location"].values[0],
        "longitude":station_data["longitude"].values[0],
        "latitude":station_data["latitude"].values[0],
        "npts": trace.stats.npts,
        "station":trace.stats.station,
        "network":trace.stats.network,
        "channel":trace.stats.channel,
        "expiration_timestamp":int(time.time()) + 1800,
        "waveform":trace.data.tolist()
    }
    publish_redis_message(channel, json.dumps(json_string), r)
    print(f"Sent to redis", trace, UTCDateTime.now())

def get_trace(trid, Delta_T, producer, r, r_fe, frac=1, NOWTIME=True):

    print("=== Getting from redis:", trid)

    # r = redis.Redis(host=redis_host, port=int(redis_port), db=0)
    station_data = station_datas[station_datas['code'] == trid.split('.')[1]]
    last_msg = "0"
    last_msg2 = "0"

    while True:
        try:
            # Read MiniSEED data from Redis stream
            data_stream_key = "mseed_stream_" + trid
            data_msg = r.xread({data_stream_key: last_msg}, count=1)

            if not data_msg:
                print("Station Ended!", trid)
                break

            data_msg_id, data_fields = data_msg[0][1][0]
            mseed_data = data_fields[b'data']

            # Read header from Redis stream
            header_stream_key = "mseed_header_" + trid
            header_msg = r.xread({header_stream_key: last_msg2}, count=1)

            if not header_msg:
                break

            header_msg_id, header_fields = header_msg[0][1][0]
            header_json = header_fields[b'data']

            # Decode the header information from JSON
            header = json.loads(header_json)

            # Convert MiniSEED data to numpy array
            data = np.frombuffer(mseed_data, dtype=np.int32)

            # Create a Trace object with data and header
            trace = Trace(data=data, header=header)

            last_msg = data_msg_id
            last_msg2 = header_msg_id

            if NOWTIME:
                trace.stats.starttime += Delta_T
                t_now = UTCDateTime.now()
                sleep_time = trace.stats.endtime - t_now
                if sleep_time > 0:
                    time.sleep(sleep_time*frac)
            else:
                t_now = UTCDateTime.now() - Delta_T
                sleep_time = trace.stats.endtime - t_now
                if sleep_time > 0:
                    time.sleep(sleep_time*frac)
            
            threading.Thread(target=store_trace, args=(trace, station_data, producer, r_fe)).start()
            # try:
            #     store_trace(trace, db, producer)
            # except:
            #     print("Error.......................", trace.id)
        except Exception as e:
            print("Error:", e)
            r = redis.Redis(host=redis_host, port=int(redis_port), db=0)
            r_fe = redis.Redis(host=redis_host_fe, port=int(redis_port_fe), db=0)
            continue

from pymongo import MongoClient
from bson import ObjectId
import pandas as pd

def set_db_all(FGSK):

    FGSK2 = []
    # Baca file excel
    df_iter = pd.read_excel("Station_BMKG_Now.xlsx")

    # Inisialisasi daftar
    station_list = []

    DICT_sta = pd.DataFrame({'Path':FGSK,
                  'Station':['.'.join(_.split('/')[-1].split('.')[:2]) for _ in FGSK], 
                  'Channel':[_.split('/')[-1].split('.')[3] for _ in FGSK]}).groupby('Station').agg(list).to_dict()

    # Loop melalui setiap baris dalam dataframe
    for index, row in df_iter.iterrows():
        if f"{row['#Network']}.{row['Station']}" in list(DICT_sta['Channel'].keys()):
            # Buat dictionary untuk setiap baris
            station_data = {
                "name": row['Station'] + ' (' + row['SiteName'] + ')',
                "code": row['Station'],
                "network": row['#Network'],
                "channel": DICT_sta['Channel'][f"{row['#Network']}.{row['Station']}"],  # Ganti sesuai data channel jika ada
                "location": "",
                "longitude": row['Longitude'],
                "latitude": row['Latitude'],
                "elevation": row['Elevation'],
                "server_seedlink": "localhost",
                "server_fdsn": "localhost"
            }
            FGSK2 += DICT_sta['Path'][f"{row['#Network']}.{row['Station']}"]
            # Tambahkan dictionary ke dalam list
            station_list.append(station_data)


    DB_HOST = '152.118.31.62'
    DB_PORT = 23982

    client = MongoClient(DB_HOST, DB_PORT)
    client.drop_database('sispro-tews_player')

    db = client['sispro-tews_player']

    # Insert all stations in starter_station_data 
    station_ids = db['station'].insert_many(station_list).inserted_ids

    # Define player user
    user = {
        "username": "user_player",
        "password": "$2y$10$M.KuKs6msFIMynE/yS15WOPd.99xcCidADgdjotqT/HKxf.iD3XA6",
        "region": "User Player",
        "stations": [
            ObjectId(station_id) for station_id in station_ids
        ],
        "role": "superadmin",
        "modules": {},
        "disable_stations": []
    }
    user_id = db['user'].insert_one(user).inserted_id

    return pd.Series(FGSK2).value_counts().index.tolist()

