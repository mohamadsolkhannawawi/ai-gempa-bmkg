import os, json, glob, redis
import numpy as np
from tqdm import tqdm
from obspy import UTCDateTime, read
from seedlink_player_utils import STARTTIME, ENDTIME

from dotenv import load_dotenv

load_dotenv("./.env")

redis_host = os.getenv('redis_host')
redis_port = os.getenv('redis_port')

# Connect to Redis
r = redis.Redis(host=redis_host, port=int(redis_port), db=0)

def store(stream):
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
    
print("Processing...", STARTTIME, "to", ENDTIME)

# Get all data in this range
T = UTCDateTime(STARTTIME)

root = '../'
streams = [s.replace('\\','/').replace(root,'') for s in tqdm(sorted(glob.glob(root+f'archive_local/*/*/*/*/*.{T.strftime("%Y.%j")}')))]
print(len(streams))

station = np.unique(['_'.join(s.split('/')[2:4]) for s in streams])
_length = {s:v for s,v in zip(station,np.random.randint(3, 43, len(station)).tolist())}

timestamps = {}
datalength = {}
for i,st in tqdm(enumerate(streams)):
    stream = read(root+st).merge()
    datalength[st] = _length['_'.join(st.split('/')[2:4])]
    _info = stream[0].stats
    starttime = _info.starttime + round((T - _info.starttime + _info.delta)//_info.delta)*_info.delta
    timestamps[st] = []
    cur_time = starttime
    r.delete("mseed_stream_"+stream[0].id)
    r.delete("mseed_header_"+stream[0].id)

    while (cur_time <= UTCDateTime(ENDTIME) - datalength[st]):
        random_value = np.random.choice([0,0,0,0,np.random.randint(-5/_info.delta, 5/_info.delta)*_info.delta])
        (t0, t1) = (cur_time, cur_time + max(datalength[st]+random_value, 3) - _info.delta)
        timestamps[st] += [(t0, t1)]
        trs = stream.copy()
        trs = trs.trim(t0, t1).merge()
        try:
            store(trs)
        except:
            pass
        cur_time += max(datalength[st]+random_value, 3)

