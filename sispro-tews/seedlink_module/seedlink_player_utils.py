import json, time, glob
import numpy as np
from datetime import datetime
from obspy import UTCDateTime, Trace
from configuration.redis import redis_client as r
from configuration.redis import publish_redis_message
from repositories.station_repository import station_find_by_code_and_network_repository as find_sta

# import redis, os
# from dotenv import load_dotenv
# load_dotenv("./.env")
# redis_host = os.getenv('redis_host')
# redis_port = os.getenv('redis_port')
# # Connect to Redis
# r = redis.Redis(host='localhost', port=6379, db=0)

STARTTIME = "2019-07-14T01:00:00.000000Z"
ENDTIME = "2019-07-14T13:00:00.000000Z"

def get_started_time():
    # Get all data in this range
    while True:
        T_now = UTCDateTime.now()
        if T_now.strftime("%S") == "59":
            T_now = UTCDateTime(T_now.strftime("%Y-%m-%dT%H:%M:%S"))+1
            Delta_T = T_now - UTCDateTime(STARTTIME)
            break

    return Delta_T

def store_trace(trace, db, producer):
    today = datetime.utcnow().date()
    channel = trace.stats.network+"."+trace.stats.station+"."+trace.stats.location+"."+trace.stats.channel
    station_data = find_sta(db, trace.stats.station, trace.stats.network,)
    json_string = {
        "date":str(today),
        "starttime":str(trace.stats.starttime),
        "endtime":str(trace.stats.endtime),
        "sampling_rate": trace.stats.sampling_rate,
        # "record_length": trace.stats.number_of_records,
        "delta": trace.stats.delta,
        "location": trace.stats.location,
        "location_database":station_data["location"],
        "longitude":station_data["longitude"],
        "latitude":station_data["latitude"],
        "npts": trace.stats.npts,
        "station":trace.stats.station,
        "network":trace.stats.network,
        "channel":trace.stats.channel,
        "expiration_timestamp":int(time.time()) + 1800,
        "waveform":trace.data.tolist()
    }

    # Send a message to redis
    publish_redis_message(channel, json.dumps(json_string))

    # Send a message to kafka
    producer.produce('waveform_player',json.dumps(json_string))
    # Ensure all messages are sent and then close the producer
    producer.flush()
    print(trace)

def get_trace(trid, db, producer, Delta_T, NOWTIME=True):

    print("=== Getting from redis:", trid)

    last_msg = "0"
    last_msg2 = "0"

    while True:
        # Read MiniSEED data from Redis stream
        data_stream_key = "mseed_stream_" + trid
        data_msg = r.xread({data_stream_key: last_msg}, count=1)

        if not data_msg:
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
                time.sleep(sleep_time)
        else:
            t_now = UTCDateTime.now() - Delta_T
            sleep_time = trace.stats.endtime - t_now
            if sleep_time > 0:
                time.sleep(sleep_time)
           
        try:
            store_trace(trace, db, producer)
        except:
            print("Error.......................", trace.id)

def get_stream():
    # Get all data in this range
    T = UTCDateTime(STARTTIME)
    root = '../'
    streams = [s.replace('\\','/').replace(root,'') for s in sorted(glob.glob(root+f'archive_local/*/*/*/*/*.{T.strftime("%Y.%j")}'))]
    traceids = {tuple(tr.split('/')[-4:-1]): tr.split('/')[-1][:-9] for tr in streams}
    return traceids


# from seedlink_player_utils import get_started_time, get_trace, get_stream
# if seedlink_url=='localhost':
#     stid = get_stream()[(network, station, channel+'.D')]
#     Delta_T = get_started_time()
#     get_trace(stid, db, kafka_prod, Delta_T, NOWTIME=True)
#     break