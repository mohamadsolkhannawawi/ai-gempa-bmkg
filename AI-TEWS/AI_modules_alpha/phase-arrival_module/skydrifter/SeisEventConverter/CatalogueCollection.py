from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *
from skydrifter.PeculiarSupport.support import access_single_waveform

import numpy as np
import obspy as op

class Catalogue_Seisgram:
    def convert_without_waveform(self,dfa,event):
        # Section 1 Convert Pick
        lines = []
        for i in range(0,len(dfa)):
            station = dfa['Station'].iloc[i]
            pick_p = op.UTCDateTime(dfa['P'].iloc[i])
            pick_s = op.UTCDateTime(dfa['S'].iloc[i])
            if dfa['P'].iloc[i] != -1 and dfa['P'].iloc[i] != '-1': 
                p_date = join_by((separate_by(pick_p.date.strftime('%Y:%m:%d'),separator=':')),separator='')
                p_hour = join_by((separate_by(pick_p.time.strftime('%H:%M'),separator=':')),separator='')
                p_secn = join_by([pick_p.time.strftime('%S'),str(pick_p.microsecond)[0:2]],separator='.')
                p_chan = 'BHZ'
                string = join_by([station,'?',p_chan,'?','P','?',p_date,p_hour,p_secn,'GAU','0.0','0.0','0.0','0.0'],separator=' ')
                lines.append(string)
            if dfa['S'].iloc[i] != -1 and dfa['S'].iloc[i] != '-1': 
                s_date = join_by((separate_by(pick_s.date.strftime('%Y:%m:%d'),separator=':')),separator='')
                s_hour = join_by((separate_by(pick_s.time.strftime('%H:%M'),separator=':')),separator='')
                s_secn = join_by([pick_s.time.strftime('%S'),str(pick_s.microsecond)[0:2]],separator='.')
                s_chan = 'BHE'
                string = join_by([station,'?',s_chan,'?','S','?',s_date,s_hour,s_secn,'GAU','0.0','0.0','0.0','0.0'],separator=' ')
                lines.append(string)
        # Section 2 Return Output
        return lines

    def convert_with_waveform(self,dfa,event,path_df,path_collector):
        # Section 1 Generate Waveform
        station_list = dfa['Station'].tolist()
        year = dfa['Year'].iloc[0]
        ot = op.UTCDateTime(dfa['Origin Time'].iloc[0])
        julday = ot.julday
        st = ot - (1*60)
        et = st + (5*60)
        stn_out = op.Stream()
        for i in range(0,len(station_list)):
            sta = dfa['Station'].iloc[i]
            stn = access_single_waveform(self.path_df,self.path_collector,year=year,julday=julday,station=sta)
            for channel in ['E','N','Z']:
                stn_copy = stn.select(channel='**' + channel).copy()
                try:
                    stn_copy = merge_overlap_traces(stn_copy)
                except:
                    pass
                for k in range(0,len(stn_copy)):
                    logic1 = stn_copy[k].stats.starttime <= st
                    logic2 = stn_copy[k].stats.endtime >= et
                    logic3 = len(stn_copy[k].data) >= 3001
                    if logic1 == True and logic2 == True and logic3 == True:
                        stn_out += stn_copy[k]
                        break
        removed_station = [i for i in dfa['Station'].tolist() if len(stn_out.select(station=i)) != 3]
        # Section 2 Convert Pick
        lines = Catalogue_Seisgram.convert_without_waveform(self,dfa,event)
        # Section 3 Return Output
        return lines,stn_out