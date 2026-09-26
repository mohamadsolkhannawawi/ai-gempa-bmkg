from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *
from skydrifter.PeculiarSupport.support import make_ot_df,make_at_df,polygon_contain,repair_region_string,decimaldegree_to_minutedegree,latlong_distance

import time

import pandas as pd
import geopandas as gpd
import obspy as op

from geopy.geocoders import Nominatim
from shapely.geometry import Point, Polygon, MultiPolygon, LineString
    
class SeisEventAnalyzer:
    def __init__(self,input):
        self.event = input
        self.stored_data = list(self.event.keys())

    def import_shp_data(self,path):
        self.shp_out_marine = gpd.read_file(path['World Marine'])
        self.gdf_out_marine = gpd.GeoSeries(self.shp_out_marine['geometry'])
        print(f"\rLoad Shapefile Data: Shape File Number {1} From {4} Total Shapefile Loaded | {(((1)/(4))*100):.2f} %",end=' ')
        self.shp_out_land = gpd.read_file(path['World Land'])
        self.gdf_out_land = gpd.GeoSeries(self.shp_out_land['geometry'])
        print(f"\rLoad Shapefile Data: Shape File Number {2} From {4} Total Shapefile Loaded | {(((2)/(4))*100):.2f} %",end=' ')
        self.shp_ind_land = gpd.read_file(path['Indonesia Land'])
        self.gdf_ind_land = gpd.GeoSeries(self.shp_ind_land['geometry'])
        print(f"\rLoad Shapefile Data: Shape File Number {3} From {4} Total Shapefile Loaded | {(((3)/(4))*100):.2f} %",end=' ')
        self.shp_ind_marine = gpd.read_file(path['Indonesia Marine'])
        self.gdf_ind_marine = gpd.GeoSeries(self.shp_ind_marine['geometry'])
        print(f"\rLoad Shapefile Data: Shape File Number {4} From {4} Total Shapefile Loaded | {(((4)/(4))*100):.2f} %",end=' ')

    def import_inventory_data(self,path):
        self.inventory = path

    def split_event_by_eventID(self,new_eventID):
        new_index = [find_index_list(new_eventID[i],self.event['eventID']) for i in range(0,len(new_eventID))]
        data_key = list(self.event.keys())
        new_event = {}
        for i in range(0,len(data_key)):
            new_event[data_key[i]] = [self.event[data_key[i]][j] for j in new_index]
        return new_event

    def get_region_data_ops(self):
        lat = self.event['latitude']
        long = self.event['longitude']
        reg,c = [],[]        
        for i in range(0,len(lat)):
            try:
                geoLoc = Nominatim(user_agent="GetLoc")
                locname = geoLoc.reverse(str(lat[i])+", "+str(long[i]))
                loc = locname.address
                loc = separate_by(locname.address,separator=',')
                region = repair_region_string(loc)[1]
                if region == 'Jawa':
                    region = repair_region_string(loc)[0]    
                country = repair_region_string(loc)[2]
            except:
                region = '-1'
                country = '-1'
            reg.append(region)
            c.append(country)
            print(f"\rGetting Region Data For All Event: Event Number {i+1} From {len(lat)} Total Event Available | {(((i+1)/len(lat))*100):.2f} %",end=' ')
        self.event['region'] = reg
        self.event['country'] = c

    def get_region_data_shp(self):
        lat = self.event['latitude']
        long = self.event['longitude']
        n = len(lat)
        r,sr,t,c = [],[],[],[]
        for i in range(0,n):
            point = Point(long[i],lat[i])
            region,sub_region = polygon_contain(point,self.shp_ind_land,self.gdf_ind_land)
            terrain = 'Land'
            country = 'Indonesia'
            if region == 'Unidentified':
                region,sub_region = polygon_contain(point,self.shp_ind_marine,self.gdf_ind_marine)
                terrain = 'Sea'
                country = 'Indonesia'
            if region == 'Unidentified':
                region,sub_region = polygon_contain(point,self.shp_out_land,self.gdf_out_land)
                terrain = 'Land'
                country = 'Non-Indonesia'
            if region == 'Unidentified':
                region,sub_region = polygon_contain(point,self.shp_out_marine,self.gdf_out_marine)
                terrain = 'Sea'
                country = 'Non-Indonesia'
            if region == 'Unidentified':
                terrain = 'Sea'
                country = 'Non-Indonesia'
            r.append(region)
            sr.append(sub_region)
            t.append(terrain)
            c.append(country)
            print(f"\rEvent Number {i+1} Processed From {n} Total Event | {(((i+1)/(n))*100):.2f} %",end=' ')
        self.event['region'] = r
        self.event['sub_region'] = sr
        self.event['terrain'] = t
        self.event['country'] = c

    def get_first_P_time_difference(self):
        df1 = make_ot_df(self.event)
        eventID_list = df1['EventID'].values
        first_P_difference = []
        for i in range(0,len(eventID_list)):
            df2 = make_at_df(data,eventID=eventID_list[i])
            first_P_difference_in_loop = []
            if len(df2) != 0:
                arrival_time = df2['P'].values
                first = op.UTCDateTime(np.min(np.delete(arrival_time, np.where(arrival_time == -1))))
                for j in range(0,len(arrival_time)):
                    if arrival_time[j] != -1:
                        first_P_difference_in_loop.append(abs(op.UTCDateTime(arrival_time[j]) - (first)))
                    elif arrival_time[j] == -1:
                        first_P_difference_in_loop.append(-1)
                first_P_difference.append(first_P_difference_in_loop)
            elif len(df2) == 0:
                first_P_difference.append(first_P_difference_in_loop)
            print(f"\rEvent Number {i+1} Processed From {len(eventID_list)} Total Event Available | {(((i+1)/len(eventID_list))*100):.2f} %",end=' ')
        self.event['first_P_time_difference'] = first_P_difference 
        
    def get_distance(self):
        df = self.inventory.copy()
        df1 = make_ot_df(self.event)
        eventID_list = df1['EventID'].values
        event_latitude = list(df1['Y'].values)
        event_longitude = list(df1['X'].values)
        distance = []
        for i in range(0,len(df1)):
            df2 = make_at_df(self.event,eventID=eventID_list[i])
            distance_in_loop = []
            for j in range(0,len(df2)):
                try:
                    sta_latitude = df[df['Station'] == df2['Station'][j]]['Latitude'].values[0]
                    sta_longitude = df[df['Station'] == df2['Station'][j]]['Longitude'].values[0]
                    distance_in_loop.append(int(latlong_distance(event_latitude[i], sta_latitude, event_longitude[i], sta_longitude)))
                except:
                    distance_in_loop.append(-1)
            distance.append(distance_in_loop)
            print(f"\rEvent Number {i+1} Processed From {len(df1)} Total Event Available | {(((i+1)/len(df1))*100):.2f} %",end=' ')
        self.event['distance'] = distance
    
    def get_year(self):
        df1 = make_ot_df(self.event)
        year = []
        for i in range(0,len(df1)):
            year.append((op.UTCDateTime(df1['Origin Time'][i])).year)
            pp = (((i+1)/len(df1))*100)
            if pp == 1 or pp == 25 or pp == 50 or pp == 75 or pp == 100:
                print(f"\rEvent Number {i+1} Processed From {len(df1)} Total Event Available | {(((i+1)/len(df1))*100):.2f} %",end=' ')
        self.event['year'] = year

    def get_month(self):
        df1 = make_ot_df(self.event)
        month = []
        for i in range(0,len(df1)):
            month.append((op.UTCDateTime(df1['Origin Time'][i])).month)
            pp = (((i+1)/len(df1))*100)
            if pp == 1 or pp == 25 or pp == 50 or pp == 75 or pp == 100:
                print(f"\rEvent Number {i+1} Processed From {len(df1)} Total Event Available | {(((i+1)/len(df1))*100):.2f} %",end=' ')
        self.event['month'] = month

    def get_julday(self):
        df1 = make_ot_df(self.event)
        julday = []
        for i in range(0,len(df1)):
            julday.append((op.UTCDateTime(df1['Origin Time'][i])).julday)
            pp = (((i+1)/len(df1))*100)
            if pp == 1 or pp == 25 or pp == 50 or pp == 75 or pp == 100:
                print(f"\rEvent Number {i+1} Processed From {len(df1)} Total Event Available | {(((i+1)/len(df1))*100):.2f} %",end=' ')
        self.event['julday'] = julday
    
    def get_station_coordinate(self):
        df = self.inventory.copy()
        df1 = make_ot_df(self.event)
        eventID_list = df1['EventID'].values
        sta_lat,sta_lon = [],[]
        n = len(df1)
        for i in range(0,n):
            df2 = make_at_df(self.event,eventID=eventID_list[i])
            sta_lat_in_loop = []
            sta_lon_in_loop = []
            for j in range(0,len(df2)):
                try:
                    sta_latitude = df[df['Station'] == df2['Station'][j]]['Latitude'].values[0]
                    sta_longitude = df[df['Station'] == df2['Station'][j]]['Longitude'].values[0]
                    sta_lat_in_loop.append(sta_latitude)
                    sta_lon_in_loop.append(sta_longitude)
                except:
                    sta_lat_in_loop.append(-1)
                    sta_lon_in_loop.append(-1)
            sta_lat.append(sta_lat_in_loop)
            sta_lon.append(sta_lon_in_loop)
            print(f"\rEvent Number {i+1} Processed From {len(df1)} Total Event Available | {(((i+1)/len(df1))*100):.2f} %",end=' ')
        self.event['y_station'] = sta_lat
        self.event['x_station'] = sta_lon
    
    def get_distance_after_n_station(self,numbers_station):
        df1 = make_ot_df(self.event)
        eventID_list = df1['EventID'].values
        counter = []
        for i in range(0,len(df1)):
            df2 = make_at_df(data,eventID=eventID_list[i],additional=['distance','first_P_time_difference'])
            df2 = df2.sort_values(by=['First P Time Difference'])
            df2.index = [j for j in range(0,len(df2))]
            if len(df2) >= numbers_station:
                distance = df2['Distance'].values
                counter.append(df2['Distance'][numbers_station-1])
            elif len(df2) < numbers_station:
                counter.append(int(-1))
            print(f"\rEvent Number {i+1} Processed From {len(df1)} Total Event Available | {(((i+1)/len(df1))*100):.2f} %",end=' ')
        self.event['distance_after_'  + str(numbers_station) + '_station'] = counter

    def get_elapsed_time_after_n_station(self,numbers_station):
        df1 = make_ot_df(self.event)
        eventID_list = df1['EventID'].values
        counter = []
        for i in range(0,len(df1)):
            df2 = make_at_df(data,eventID=eventID_list[i],additional=['distance','first_P_time_difference'])
            df2 = df2.sort_values(by=['First P Time Difference'])
            df2.index = [j for j in range(0,len(df2))]
            if len(df2) >= numbers_station:
                difference = df2['First P Time Difference'].values
                counter.append(df2['First P Time Difference'][numbers_station-1])
            elif len(df2) < numbers_station:
                counter.append(int(-1))
            print(f"\rEvent Number {i+1} Processed From {len(df1)} Total Event Available | {(((i+1)/len(df1))*100):.2f} %",end=' ')
        self.event['elapsed_time_after_'  + str(numbers_station) + '_station'] = counter

    def get_arrival_counter_after_n_second(self,forward_time):
        df1 = make_ot_df(self.event)
        eventID_list = df1['EventID'].values
        counter = []
        for i in range(0,len(eventID_list)):
            df2 = make_at_df(data,eventID=eventID_list[i],additional=['distance','first_P_time_difference'])
            if len(df2) != 0:
                df2 = df2.sort_values(by=['First P Time Difference'])
                df2.index = [j for j in range(0,len(df2))]
                difference = df2['First P Time Difference'].values
                counter.append(np.size(np.where(difference < forward_time)))
            elif len(df2) == 0:
                counter.append(0)
            print(f"\rEvent Number {i+1} Processed From {len(df1)} Total Event Available | {(((i+1)/len(df1))*100):.2f} %",end=' ')
        self.event['arrival_counter_after_'  + str(forward_time) + '_second'] = counter

    def get_distance_after_n_second(self,forward_time):
        df1 = make_ot_df(self.event)
        eventID_list = df1['EventID'].values
        counter = []
        for i in range(0,len(eventID_list)):
            df2 = make_at_df(data,eventID=eventID_list[i],additional=['distance','first_P_time_difference'])
            if len(df2) != 0:
                df2 = df2.sort_values(by=['First P Time Difference'])
                df2.index = [j for j in range(0,len(df2))]
                distance = df2['Distance'].values
                difference = df2['First P Time Difference'].values
                counter.append(df2['Distance'][np.where(difference < forward_time)[0][-1]])
            elif len(df2) == 0:
                counter.append(-1)
            print(f"\rEvent Number {i+1} Processed From {len(df1)} Total Event Available | {(((i+1)/len(df1))*100):.2f} %",end=' ')
        self.event['distance_after_'  + str(forward_time) + '_second'] = counter

    def get_phase_completeness(self):
        n = len(self.event['eventID'])
        p_counter,s_counter = [],[]
        p_completness,s_completness = [],[]
        for i in range(0,n):
            dfa = make_at_df(self.event,index=i)
            total_event = len(dfa)
            p_counter_in_loop = total_event - len(dfa[dfa['P'] == -1])
            s_counter_in_loop = total_event - len(dfa[dfa['S'] == -1])
            s_counter.append(p_counter_in_loop)
            p_counter.append(s_counter_in_loop)
            p_completness.append(round((p_counter_in_loop / total_event) * 100,2))
            s_completness.append(round((s_counter_in_loop / total_event) * 100,2))
            print(f"\rEvent Number {i+1} Processed From {n} Total Event Available | {(((i+1)/(n))*100):.2f} %",end=' ')
        self.event['p_counter'] = p_counter
        self.event['s_counter'] = s_counter
        self.event['p_completeness'] = p_completness
        self.event['s_completeness'] = s_completness

    def get_tp_ts(self):
        df1 = make_ot_df(self.event)
        n = len(df1)
        eventID_list = df1['EventID'].values
        tp,ts = [],[]
        for i in range(0,len(eventID_list)):
            df1 = make_at_df(self.event,eventID=eventID_list[i])
            tp_in_loop = ['-1' if (df1['P'][j] == -1 or df1['P'][j] == '-1') else op.UTCDateTime(df1['P'][j]) - op.UTCDateTime(df1['Origin Time'][j]) for j in range(0,len(df1))]
            ts_in_loop = ['-1' if (df1['S'][j] == -1 or df1['S'][j] == '-1') else op.UTCDateTime(df1['S'][j]) - op.UTCDateTime(df1['Origin Time'][j]) for j in range(0,len(df1))]
            tp.append(tp_in_loop)
            ts.append(ts_in_loop)
            print(f"\rEvent Number {i+1} Processed From {n} Total Event Available | {(((i+1)/(n))*100):.2f} %",end=' ')
        self.event['tp'] = tp
        self.event['ts'] = ts

    def get_vpvs_ratio(self):
        df = make_ot_df(self.event)
        eventID_list = df['EventID'].values
        n = len(eventID_list)
        vpvs_ratio = []
        for i in range(0,n):
            df1 = make_at_df(self.event,pair_ps=True,eventID=eventID_list[i],additional=['tp','ts'])
            if len(df1) >= 3:
                try:
                    slope, intercept = np.polyfit((df1['Tp'].values).tolist(), (df1['Ts'].values-df1['Tp'].values).tolist(), 1)
                    vpvs_ratio.append(slope+1)
                except:
                    vpvs_ratio.append(-2)
            elif len(df1) < 3:
                vpvs_ratio.append(-1)
            print(f"\rEvent Number {i+1} Processed From {n} Total Event Available | {(((i+1)/(n))*100):.2f} %",end=' ')
        self.event['VpVs_ratio'] = vpvs_ratio
        
    def get_event_degree_minute(self):
        n = len(self.event['latitude'])
        lon_degree,lon_minute,lon_second = [],[],[]
        lat_degree,lat_minute,lat_second = [],[],[]
        for i in range(0,n):
            lon = self.event['longitude'][i]
            lat = self.event['latitude'][i]
            lon_degree_in_loop = float((separate_by(str(float(lon)),separator='.')[0]))
            lat_degree_in_loop = float((separate_by(str(float(lat)),separator='.')[0]))
            lon_minute_in_loop = float(join_by(['0',(separate_by(str(float(lon)),separator='.')[-1])],separator='.'))*60
            lat_minute_in_loop = float(join_by(['0',(separate_by(str(float(lat)),separator='.')[-1])],separator='.'))*60
            lon_second_in_loop = float(join_by(['0',(separate_by(str(float(lon_minute_in_loop)),separator='.')[-1])],separator='.'))*60
            lat_second_in_loop = float(join_by(['0',(separate_by(str(float(lat_minute_in_loop)),separator='.')[-1])],separator='.'))*60
            lon_degree.append(lon_degree_in_loop)
            lat_degree.append(lat_degree_in_loop)
            lon_minute.append(lon_minute_in_loop)
            lat_minute.append(lat_minute_in_loop)
            lon_second.append(lon_second_in_loop)
            lat_second.append(lat_second_in_loop)
            print(f"\rEvent Number {i+1} Processed From {n} Total Event Available | {(((i+1)/(n))*100):.2f} %",end=' ')
        self.event['lon_degree'] = lon_degree
        self.event['lat_degree'] = lat_degree
        self.event['lon_minute'] = lon_minute
        self.event['lat_minute'] = lat_minute
        self.event['lon_second'] = lon_second
        self.event['lat_second'] = lat_second

    def get_station_degree_minute(self):
        n = len(self.event['x_station'])
        lon_degree = []
        lon_minute = []
        lon_second = []
        lat_degree = []
        lat_minute = []
        lat_second = []
        for i in range(0,n):
            try:
                lon = np.array([decimaldegree_to_minutedegree(self.event['x_station'][i][j]) for j in range(0,len(self.event['x_station'][i]))])
                lat = np.array([decimaldegree_to_minutedegree(self.event['y_station'][i][j]) for j in range(0,len(self.event['y_station'][i]))])
                lon_degree_in_loop = lon[:,0].tolist()
                lon_minute_in_loop = lon[:,1].tolist()
                lon_second_in_loop = lon[:,2].tolist()
                lat_degree_in_loop = lat[:,0].tolist()
                lat_minute_in_loop = lat[:,1].tolist()
                lat_second_in_loop = lat[:,2].tolist()
                lon_degree.append(lon_degree_in_loop)    
                lon_minute.append(lon_minute_in_loop)
                lon_second.append(lon_second_in_loop)
                lat_degree.append(lat_degree_in_loop)
                lat_minute.append(lat_minute_in_loop)
                lat_second.append(lat_second_in_loop)
            except:
                lon_degree.append([-1 for j in range(0,len(self.event['x_station'][i]))])    
                lon_minute.append([-1 for j in range(0,len(self.event['x_station'][i]))])
                lon_second.append([-1 for j in range(0,len(self.event['x_station'][i]))])
                lat_degree.append([-1 for j in range(0,len(self.event['x_station'][i]))])
                lat_minute.append([-1 for j in range(0,len(self.event['x_station'][i]))])
                lat_second.append([-1 for j in range(0,len(self.event['x_station'][i]))])
            print(f"\rEvent Number {i+1} Processed From {n} Total Event Available | {(((i+1)/(n))*100):.2f} %",end=' ')
        self.event['x_station_degree'] = lon_degree        
        self.event['x_station_minute'] = lon_minute
        self.event['x_station_second'] = lon_second
        self.event['y_station_degree'] = lat_degree
        self.event['y_station_minute'] = lat_minute    
        self.event['y_station_second'] = lat_second
        
    def update_hypocenter(self,df,eventID_column,X_column,Y_column,Z_column):
        # Section 1
        df1 = make_ot_df(self.event)
        df2 = df.copy()
        eventID_list_old = (df1['EventID'].values) 
        eventID_list_new = (df2[eventID_column].values)
        update_index = []
        for i in range(0,len(eventID_list_new)):
            index = np.where(eventID_list_old == eventID_list_new[i])[0]
            if len(index.tolist()) != 0:
                update_index.append(index.tolist()[0])
            print(f"\r[Phase 1] Processed Data: Data Number {i+1} From {len(eventID_list_new)} Total Data | {(((i+1)/len(eventID_list_new))*100):.2f} %",end=' ')
        update_index = list(set(update_index))
        # Section 2
        eventID_update = [eventID_list_old[update_index[i]] for i in range(0,len(update_index))]
        for i in range(len(update_index)):
            Y_new = ((df2[df2[eventID_column] == eventID_update[i]])[Y_column]).values[0]
            X_new = ((df2[df2[eventID_column] == eventID_update[i]])[X_column]).values[0]
            Z_new = ((df2[df2[eventID_column] == eventID_update[i]])[Z_column]).values[0]
            self.event['latitude'][update_index[i]] = Y_new
            self.event['longitude'][update_index[i]] = X_new
            self.event['depth'][update_index[i]] = Z_new
            print(f"\r[Phase 2] Processed Data: Data Number {i+1} From {len(update_index)} Total Data | {(((i+1)/len(update_index))*100):.2f} %",end=' ')
        # Section 3
        hypocenter_status = ['Unupdated' for i in range(0,len(df1))]
        for i in range(0,len(update_index)):
            hypocenter_status[update_index[i]] = 'Updated'
        self.event['hypocenter_status'] = hypocenter_status