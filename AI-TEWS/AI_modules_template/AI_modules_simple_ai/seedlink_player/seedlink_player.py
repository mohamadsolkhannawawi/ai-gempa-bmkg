import os, json, time, glob, threading
import numpy as np
import pandas as pd
from obspy import UTCDateTime, read
from kafka import KafkaProducer
from dotenv import load_dotenv
from obspy.clients.filesystem.sds import Client

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

STARTTIME = "2024-03-18T05:56:00.000000Z"
ENDTIME = "2024-03-18T06:15:00.000000Z"

producer = KafkaProducer(bootstrap_servers=[f"{KAFKA_HOST}:{KAFKA_PORT}"])

print("Processing...")

# Get all data in this range
T = UTCDateTime(STARTTIME)

root = '../../'
streams = [s.replace('\\','/').replace(root,'') for s in glob.glob(root+f'archive/*/*/*/*/*.{T.strftime("%Y.%j")}')]
print(len(streams))

station = np.unique(['_'.join(s.split('/')[2:4]) for s in streams])
_length = {s:v for s,v in zip(station,np.random.randint(3, 43, len(station)).tolist())}

timestamps = {}
datalength = {}
for i,st in enumerate(streams):
    datalength[st] = _length['_'.join(st.split('/')[2:4])]
    _info = read(root+st).merge()[0].stats
    starttime = _info.starttime + round((T - _info.starttime + _info.delta)//_info.delta)*_info.delta
    timestamps[st] = []
    cur_time = starttime

    while (cur_time <= UTCDateTime(ENDTIME) - datalength[st]):
        random_value = np.random.choice([0,0,0,0,np.random.randint(-5/_info.delta, 5/_info.delta)*_info.delta])
        timestamps[st] += [(cur_time, cur_time + max(datalength[st]+random_value, 3) - _info.delta)]
        cur_time += max(datalength[st]+random_value, 3)

def send_waveform(net, sta, cha, t0, t1):
    client = Client(sds_root=root+'archive')
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

def task(key):
    net, sta, cha = key.split('/')[2:5]
    cha = cha.split('.')[0]
    while True:
        if timestamps[key][0][1].strftime("%S") == UTCDateTime.now().strftime("%S"):
            break
    for i in range(len(timestamps[key])):
        t0, t1 =  timestamps[key][i]
        send_waveform(net, sta, cha, t0, t1)
        time.sleep(datalength[key])

threads = []
for key in timestamps:
    t = threading.Thread(target=task, args=(key,))
    threads.append(t)

# Run and wait for all threads to complete
for t in threads:
    t.start()
    t.join(0)