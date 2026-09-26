from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *
from skydrifter.SeisArchiveCollector.SeisStreamRecap import *
from skydrifter.TraceAttribute.TraceAttribute import *
from skydrifter.PeculiarSupport.obspy_support import convert_timestamp

import numpy as np
import pandas as pd

class SeisAutoDetect:
    def __init__(self,stream):
        self.stream = stream

    def execute(self):
        # Session 1
        recap = SeisStreamRecap(self.stream)
        instrument = np.unique(recap.get_detail_instrument()).tolist()
        if len(instrument) > 1:
            instrument = instrument[0]
        stn_copy1 = self.stream.copy()
        stn_copy1 = stn_copy1.select(channel=instrument[0][0:2]+'*')
        stn_copy1 = stn_copy1.select(channel='**Z')
        if len(stn_copy1) == 0:
            stn_copy1 = stn.copy()
            stn_copy1 = stn_copy1.select(channel=instrument[0][0:2]+'*')
            stn_copy1 = stn_copy1.select(channel='**E')
        if len(stn_copy1) == 0:
            stn_copy1 = stn.copy()
            stn_copy1 = stn_copy1.select(channel=instrument[0][0:2]+'*')
            stn_copy1 = stn_copy1.select(channel='**N')
        # Session 2
        trc = TraceAttribute(self.stream[0])
        trace = trc.instantaneous_amplitude()
        # Session 3
        converted_t = convert_timestamp(self.stream[0])
        s_index,e_index = sliding_index(trace,window=int(trace.stats.npts/10),overlap_point=0)
        signal_index = []
        value_index = []
        roll = []
        time = []
        for rolling_index in range(0,len(s_index)):
            mean_data = np.mean(trace.data)
            max_data = np.max(trace.data[s_index[rolling_index]:e_index[rolling_index]])
            now_data = trace.data[s_index[rolling_index]:e_index[rolling_index]]
            index_max = np.argmax(now_data)
            logic = max_data > (mean_data*2)
            if logic == True:
                now_t = converted_t[s_index[rolling_index]:e_index[rolling_index]]
                index_now_t = np.where(np.array(converted_t) == now_t[index_max])
                signal_index.append(index_now_t[0][0])
                value_index.append(max_data)
                roll.append(rolling_index)
                time.append(converted_t[index_now_t[0][0]])
        # Session 4
        df = pd.DataFrame()
        df['Rolling Index'] = roll
        df['Signal Index'] = signal_index
        df['Value Index'] = value_index
        df['Timestamp'] = time
        diff = [(df['Rolling Index'].iloc[i+1]-df['Rolling Index'].iloc[i]) for i in range(0,len(df)-1)]
        diff.insert(len(diff),1)
        status = []
        for i in range(0,len(diff)-1):
            if diff[i] == diff[i+1]:
                status.append(0)
            elif diff[i] != diff[i+1]:
                status.append(1)
        status.insert(0,1)
        df['Diff'] = diff
        df['Status'] = status
        df = df[df['Status'] == 1]
        signal_index = df['Signal Index'].tolist()
        value_index = df['Value Index'].tolist()
        timestamp = df['Timestamp'].tolist()
        return timestamp