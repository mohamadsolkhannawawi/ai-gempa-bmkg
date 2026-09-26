import json, requests
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

def get_channel_fdsn(network, code, location, channel, starttime, endtime, fdsn_server):
    stream = Stream()
    fdsn_client = FDSNClient(fdsn_server)
    try:
        stream = fdsn_client.get_waveforms(network, code, location, channel, starttime, endtime)
        stream.merge()
    except Exception as e:
        print(e)
    
    return stream

def get_recordstream(network, code, location, channel, starttime, endtime, recorstream_server):
    stream = Stream()
    try:
        url = f"{recorstream_server}/api/v1/recordstream/get"
        params = {
            "year": starttime.year,
            "network": network,
            "station": code,
            "location": location,
            "channel": channel,
            "sds_type": "D",
            "doy": starttime.julday,
            "starttime": starttime.isoformat() + 'Z',
            "endtime": endtime.isoformat() + 'Z'
        }
        response = requests.get(url, params=params)
        if type(response.json()) == dict:
            if response.json().get('status', False) == True:
                header = {
                    **response.json()['data']
                }
                
                # Rename to match obspy format
                header['starttime'] = header['time_start']
                header['endtime'] = header['time_end']
                
                del header['waveform']
                del header['time_start']
                del header['time_end']
                
                # Create stream
                data = np.array(response.json()['data']['waveform'])
                trace = Trace(data=data, header=header)
                stream.append(trace)
                stream.merge()
        else:
            raise Exception(f"Data not found for {network}.{code} or request failed. Response:", response.content)
    except Exception as e:
        raise e
    
    return stream
