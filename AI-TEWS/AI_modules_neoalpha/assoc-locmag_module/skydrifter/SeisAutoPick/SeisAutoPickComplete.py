from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *
from skydrifter.PeculiarSupport.support import make_ot_df,make_at_df,access_single_waveform
from skydrifter.PeculiarSupport.obspy_support import convert_timestamp,merge_overlap_traces
from skydrifter.PeculiarSupport.pytorch_support import pytorch_predict

import warnings
import copy
import numpy as np
import obspy as op

warnings.filterwarnings("ignore")

class SeisAutoPickComplete:
    def __init__(self,event,path_df,path_collector):
        self.event = event
        self.df = path_df
        self.collector = path_collector
        self.station_feature,self.event_feature = SeisAutoPickComplete.check_feature(self)

    def import_model(self,model,model_type):
        self.model = model
        self.model_type = model_type
        if model_type == 'P':
            self.opposite_model_type = 'S'
        elif model_type == 'S':
            self.opposite_model_type = 'P'

    def check_feature(self):
        key_name = list(self.event.keys())
        station_feature = []
        event_feature = []
        for i in range(0,len(key_name)):
            df = make_ot_df(self.event,n=5,additional=[key_name[i]])
            column_name = list(df.columns)
            logic = isinstance(df[column_name[-1]].iloc[0], list)
            if logic == True:
               station_feature.append(key_name[i])
            elif logic == False:
                event_feature.append(key_name[i])
        return station_feature,event_feature

    def save_opposite_station_feature(self,eventID):
        index = np.where(np.array(self.event['eventID']) == eventID)[0][0]
        opposite_index = (np.where(np.array(self.event['phase'][index]) == self.opposite_model_type)[0]).tolist()
        station_feature = ['station','arrival_time','phase']
        event_station_feature = {}
        for i in range(0,len(station_feature)):
            event_station_feature[station_feature[i]] = [self.event[station_feature[i]][index][j] for j in opposite_index]
        return event_station_feature

    def generate_single_station_pick(self,year,julday,station,ot,probability_limit=0.8,return_stream=False):
        # Section 1 Acces Waveform Based On Event
        stn = access_single_waveform(self.df,self.collector,year=year,julday=julday,station=station)
        st = op.UTCDateTime(ot) - (1*60)
        et = st + (5*60)
        # Section 2 Adjust Waveform
        stn_out = op.Stream()
        for channel in ['E','N','Z']:
            stn_copy = stn.select(channel='**' + channel).copy()
            try:
                stn_copy = merge_overlap_traces(stn_copy)
            except:
                pass
            for i in range(0,len(stn_copy)):
                logic1 = stn_copy[i].stats.starttime <= st
                logic2 = stn_copy[i].stats.endtime >= et
                logic3 = len(stn_copy[i].data) >= 3001
                if logic1 == True and logic2 == True and logic3 == True:
                    stn_out += stn_copy[i]
                    break
        stn_out.trim(starttime=st,endtime=et)
        if len(stn_out) > 3:
            raise Exception("Sorry, your data is missing or the requested data does not match the origin time")
        # Section 3 Predict Pick
        pick = []
        converted_t = convert_timestamp(stn_out[0])
        s_index,e_index = sliding_index(stn_out[0].data,window=3001,overlap_point=2500)
        for rolling_index in range(0,len(s_index)):
            try:
                y = pytorch_predict(stn_out,self.model,s_index[rolling_index],e_index[rolling_index])
                now_t = converted_t[s_index[rolling_index]:e_index[rolling_index]]
                index_t = (np.where(y > probability_limit)[0]).tolist()
                possible_pick = [now_t[index_t[i]] for i in range(0,len(index_t))]
                pick.append((possible_pick[int(len(possible_pick)/2)]))
            except:
                pass
        pick = op.UTCDateTime(np.mean(pick))
        if return_stream == True:
            return pick,stn_out
        elif return_stream == False:
            return pick
        
    def generate_single_event_pick(self,eventID,only_missing=True):
        dfa = make_at_df(self.event,eventID=eventID,additional=['year'])
        station_feature = ['station','arrival_time','phase']
        event_station_feature = SeisAutoPickComplete.save_opposite_station_feature(self,eventID=eventID)
        event_station_feature['pick_' + self.model_type + '_status'] = ['Default' for i in range(0,len(dfa))]
        event_station_feature['pick_status'] = 'Unupdated'
        pick_succes_count = 0
        for index in range(0,len(dfa)):
            year = dfa['Year'].iloc[index]
            julday = (op.UTCDateTime(dfa['Origin Time'].iloc[index])).julday
            station = dfa['Station'].iloc[index]
            ot = dfa['Origin Time'].iloc[index]
            if dfa[self.model_type].iloc[index] == -1:
                try:
                    pick = SeisAutoPickComplete.generate_single_station_pick(self,year=year,julday=julday,station=station,ot=ot,return_stream=False)
                    pick = join_by([pick.date.strftime('%Y:%m:%d'),'T',pick.time.strftime('%H:%M:%S')],separator='')
                    event_station_feature['station'].append(station)
                    event_station_feature['phase'].append(self.model_type)
                    event_station_feature['arrival_time'].append(pick)
                    event_station_feature['pick_' + self.model_type + '_status'][index] = 'Succes'
                    pick_succes_count += 1
                except:
                    event_station_feature['station'].append(station)
                    event_station_feature['phase'].append(self.model_type)
                    event_station_feature['arrival_time'].append(-1)
                    event_station_feature['pick_' + self.model_type + '_status'][index] = 'Fail'
            elif dfa[self.model_type].iloc[index] != -1:
                event_station_feature['station'].append(station)
                event_station_feature['phase'].append(self.model_type)
                event_station_feature['arrival_time'].append(dfa[self.model_type].iloc[index])
        if pick_succes_count != 0:
            event_station_feature['pick_status'] = 'Updated'
        return event_station_feature

    def generate_bulk_event_pick(self,only_missing=True):
        self.new_event = copy.deepcopy(self.event)
        self.new_event['pick_' + self.model_type + '_status'] = [[] for i in range(0,len(self.new_event['eventID']))]
        self.new_event['pick_status'] = []
        dfo = make_ot_df(self.event)
        eventID_list = dfo['EventID'].tolist()
        n = len(eventID_list)
        station_feature = ['station','arrival_time','phase','pick_' + self.model_type + '_status']
        for i in range(0,n):
            index = np.where(np.array(self.event['eventID']) == eventID_list[i])[0][0]
            event_station_feature = SeisAutoPickComplete.generate_single_event_pick(self,eventID=eventID_list[i])
            for j in range(0,len(station_feature)):
                self.new_event[station_feature[j]][index] = copy.deepcopy(event_station_feature[station_feature[j]])
            self.new_event['pick_status'].append(event_station_feature['pick_status'])
            print(f"\rPick Missing Phase: Data Number {i+1} From {n} Total Data | {(((i+1)/(n))*100):.2f} %",end=' ')