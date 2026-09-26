import os
import zipfile
import shutil
import time
import random

import numpy as np
import pandas as pd
import obspy as op

from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *
from skydrifter.PeculiarSupport.support import Point, polygon_contain
from obspy.taup import TauPyModel
from geopy.distance import geodesic

# Support Location Function
def create_latlon_grid(ref_lat, ref_lon, grid_size_lat, grid_size_lon, lat_spacing, lon_spacing):
    # Ensure the grid size is odd to have a center point
    assert grid_size_lat % 2 == 1, "grid_size_lat must be odd"
    assert grid_size_lon % 2 == 1, "grid_size_lon must be odd"
    # Generate latitude and longitude grid values
    lat_offsets = np.linspace(-lat_spacing*(grid_size_lat//2), lat_spacing*(grid_size_lat//2), grid_size_lat)
    lon_offsets = np.linspace(-lon_spacing*(grid_size_lon//2), lon_spacing*(grid_size_lon//2), grid_size_lon)
    # Create the grid
    lat_grid, lon_grid = np.meshgrid(ref_lat + lat_offsets, ref_lon + lon_offsets, indexing='ij')
    return lat_grid, lon_grid

def taupi_teoritical(eq_lat,eq_lon,eq_depth,sta_lat,sta_lon,model='ak135'):
    eq_coordinates = (eq_lat,eq_lon)  
    station_coordinates = (sta_lat,sta_lon) 
    distance_km = geodesic(eq_coordinates,station_coordinates).kilometers
    distance_deg = distance_km / 111.32 
    model = TauPyModel(model=model)
    arrival = {}
    try: arrival['P'] = model.get_travel_times(source_depth_in_km=eq_depth, distance_in_degree=distance_deg,phase_list=["P"])[0].time
    except: arrival['P'] = -1
    try: arrival['S'] = model.get_travel_times(source_depth_in_km=eq_depth, distance_in_degree=distance_deg,phase_list=["S"])[0].time
    except: arrival['S'] = -1
    return arrival

def rms_error(x_event, y_event, z_event, x_station, y_station, y_true):
    n = len(x_station)
    y_pred = np.array([taupi_teoritical(y_event,x_event,z_event,y_station[i],x_station[i],model='ak135')['P'] for i in range(0,n)])
    return np.sqrt(np.mean((y_true - y_pred)**2))

def pure_rms_error(y_true,y_pred):
    return np.sqrt(np.mean((y_true - y_pred)**2))

# Main Location Function List
# 1. NLLoc Global
# 2. Taup Inversion
def nlloc_global(dfa):
    # Path Config
    input_file = "/app/NonLinLoc/skydrifter_global_run_file"
    destination_folder = "/app/NonLinLoc/skydrifter_global_run_file"
    shutil.copytree("/app/skydrifter_global_run_file", "/app/NonLinLoc/skydrifter_global_run_file")
    
    # Input Pick
    all_string = []
    for i in range(0,len(dfa)):
        for j in ['P','S']:
            if dfa[j].iloc[i] != -1:
                if j == 'P':
                    timestamp = op.UTCDateTime(dfa[j].iloc[i])
                    string_join = join_by([dfa['Station'].iloc[i],'?','BHZ','?',j,'?',str(timestamp.strftime("%Y%m%d")),str(timestamp.strftime("%H%M")),str(timestamp.second),'GAU','0.0','0.0','0.0','0.0','\n'],separator=' ')
                    all_string.append(string_join)
                elif j == 'S':
                    timestamp = op.UTCDateTime(dfa[j].iloc[i])
                    string_join = join_by([dfa['Station'].iloc[i],'?','BHE','?',j,'?',str(timestamp.strftime("%Y%m%d")),str(timestamp.strftime("%H%M")),str(timestamp.second),'GAU','0.0','0.0','0.0','0.0','\n'],separator=' ')
                    all_string.append(string_join)
    write_line_list(output_file=destination_folder + '/obs/catalog2009-2020_opak.pick',line_list=all_string)
    # Input Station Coordinate
    all_string = []
    for i in range(0,len(dfa)):
        string_join = join_by(['LOCSRCE',dfa['Station'].iloc[i],'LATLON',str(dfa['Y Station'].iloc[i]),str(dfa['X Station'].iloc[i]),'0.0','0.0','\n'],separator=' ')
        all_string.append(string_join)
    write_line_list(output_file=destination_folder + '/run/sta_list_BMKG.in',line_list=all_string)
    # Run NLL
    os.system(f'NLLoc {input_file}/run/global_run.in')
    df = pd.read_csv(destination_folder + '/loc/simulasiBMKG.sum.grid0.loc.csv')
    shutil.rmtree(destination_folder)
    return df

def taup_inversion(dfa,n_station=5,alpha=0.005,z_event=15,max_iter=10):
	# Adjust dfa
    x_station = dfa['X Station'].to_numpy()[0:n_station]
    y_station = dfa['Y Station'].to_numpy()[0:n_station]
    y_true = dfa['Travel Time P'].to_numpy()[0:n_station]
    # Hyperparameters
    lat_max = np.max(y_station)+2
    lat_min = np.min(y_station)-2
    lon_max = np.max(x_station)+2
    lon_min = np.min(x_station)-2
    x_event = random.uniform(lon_min,lon_max)
    y_event = random.uniform(lat_min,lat_max)
    delta_x_event = 1e-6  
    delta_y_event = 1e-6 
    delta_z_event = 1e-6 
    # Number of data points
    n = len(x_station)
    pm_all = []
    rms_all = []
    pm = []
    rms = []
    for iteration in range(0,max_iter):
        # Current RMS error
        loss = rms_error(x_event, y_event, z_event, x_station, y_station, y_true)
        # Perturb x_event and calculate new RMS error
        loss_x_event_plus_delta = rms_error(x_event+delta_x_event, y_event, z_event, x_station, y_station, y_true)
        # Perturb y_event and calculate new RMS error
        loss_y_event_plus_delta = rms_error(x_event, y_event+delta_y_event, z_event, x_station, y_station, y_true)        
        # Calculate finite difference gradients
        grad_x_event = (loss_x_event_plus_delta - loss) / delta_x_event
        grad_y_event = (loss_y_event_plus_delta - loss) / delta_y_event
        # new hyperparameter
        x_event_old = copy.deepcopy(x_event)
        y_event_old = copy.deepcopy(y_event)
        # z_event_old = copy.deepcopy(z_event)
        x_event = x_event_old - (alpha*grad_x_event)
        y_event = y_event_old - (alpha*grad_y_event)
        # new forward
        y_pred = np.array([taupi_teoritical(y_event,x_event,z_event,y_station[i],x_station[i],model='ak135')['P'] for i in range(0,n)])
        # get rms
        rms_in_loop = pure_rms_error(y_true,y_pred)
        rms.append(rms_in_loop)
        pm.append([x_event,y_event,z_event])
        rms_all.append(rms_in_loop)
        pm_all.append([x_event,y_event,z_event])
        # Break
        if rms_in_loop <= 3:
            break
    x_event = pm[np.argmin(rms)][0]
    y_event = pm[np.argmin(rms)][1]
    z_event = pm[np.argmin(rms)][2]
    # Section 2    
    reference_latitude = y_event  # Reference point latitude
    reference_longitude = x_event  # Reference point longitude
    grid_size_latitude = 5  # Number of points along latitude (must be odd)
    grid_size_longitude = 5  # Number of points along longitude (must be odd)
    latitude_spacing = 0.5  # Latitude spacing in degrees
    longitude_spacing = 0.5  # Longitude spacing in degrees
    lat_grid, lon_grid = create_latlon_grid(reference_latitude, reference_longitude,grid_size_latitude, grid_size_longitude,latitude_spacing, longitude_spacing)
    lat_grid, lon_grid = lat_grid.flatten(), lon_grid.flatten()
    count = 0
    portion = int(0.6 * len(lat_grid)) 
    random_index = random.sample(range(0,len(lat_grid)),portion)
    rms = [None]*len(random_index)
    for index in range(0,len(random_index)):
        try:
            y_pred = np.array([taupi_teoritical(lat_grid[index],lon_grid[index],z_event,y_station[i],x_station[i],model='ak135')['P'] for i in range(0,n)])
            rms_in_loop = pure_rms_error(y_true,y_pred) 
            rms[count] = rms_in_loop
            rms_all.append(rms_in_loop)
            pm_all.append([lon_grid[index],lat_grid[index],z_event])
        except:
            pass
        count += 1
    x_event = pm_all[np.argmin(rms_all)][0]
    y_event = pm_all[np.argmin(rms_all)][1]
    # Section 3    
    reference_latitude = y_event  # Reference point latitude
    reference_longitude = x_event  # Reference point longitude
    grid_size_latitude = 5  # Number of points along latitude (must be odd)
    grid_size_longitude = 5  # Number of points along longitude (must be odd)
    latitude_spacing = 0.1  # Latitude spacing in degrees
    longitude_spacing = 0.1  # Longitude spacing in degrees
    lat_grid, lon_grid = create_latlon_grid(reference_latitude, reference_longitude,grid_size_latitude, grid_size_longitude,latitude_spacing, longitude_spacing)
    lat_grid, lon_grid = lat_grid.flatten(), lon_grid.flatten()
    count = 0
    portion = int(0.6 * len(lat_grid)) 
    random_index = random.sample(range(0,len(lat_grid)),portion)
    rms = [None]*len(random_index)
    for index in range(0,len(random_index)):
        try:
            y_pred = np.array([taupi_teoritical(space[index][1],space[index][0],z_event,y_station[i],x_station[i],model='ak135')['P'] for i in range(0,n)])
            rms_in_loop = pure_rms_error(y_true,y_pred) 
            rms[count] = rms_in_loop
            rms_all.append(rms_in_loop)
            pm_all.append([lon_grid[index],lat_grid[index],z_event])
        except:
            pass
        count += 1
    x_event = pm_all[np.argmin(rms_all)][0]
    y_event = pm_all[np.argmin(rms_all)][1]
    # Section 4
    z_space = np.arange(5,205,5)
    count = 0
    portion = int(0.4 * len(z_space)) 
    random_index = random.sample(range(0,len(z_space)),portion)
    rms = [None]*len(random_index)
    for index in range(0,len(random_index)):
        try:
            y_pred = np.array([taupi_teoritical(y_event,x_event,z_space[index],y_station[i],x_station[i],model='ak135')['P'] for i in range(0,n)])
            rms_in_loop = pure_rms_error(y_true,y_pred) 
            rms[count] = rms_in_loop
            rms_all.append(rms_in_loop)
            pm_all.append([x_event,y_event,z_space[index]])
        except:
            pass
        count += 1
    x_event = pm_all[np.argmin(rms_all)][0]
    y_event = pm_all[np.argmin(rms_all)][1]
    z_event = pm_all[np.argmin(rms_all)][2]
    return x_event,y_event,z_event,pm_all,rms_all

def region_binning(lon_series,lat_series,depth_series,shp):
    # Phase 5 Define Latitude Longitude Detailed Location
    regions = []
    sub_regions = []
    terrains = []
    countries = []
    for long, lat in zip(lon_series.iteritems(), lat_series.iteritems()):
        point = Point(long[-1],lat[-1])
        region,sub_region = polygon_contain(point,shp['shp_ind_land'],shp['gdf_ind_land'])
        terrain = 'Land'
        country = 'Indonesia'
        if region == 'Unidentified':
            region,sub_region = polygon_contain(point,shp['shp_ind_marine'],shp['gdf_ind_marine'])
            terrain = 'Sea'
            country = 'Indonesia'
        if region == 'Unidentified':
            region,sub_region = polygon_contain(point,shp['shp_out_land'],shp['gdf_out_land'])
            terrain = 'Land'
            country = 'Non-Indonesia'
        if region == 'Unidentified':
            region,sub_region = polygon_contain(point,shp['shp_out_marine'],shp['gdf_out_marine'])
            terrain = 'Sea'
            country = 'Non-Indonesia'
        if region == 'Unidentified':
            terrain = 'Sea'
            country = 'Non-Indonesia'
        
        regions.append(region)
        sub_regions.append(sub_region)
        terrains.append(terrain)
        countries.append(country)
    
    # Make DataFrame
    df_loc = pd.DataFrame()
    df_loc['Longitude'] = lon_series
    df_loc['Latitude'] = lat_series
    df_loc['Depth'] = depth_series
    df_loc['Region'] = regions
    df_loc['Sub Region'] = sub_regions
    df_loc['Terrain'] = terrains
    df_loc['Country'] = countries
    
    return df_loc