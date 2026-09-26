from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *
from skydrifter.PeculiarSupport.geodesy_support import calculate_distance,calculate_coordinate,intersection
from skydrifter.PeculiarSupport.support import polygon_contain

import pandas as pd
import numpy as np

from itertools import combinations
from shapely.geometry import LineString, Point, MultiPoint
from math import radians, cos, sin, sqrt, atan2, degrees, asin

class SeisAutoLoc:
    def __init__(self,df_event,shp_dict):
        self.df_event = df_event
        self.shp = shp_dict

    def execute(self,autoloc_model1,autoloc_model2):
        # Phase 4 : Autoloc Epicenter
        # Feature Preparation
        self.df_event = self.df_event.loc[0:3]
        epicenter_feature = pd.DataFrame()
        reference = self.df_event.loc[0]
        for i in range(1,4):
            epicenter_feature['tp_' + str(i)] = [abs(self.df_event['P'].iloc[i]-reference['P'])]
        for i in range(1,4):
            epicenter_feature['ts_' + str(i)] = [abs(self.df_event['S'].iloc[i]-reference['S'])]
        for i in range(1,4):
            epicenter_feature['x_station_' + str(i)] = [self.df_event['X Station'].iloc[i]]
        for i in range(1,4):
            epicenter_feature['y_station_' + str(i)] = [self.df_event['Y Station'].iloc[i]]
        for i in range(1,4):
            epicenter_feature['ts_tp_' + str(i)] = [abs(self.df_event['S'].iloc[i]-self.df_event['P'].iloc[i])]
        # Generate Distance With AI Model
        d1 = autoloc_model1['model1'].predict(epicenter_feature)[0]
        d2 = autoloc_model1['model2'].predict(epicenter_feature)[0]
        d3 = autoloc_model1['model3'].predict(epicenter_feature)[0]
        d = [d1,d2,d3]
        # Distance Data Processing
        index_combine = list(combinations([i for i in range(1,3+1)],2))
        all_intersec = []
        for i in range(0,len(index_combine)):
            lat1, lon1, r1 = self.df_event['Y Station'].iloc[index_combine[i][0]], self.df_event['X Station'].iloc[index_combine[i][0]], d[index_combine[i][0]-1]
            lat2, lon2, r2 = self.df_event['Y Station'].iloc[index_combine[i][1]], self.df_event['X Station'].iloc[index_combine[i][1]], d[index_combine[i][1]-1]
            search_space = np.linspace(0,360,num=1000).tolist()
            line1_coords = [calculate_coordinate(lat1, lon1, r1, search_space[j]) for j in range(0,len(search_space))]
            line2_coords = [calculate_coordinate(lat2, lon2, r2, search_space[j]) for j in range(0,len(search_space))]
            intersection_point = intersection(line1_coords,line2_coords)
            all_intersec.append(intersection_point)
        all_intersec = merge_list(all_intersec)
        # Filter Intersection
        index_comb = list(combinations([i for i in range(1,len(all_intersec))],2))
        dd = [calculate_distance(all_intersec[index_comb[i][0]][1], all_intersec[index_comb[i][1]][1], all_intersec[index_comb[i][0]][0], all_intersec[index_comb[i][1]][0]) for i in range(0,len(index_comb))]
        df_temp = pd.DataFrame()
        df_temp['Index'] = index_comb
        df_temp['Distance'] = dd
        df_temp = df_temp[df_temp['Distance'] < 100]
        # Produce Latitude Longitude
        if len(df_temp) != 0:
            new_pair = df_temp['Index'].to_list()
            new_pair = [new_pair[i][0] for i in range(0,len(new_pair))] + [new_pair[i][1] for i in range(0,len(new_pair))]
            lat_pair = np.mean([all_intersec[new_pair[i]][1] for i in range(0,len(new_pair))])
            lon_pair = np.mean([all_intersec[new_pair[i]][0] for i in range(0,len(new_pair))])
        elif len(df_temp) == 0:
            lat_pair = -1
            lon_pair = -1
        
        # Phase 5 Define Latitude Longitude Detailed Location
        lat = lat_pair
        long = lon_pair
        point = Point(long,lat)
        region,sub_region = polygon_contain(point,self.shp['shp_ind_land'],self.shp['gdf_ind_land'])
        terrain = 'Land'
        country = 'Indonesia'
        if region == 'Unidentified':
            region,sub_region = polygon_contain(point,self.shp['shp_ind_marine'],self.shp['gdf_ind_marine'])
            terrain = 'Sea'
            country = 'Indonesia'
        if region == 'Unidentified':
            region,sub_region = polygon_contain(point,self.shp['shp_out_land'],self.shp['gdf_out_land'])
            terrain = 'Land'
            country = 'Non-Indonesia'
        if region == 'Unidentified':
            region,sub_region = polygon_contain(point,self.shp['shp_out_marine'],self.shp['gdf_out_marine'])
            terrain = 'Sea'
            country = 'Non-Indonesia'
        if region == 'Unidentified':
            terrain = 'Sea'
            country = 'Non-Indonesia'
        # Phase 6 : Autoloc Depth
        # Feature Preparation
        depth_feature = epicenter_feature.copy()
        depth_feature['Longitude'] = [lon_pair]
        depth_feature['Latitude'] = [lat_pair]
        depth_feature['Region'] = [region]
        depth_feature['Sub Region'] = [sub_region]
        depth_feature['Terrain'] = [terrain]
        # Depth Predict
        depth = autoloc_model2['model1'].predict(depth_feature)[0]
        # Make DataFrame
        self.df_loc = pd.DataFrame()
        self.df_loc['Longitude'] = [lon_pair]
        self.df_loc['Latitude'] = [lat_pair]
        self.df_loc['Depth'] = [depth]
        self.df_loc['Region'] = [region]
        self.df_loc['Sub Region'] = [sub_region]
        self.df_loc['Terrain'] = [terrain]
        self.df_loc['Country'] = [country]