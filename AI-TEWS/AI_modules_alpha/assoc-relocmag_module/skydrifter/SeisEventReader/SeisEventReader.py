from skydrifter.SeisEventReader.CatalogueCollection import *

import numpy as np
import pandas as pd

catalogue_type = {
    "Seisan": "Catalogue_Seisan",
    "BMKG": "Catalogue_BMKG",
    "Seisgram": "Catalogue_Seisgram",
    "Japan": "Catalogue_Japan"
}

class SeisEventReader:
    def __init__(self,path,type):
        self.event = eval(catalogue_type[type] + '(path)')
        self.line_list = self.event.line_list
        self.index = self.event.get_index()
        self.date = self.event.get_date()
        self.unq_date = self.event.get_unq_date()
        self.date_count = self.event.get_date_count()
        self.eventIDlist,self.s_index,self.e_index = SeisEventReader.get_eventIDlist(self)

    def count(self):
        n_event = [len(self.date_count[i]) for i in range(0,len(self.date_count))]
        df = pd.DataFrame()
        df['Date'] = self.unq_date
        df['Total Event'] = n_event
        return df

    def get_eventIDlist(self):
        eventIDlist,s_index,e_index = [],[],[]
        n = len(self.index)
        for i in range(0,n):
            s_indx = self.index[i]
            if i+1 == n:
                e_indx = len(self.line_list)
            elif i+1 != n:
                e_indx = self.index[i+1]-1 
            eventIDlist.append(self.event.get_eventID(s_indx,e_indx,i))
            s_index.append(s_indx)
            e_index.append(e_indx)
        return eventIDlist,s_index,e_index
        
    def get_catalogue_per_event(self,s_indx,e_indx,idx):
        # String Data
        origin_time = self.event.get_origin_time(s_indx,e_indx,idx)
        eventID = self.event.get_eventID(s_indx,e_indx,idx)
        station = self.event.get_station(s_indx,e_indx,idx)
        phase = self.event.get_phase(s_indx,e_indx,idx)
        arrival_time = self.event.get_arrival_time(s_indx,e_indx,idx)
        # Number Data
        lat = float(self.event.get_latitude(s_indx,e_indx,idx))
        long = float(self.event.get_longitude(s_indx,e_indx,idx))
        depth = float(self.event.get_depth(s_indx,e_indx,idx))
        mag = float(self.event.get_magnitude(s_indx,e_indx,idx))
        return station,phase,origin_time,arrival_time,lat,long,depth,mag,eventID

    def get_catalogue_per_date(self,day_number):
        day_number = np.where(self.unq_date == day_number)[0][0]
        station, phase, origin_time, arrival_time, latitude, longitude, depth, magnitude, eventID = [], [], [], [], [], [], [], [], []
        for i in range(0,len(self.date_count[day_number])):
            idx = self.date_count[day_number][i]
            s_indx = self.index[idx]
            if idx+1 == len(self.index):
                e_indx = len(self.line_list)
            elif idx+1 != len(self.index):
                e_indx = self.index[idx+1]-1 
            s,p,ot,at,lat,long,d,mag,e = SeisEventReader.get_catalogue_per_event(self,s_indx,e_indx,idx)
            station.append(s)
            phase.append(p)
            origin_time.append(ot)
            arrival_time.append(at)
            latitude.append(lat)
            longitude.append(long)
            depth.append(d)
            magnitude.append(mag)
            eventID.append(e)
        data = {
            "eventID": eventID,
            "origin_time": origin_time,
            "longitude": longitude,
            "latitude": latitude,
            "depth": depth,
            "magnitude": magnitude,
            "station": station,
            "arrival_time": arrival_time,
            "phase": phase  
        }
        return data

    def get_all_catalogue(self,bulk_mode=False,**kwargs):
        n = len(self.unq_date)
        if n == 1:
            self.data = SeisEventReader.get_catalogue_per_date(self,self.unq_date[0])
            if bulk_mode == False:
                print(f"\rBuilding Data For All Event: Day Number {1} From {n} Total Day Available | {(((1)/n)*100):.2f} %",end=' ')
            elif bulk_mode == True:
                print(f"\r[{(((kwargs['i_bulk'])/kwargs['n_bulk'])*100):.2f} %] | Building Data For All Event: Day Number {1} From {n} Total Day Available | {(((1)/n)*100):.2f} %",end=' ')
        elif n == 2:
            self.data = merge_identical_dict(SeisEventReader.get_catalogue_per_date(self,self.unq_date[0]),SeisEventReader.get_catalogue_per_date(self,self.unq_date[1]))
        elif n >= 3:
            self.data = SeisEventReader.get_catalogue_per_date(self,self.unq_date[0])
            if bulk_mode == False:
                print(f"\rBuilding Data For All Event: Day Number {2} From {n} Total Day Available | {(((2)/n)*100):.2f} %",end=' ')
            elif bulk_mode == True:
                print(f"\r[{(((kwargs['i_bulk'])/kwargs['n_bulk'])*100):.2f} %] | Building Data For All Event: Day Number {2} From {n} Total Day Available | {(((2)/n)*100):.2f} %",end=' ')
            for i in range(1,n):
                self.data = merge_identical_dict(self.data,SeisEventReader.get_catalogue_per_date(self,self.unq_date[i]))
                if bulk_mode == False:
                    print(f"\rBuilding Data For All Event: Day Number {i+1} From {n} Total Day Available | {(((i+1)/n)*100):.2f} %",end=' ')
                elif bulk_mode == True:
                    print(f"\r[{(((kwargs['i_bulk'])/kwargs['n_bulk'])*100):.2f} %] | Building Data For All Event: Day Number {i+1} From {n} Total Day Available | {(((i+1)/n)*100):.2f} %",end=' ')

    def get_event_line_list(self,eventID):
        index = np.where(np.array(self.eventIDlist) == eventID)[0][0]
        return self.line_list[self.s_index[index]:self.e_index[index]]