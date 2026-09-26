import os
from dotenv import load_dotenv
import numpy as np
import pandas as pd
import geopandas as gpd

from skydrifter.SeisRealTimeController.Algorithm.MLLocEpicenter.MLLocEpicenter import MLLocEpicenter
from skydrifter.SeisRealTimeController.Algorithm.MLLocDepth.MLLocDepth import MLLocDepth
from skydrifter.SeisRealTimeController.Algorithm.MLMag.MLMag import MLMag
from skydrifter.SeisRealTimeController.Algorithm.MLOriginTime.MLOriginTime import MLOriginTime

# env constant
load_dotenv("./.env")
KAFKA_HOST = os.getenv("kafka_host")
KAFKA_PORT = os.getenv("kafka_port")

REDIS_HOST = os.getenv("redis_host")
REDIS_PORT = os.getenv("redis_port")

MONGO_HOST = os.getenv("database_host")
MONGO_PORT = os.getenv("database_port")
DB_NAME = os.getenv("database_name")

USER_NAME = os.getenv("regional")

# Kafka topics
PICK_TOPIC = os.getenv("pick_topic")
ARRIVAL_PICK_TOPIC = os.getenv("arrival_pick_topic")
CLUSTER_TOPIC = os.getenv("cluster_topic")
EVENT_TOPIC = os.getenv("event_topic")
RELOCATION_TOPIC = os.getenv("relocation_topic")

# Other constants
SAMPLE_RATE = int(os.getenv("sample_rate"))
WINDOW_SIZE_SEC = int(os.getenv("window_size_sec"))
WINDOW_SIZE = WINDOW_SIZE_SEC * SAMPLE_RATE
OVERLAPS_SEC = int(os.getenv("overlap_sec"))
OVERLAPS = OVERLAPS_SEC * SAMPLE_RATE
ASSOCIATION_EXPIRED_SEC = 300
N_STATION = 4
MAX_WORKERS = 300

# SHP
path = {
    "World Marine": r"skydrifter/__SkydrifterFile/world_shapefile/world_marine.shp",
    "World Land": r"skydrifter/__SkydrifterFile/world_shapefile/world_land.shp",
    "Indonesia Marine": r"skydrifter/__SkydrifterFile/world_shapefile/indonesia_marine.shp",
    "Indonesia Land": r"skydrifter/__SkydrifterFile/world_shapefile/indonesia_land.shp"
}

shp_out_marine = gpd.read_file(path['World Marine'])
gdf_out_marine = gpd.GeoSeries(shp_out_marine['geometry'])
shp_out_land = gpd.read_file(path['World Land'])
gdf_out_land = gpd.GeoSeries(shp_out_land['geometry'])
shp_ind_land = gpd.read_file(path['Indonesia Land'])
gdf_ind_land = gpd.GeoSeries(shp_ind_land['geometry'])
shp_ind_marine = gpd.read_file(path['Indonesia Marine'])
gdf_ind_marine = gpd.GeoSeries(shp_ind_marine['geometry'])

SHP_DICT = {
    'shp_out_marine': shp_out_marine,
    'gdf_out_marine': gdf_out_marine,
    'shp_out_land': shp_out_land, 
    'gdf_out_land': gdf_out_land, 
    'shp_ind_land': shp_ind_land, 
    'gdf_ind_land': gdf_ind_land, 
    'shp_ind_marine': shp_ind_marine,
    'gdf_ind_marine': gdf_ind_marine
}

# ML Model
path = r"skydrifter/SeisRealTimeController/Algorithm/MLLocEpicenter/model_4sta.npy"
model_epicenter = np.load(path,allow_pickle='TRUE').item()
path = r"skydrifter/SeisRealTimeController/Algorithm/MLLocDepth/model_4sta.npy"
model_depth = np.load(path,allow_pickle='TRUE').item()
path = r"skydrifter/SeisRealTimeController/Algorithm/MLMag/model_4sta.npy"
model_mag = np.load(path,allow_pickle='TRUE').item()
path = r"skydrifter/SeisRealTimeController/Algorithm/MLOriginTime/model_4sta.npy"
model_ot = np.load(path,allow_pickle='TRUE').item()

location = MLLocEpicenter()
location.model = model_epicenter
location.n_station = N_STATION
location.shp = SHP_DICT

depth = MLLocDepth()
depth.model = model_depth
depth.n_station = N_STATION

mag = MLMag()
mag.model = model_mag
mag.n_station = N_STATION

ot = MLOriginTime()
ot.model = model_ot
ot.n_station = N_STATION

TABULAR_MODEL = {}
TABULAR_MODEL['1'] = location
TABULAR_MODEL['2'] = depth
TABULAR_MODEL['3'] = mag
TABULAR_MODEL['4'] = ot
