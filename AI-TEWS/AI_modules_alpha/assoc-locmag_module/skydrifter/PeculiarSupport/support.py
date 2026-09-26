from skydrifter.Utils.nonpartisan import *
from skydrifter.Utils.partisan import *

import string
import numpy as np
import pandas as pd
import geopandas as gpd
import obspy as op

from math import radians, cos, sin, asin, sqrt
from geopy.geocoders import Nominatim
from shapely.geometry import Point, Polygon, MultiPolygon, LineString

# Group 1
# all functions in this group have general functionality to support skydrifter package
def make_ot_df(data,additional=[],n=True):
    if n == True:
        n = len(data['eventID'])
    df = pd.DataFrame()
    df['EventID'] = data['eventID'][0:n]
    df['Origin Time'] = data['origin_time'][0:n]
    df['X'] = data['longitude'][0:n]
    df['Y'] = data['latitude'][0:n]
    df['Z'] = data['depth'][0:n]
    for i in range(0,len(additional)):
        try:
            try:
                additional_column = join_by(separate_by(additional[i],'_'),separator=' ').title()
            except:
                additional_column = additional[i].title()
            df[additional_column] = data[additional[i]][0:n]
        except:
            pass
    return df

def make_at_df(data,pair_ps=False,additional=[],**kwargs):
    try:
        index = np.where(np.array(data['eventID']) == kwargs['eventID'])[0][0]
    except:
        index = kwargs['index']
    station_event = data['station'][index]
    phase_event = data['phase'][index]
    at_event = data['arrival_time'][index]
    n = len(station_event)
    p_index,s_index = [],[]
    station_event_unq = np.unique(station_event)
    for i in station_event_unq:
        for j in ['P','S']:
            count = 0
            for k in range(0,n):
                if station_event[k] == i and phase_event[k] == j and j == 'P':
                    count += 1
                    p_index.append(at_event[k])
                    break
                elif station_event[k] == i and phase_event[k] == j and j == 'S':
                    count += 1
                    s_index.append(at_event[k])
                    break
            if k+1 == n and j == 'P' and count != 1:
                p_index.append(-1)
            elif k+1 == n and j == 'S' and count != 1:
                s_index.append(-1)
    df = pd.DataFrame()
    df['EventID'] = [data['eventID'][index] for i in range(0,len(station_event_unq))]
    df['Origin Time'] = [data['origin_time'][index] for i in range(0,len(station_event_unq))]
    df['Station'] = station_event_unq
    df['P'] = p_index
    df['S'] = s_index
    for i in range(0,len(additional)):
        try:
            try:
                additional_column = join_by(separate_by(additional[i],'_'),separator=' ').title()
            except:
                additional_column = additional[i].title()
            df[additional_column] = data[additional[i]][index]
        except:
            pass
    if pair_ps == False:
        return df
    elif pair_ps == True:
        n_index = []
        y_index = []
        for i in range(0,len(df)):
            logic1 = df['P'][i] == '-1' or df['S'][i] == '-1' 
            logic2 = df['P'][i] == -1 or df['S'][i] == -1
            if logic1 == True or logic2 == True:
                n_index.append(i)
            else:
                y_index.append(i)
        df_pair_ps = (df.iloc[y_index, :]).copy()
        df_pair_ps.index = [i for i in range(0,len(df_pair_ps))]
        return df_pair_ps

def make_all_at_df(data,additional):
    n = len(data['eventID'])
    dfa1 = make_at_df(data,index=0,additional=additional)
    dfa2 = make_at_df(data,index=1,additional=additional)
    dfa = pd.concat([dfa1,dfa2])
    for i in range(3,n):
        dfa_in_loop = make_at_df(data,index=i,additional=additional)
        dfa = pd.concat([dfa,dfa_in_loop])
        print(f"\rEvent Number {i+1} Processed From {n} Total Event Available | {(((i+1)/(n))*100):.2f} %",end=' ')
    dfa.index = [i for i in range(0,len(dfa))]
    return dfa
   
""" 
def access_single_waveform(df,data,year,julday,station):
    # Section 1 Dataframe Preparation
    df1 = df.copy()
    df1 = df1[df1['Year'] == year]
    df1 = df1[df1['Julian Day'] == julday]
    df1 = df1[df1['Station'] == station]
    # Section 2 Acces Waveform
    index_stream = np.unique(df1['Index Stream'].values).tolist()
    stream_now = op.Stream()
    for i in range(0,len(index_stream)):
        df2 = df1[df1['Index Stream'] == index_stream[i]]
        index_trace = (df2['Index Trace'].values).tolist()
        mseed_path = data['filepath'][index_stream[i]]
        stn = op.read(mseed_path)
        for j in range(0,len(index_trace)):
            stream_now += stn[index_trace[j]]
    return stream_now
"""
  
def access_single_waveform(data,station):
    stream_now = op.Stream()
    paths = [path for path in data['filepath'] if station in path]
    for path in paths:
        stn = op.read(path)
        for j in range(0,len(stn)):
            stream_now += stn[j]
    return stream_now
# Group 1

# Group 2
# all functions in this group have specific functionality to only specific class in skydrifter package
def polygon_contain(point,shp,gdf):
    for i in range(0,len(gdf)):
        logic = gdf[i].contains(point)
        if logic == True:
            region = string.capwords(shp['Region'][i])
            sub_region = string.capwords(shp['Sub Region'][i])
            break
        if i == len(gdf)-1 and logic == False:
            region = 'Unidentified'
            sub_region = 'Unidentified'
    return region,sub_region

def repair_region_string(input):
    input = [remove_cover_whitespace(input[i]) for i in range(0,len(input))]
    if isStringNumber(input[-2]) == True:
        input.pop(-2)
    output = input[len(input)-3:len(input)]
    return output

def decimaldegree_to_minutedegree(x):
    degree = float((separate_by(str(float(x)),separator='.')[0]))
    minute = float(join_by(['0',(separate_by(str(float(x)),separator='.')[-1])],separator='.'))*60
    second = float(join_by(['0',(separate_by(str(float(minute)),separator='.')[-1])],separator='.'))*60
    return degree,minute,second

def latlong_distance(lat1, lat2, lon1, lon2):
    lon1 = radians(lon1)
    lon2 = radians(lon2)
    lat1 = radians(lat1)
    lat2 = radians(lat2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * asin(sqrt(a))
    return(c * 6371)
# Group 2
