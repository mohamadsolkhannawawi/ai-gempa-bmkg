import json
import numpy as np
from obspy import Stream, Trace, UTCDateTime
from obspy.clients.fdsn import Client as FDSNClient

from config import *

def ts_transform(x):
    return round(UTCDateTime(str(x)).timestamp*1000)

def get_channel_stream(key, endtime, window, r):
    stream = Stream()
    endtime = UTCDateTime(endtime)+1
    starttime = endtime-window
    messages = r.ts().range(key=key.replace('_data',''), 
                            from_time=ts_transform(str(starttime)),
                            to_time=ts_transform(str(endtime)))
    for i,(end,start) in enumerate(messages):
        data = r.hget(key, end)
        data = json.loads(data)['data']
        data = np.array(data)
        stats = key.split('_')[1].split('.')
        header = {
            'network': stats[0],
            'station': stats[1],
            'location': stats[2], 
            'channel': stats[3],
            'starttime': UTCDateTime(start/1000), 
            'endtime': UTCDateTime(end/1000), 
            'sampling_rate': SAMPLE_RATE, 
            'mseed': {"dataquality":'D'},
        }
        trace = Trace(data=data, header=header)
        stream.append(trace)

    try:
        stream.merge()
        stream[0].data = stream[0].data.filled(np.mean(stream[0].data))
    except:
        pass
    return stream

def convert_latitude_to_km(lat):
    return lat * 110.574

def convert_longitude_to_km(lon, lat):
    return lon * 111.320 * np.cos(np.radians(lat))

def get_channel_fdsn(network, code, location, channel, starttime, endtime, fdsn_server):
    stream = Stream()
    fdsn_client = FDSNClient(fdsn_server)
    try:
        stream = fdsn_client.get_waveforms(network, code, location, channel, starttime, endtime)
        stream.merge()
    except Exception as e:
        print(e)
    
    return stream