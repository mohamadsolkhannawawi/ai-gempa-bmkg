from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *
from skydrifter.PeculiarSupport.support import make_ot_df,make_at_df

from itertools import combinations
import pandas as pd

class SeisTabularDataset:
    def input_dataframe(self,input):
        self.data = input

    def input_datadict(self,input):
        self.data_dict = input

    def check_feature(self):
        key_name = list(self.data_dict.keys())
        station_feature = []
        event_feature = []
        for i in range(0,len(key_name)):
            df = make_ot_df(self.data_dict,n=5,additional=[key_name[i]])
            column_name = list(df.columns)
            logic = isinstance(df[column_name[-1]].iloc[0], list)
            if logic == True:
               station_feature.append(key_name[i])
            elif logic == False:
                event_feature.append(key_name[i])
        return station_feature,event_feature

    def build_tabular_dataset(self,station_feature,event_feature,n_station,combination=False,max_allowed_combination=70,max_index_combinator=30):
        feature1,eventID_list_next = SeisTabularDataset.builder_algorithm_1(self,station_feature,event_feature,n_station,combination=combination,max_allowed_combination=max_allowed_combination,max_index_combinator=max_index_combinator)
        n = len(eventID_list_next)
        feature2 = []
        df1 = make_ot_df(self.data_dict,additional=event_feature)
        for i in range(0,n):
            df_in_loop = df1[df1['EventID'] == eventID_list_next[i]]
            column_name = list(df_in_loop.columns)[5:len(list(df_in_loop.columns))]
            feature2_in_loop = []
            for j in range(0,len(column_name)):
                feature2_in_loop.append(df_in_loop[column_name[j]].values[0])
            feature2.append(feature2_in_loop)
            print(f"\rEvent Number {i+1} Processed From {n} Total Event Available | {(((i+1)/(n))*100):.2f} %",end=' ')
        df3 = pd.DataFrame()
        count = 0
        for i in range(0,len(station_feature)):
            for j in range(0,n_station):
                df3[station_feature[i]+'_'+str(j+1)] = [feature1[i][count] for i in range(0,len(feature1))]
                count += 1
        for i in range(0,len(column_name)):
            df3[column_name[i]] = [feature2[j][i] for j in range(0,len(feature2))]
        self.data = df3

    def builder_algorithm_1(self,station_feature,event_feature,n_station,combination=False,max_allowed_combination=70,max_index_combinator=30):
        eventID_list = self.data_dict['eventID']
        feature1 = []
        eventID_list_next = []
        n = len(eventID_list)
        for i in range(0,n):
            df2 = make_at_df(self.data_dict,eventID=eventID_list[i],additional=station_feature,pair_ps=True)
            df2 = df2[df2['X Station'] != -1]
            if len(df2) >= n_station:
                df2.sort_values(by=['Tp'],inplace=True)
                df2.index = [i for i in range(0,len(df2))]
                df_index = list(df2.index)
                # Condition 1
                if combination == False:
                    df_index = list(df2.index)[0:n_station]
                elif combination == True:
                    df_index = list(df2.index)
                # Condition 2
                if len(df_index) > max_index_combinator:
                    df_index = [i for i in range(0,max_index_combinator)]
                elif len(df_index) <= max_index_combinator:
                    pass
                index_combination = list(combinations(df_index,n_station))
                # Condition 3
                n_comb = len(index_combination) 
                if n_comb > max_allowed_combination:
                    n_comb = max_allowed_combination
                for j in range(0,n_comb):
                    column_name = df2.columns[5:len(df2.columns)].tolist()
                    feature1_in_loop = [df2.iloc[list(index_combination[j])][column_name[k]].values.tolist() for k in range(0,len(column_name))]
                    feature1.append(merge_list(feature1_in_loop))
                    eventID_list_next.append(eventID_list[i])
                    print(f"\rEvent Number {i+1} Processed From {n} Total Event Available | {(((i+1)/(n))*100):.2f} % | {(((j+1)/len(index_combination))*100):.2f} % ",end=' ')
            elif len(df2) != 3:
                pass
        return feature1,eventID_list_next


    def calculate_vincenty_distance(self,latitude_station_name='y_station_',longitude_station_name='x_station_',latitude_event_name='Y_event',longitude_event_name='X_event'):
        from geopy.distance import geodesic
        dfc = self.data.copy()
        # Define Number of Station
        n_station = 0
        for i in range(0,len(list(dfc.columns))):
            if list(dfc.columns)[i][0:len(latitude_station_name)] == latitude_station_name:
                n_station += 1
        # Calculate Distance
        for i in range(1,n_station+1):
            distance = []
            for j in range(0,len(dfc)):
                lon_event = dfc[longitude_event_name].iloc[j]
                lat_event = dfc[latitude_event_name].iloc[j]
                lon_sta = dfc[longitude_station_name+str(i)].iloc[j]
                lat_sta = dfc[latitude_station_name+str(i)].iloc[j]
                event_coords = (lat_event, lon_event)
                sta_coords = (lat_sta, lon_sta)
                distance.append(geodesic(event_coords, sta_coords).kilometers)
                print(f"\r{i} of {n_station} | Event Number {j+1} Processed From {len(dfc)} Total Event Available | {(((j+1)/(len(dfc)))*100):.2f} %",end=' ')
            dfc['vincenty_distance_'+str(i)] = distance
        self.data = dfc

    def calculate_gcircle_distance(self,latitude_station_name='y_station_',longitude_station_name='x_station_',latitude_event_name='Y_event',longitude_event_name='X_event'):
        from geopy.distance import great_circle
        dfc = self.data.copy()
        # Define Number of Station
        n_station = 0
        for i in range(0,len(list(dfc.columns))):
            if list(dfc.columns)[i][0:len(latitude_station_name)] == latitude_station_name:
                n_station += 1
        # Calculate Distance
        for i in range(1,n_station+1):
            distance = []
            for j in range(0,len(dfc)):
                lon_event = dfc[longitude_event_name].iloc[j]
                lat_event = dfc[latitude_event_name].iloc[j]
                lon_sta = dfc[longitude_station_name+str(i)].iloc[j]
                lat_sta = dfc[latitude_station_name+str(i)].iloc[j]
                event_coords = (lat_event, lon_event)
                sta_coords = (lat_sta, lon_sta)
                distance.append(great_circle(event_coords, sta_coords).kilometers)
                print(f"\r{i} of {n_station} | Event Number {j+1} Processed From {len(dfc)} Total Event Available | {(((j+1)/(len(dfc)))*100):.2f} %",end=' ')
            dfc['gcircle_distance_'+str(i)] = distance
        self.data = dfc

    def calculate_haversine_distance(self,latitude_station_name='y_station_',longitude_station_name='x_station_',latitude_event_name='Y_event',longitude_event_name='X_event'):
        from geopy.distance import distance
        dfc = self.data.copy()
        # Define Number of Station
        n_station = 0
        for i in range(0,len(list(dfc.columns))):
            if list(dfc.columns)[i][0:len(latitude_station_name)] == latitude_station_name:
                n_station += 1
        # Calculate Distance
        for i in range(1,n_station+1):
            distance = []
            for j in range(0,len(dfc)):
                lon_event = dfc[longitude_event_name].iloc[j]
                lat_event = dfc[latitude_event_name].iloc[j]
                lon_sta = dfc[longitude_station_name+str(i)].iloc[j]
                lat_sta = dfc[latitude_station_name+str(i)].iloc[j]
                event_coords = (lat_event, lon_event)
                sta_coords = (lat_sta, lon_sta)
                distance.append(ditance(event_coords, sta_coords).kilometers)
                print(f"\r{i} of {n_station} | Event Number {j+1} Processed From {len(dfc)} Total Event Available | {(((j+1)/(len(dfc)))*100):.2f} %",end=' ')
            dfc['haversine_distance_'+str(i)] = distance
        self.data = dfc

    def update_event_feature(self,feature):
        dfc = self.data.copy()
        dfo = make_ot_df(self.data_dict,additional=[feature])
        eventID = dfc['Eventid'].values.tolist()
        n = len(eventID)
        feature = []
        for i in range(0,n):
            try:
                df_in_loop = dfo[dfo['EventID'] == eventID[i]]
                feature.append(df_in_loop[list(df_in_loop.columns)[-1]].iloc[0])
            except:
                feature.append('-1')    
            print(f"\rEvent Number {i+1} Processed From {n} Total Event Available | {(((i+1)/(n))*100):.2f} %",end=' ')
        self.data[list(df_in_loop.columns)[-1]] = feature