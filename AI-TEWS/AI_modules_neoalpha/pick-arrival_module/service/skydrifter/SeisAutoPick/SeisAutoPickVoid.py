from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *
from skydrifter.PeculiarSupport.obspy_support import convert_timestamp
from skydrifter.PeculiarSupport.pytorch_support import pytorch_predict

import numpy as np
import obspy as op

class SeisAutoPickVoid:
    def __init__(self,stream):
        self.stream = stream
        
    def execute(self,candidate,model,expansion=5,probability_limit=0.25):
        all_pick = []
        for i in range(0,len(candidate)):
            # Section 1
            time = candidate[i]
            stn_copy1 = self.stream.copy()
            stn_copy1.resample(sampling_rate=20)
            stn_copy1.detrend()
            start = op.UTCDateTime(time) - ((stn_copy1[0].stats.delta)*1500)*expansion
            end = op.UTCDateTime(time) + (((stn_copy1[0].stats.delta)*1500))*expansion
            stn_copy1 = stn_copy1.trim(starttime=start,endtime=end)
            # Section 2
            pick = []
            converted_t = convert_timestamp(stn_copy1[0])
            s_index,e_index = sliding_index(stn_copy1[0].data,window=3001,overlap_point=2500)
            count = 0
            for rolling_index in range(0,len(s_index)):
                try:
                    y = pytorch_predict(stn_copy1,model,s_index[rolling_index],e_index[rolling_index])
                    now_t = converted_t[s_index[rolling_index]:e_index[rolling_index]]
                    index_t = (np.where(y > probability_limit)[0]).tolist()
                    possible_pick = [now_t[index_t[i]] for i in range(0,len(index_t))]
                    pick.append((possible_pick[int(len(possible_pick)/2)]))
                    count += 1
                except:
                    pass
            # Section 3
            if len(pick) != 0:
                pick = np.mean(pick)
            elif len(pick) == 0:
                pick = -1
            all_pick.append(pick)
        return all_pick