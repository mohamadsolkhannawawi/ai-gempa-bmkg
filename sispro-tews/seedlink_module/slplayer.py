import os, time, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from glob import glob
from datetime import datetime, timezone
from obspy import UTCDateTime, read

STARTTIME = "2019-07-14T05:30:00.000000Z"
ENDTIME = "2019-07-14T06:00:00.000000Z"

def get_local_archive():
    
    # Get all data in this range
    T = UTCDateTime(STARTTIME)

    root = '../'
    streams = [s.replace('\\','/').replace(root,'') for s in tqdm(sorted(glob(root+f'archive_local/*/*/*/*/*.{T.strftime("%Y.%j")}')))]

    station = np.unique(['_'.join(s.split('/')[2:4]) for s in streams])
    _length = {s:v for s,v in zip(station,np.random.randint(3, 43, len(station)).tolist())} 
    # _length = {s:v for s,v in zip(station,np.random.randint(30, 31, len(station)).tolist())} ## Debug

    timestamps = {}
    datalength = {}
    traces = {}
    for i,st in tqdm(enumerate(streams)):
        try:
            key = '_'.join(st.split('/')[2:5])
            datalength[key] = _length['_'.join(st.split('/')[2:4])]
            _info = read(root+st).merge()[0].stats
            starttime = _info.starttime + round((T - _info.starttime + _info.delta)//_info.delta)*_info.delta
            timestamps[key] = []
            traces[key] = read(root+st)
            cur_time = starttime

            while (cur_time <= UTCDateTime(ENDTIME) - datalength[key]):
                random_value = np.random.choice([0,0,0,0,np.random.randint(-5/_info.delta, 0/_info.delta)*_info.delta])
                t0, t1 = cur_time, cur_time + max(datalength[key]+random_value, 3) - _info.delta
                timestamps[key] += [(t0, t1)]
                cur_time += max(datalength[key]+random_value, 3)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(e)
    return traces, timestamps, datalength, root

def get_delay(folder):
    root = '../'
    PATHS = sorted(glob(root+folder+"/*/*/*/*/"))
    TIMES = [(
                datetime.fromtimestamp(
                    os.path.getctime(_+sorted([ps for ps in os.listdir(_) if '.mseed' in ps])[-1]), 
                    timezone.utc
                ).strftime('%H%M%S'),

                sorted([ps for ps in os.listdir(_) if '.mseed' in ps])[-1].split('_')[-2]
                
              ) for _ in PATHS]
    TIMES = [(datetime.strptime(i, "%H%M%S") - datetime.strptime(j, "%H%M%S")).total_seconds() for i,j in TIMES]
    print("Delay:",f"({len(PATHS)})",pd.DataFrame({'path':PATHS, 'delay':TIMES}).sort_values('delay', ascending=False).values.tolist())

def plot_monitor():
    # Load TIMESTAMP and DELTATIME back from JSON file
    with open('timestamps.json', 'r') as json_file:
        TIMESTAMP = json.load(json_file)
    with open('deltatime.json', 'r') as json_file:
        DELTATIME = json.load(json_file)

    # Collect data for visualization
    keys = np.intersect1d(np.array(list(TIMESTAMP.keys())), np.array(list(DELTATIME.keys())))
    start_times = [datetime.strptime(TIMESTAMP[k], "%Y-%m-%d %H:%M:%S") for k in keys]
    durations = [DELTATIME[k] for k in keys]

    # Plotting
    fig, ax = plt.subplots(figsize=(16, 8))
    ax.plot(start_times, durations, marker='.', color='b', alpha=0.5)
    ax.set_xlabel('Start Time')
    ax.set_ylabel('Duration (seconds)')
    ax.set_title('Thread Execution Visualization')
    
    # Add annotations for each point
    for i, txt in enumerate(keys):
        ax.annotate(f"({txt})", (start_times[i], durations[i]), textcoords="offset points", xytext=(0,10), ha='center', alpha=0.5)

    # Add text indicating the number of stations
    num_stations = len(keys)
    text = f'Instances: {num_stations}'
    ax.text(1.025, 1, text, transform=ax.transAxes, fontsize=12, verticalalignment='top')

    plt.grid(True)
    plt.tight_layout()
    plt.show()