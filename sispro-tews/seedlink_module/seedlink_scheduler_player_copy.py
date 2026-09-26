from rocketry import Rocketry
from rocketry.conds import every, after_success
import json
import redis
import os, time, warnings
import pandas as pd
from multiprocessing.pool import ThreadPool
from dotenv import load_dotenv
import numpy as np
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy import Stream, UTCDateTime
import os
from datetime import date, datetime
from obspy import read
from multiprocessing import Process, set_start_method
from dotenv import load_dotenv
import io
from confluent_kafka import Producer
from bson.objectid import ObjectId
from utils.util import get_gmt_7_time
from utils.util import check_and_make_existing_path
from configuration.database import get_database_connection
# SSH tunnel settings
import threading
from time import sleep
from configuration.redis import publish_redis_message
import asyncio
from multiprocessing import Process, current_process, Manager
from repositories.station_repository import station_find_by_code_and_network_repository
import sys
import gc
from obspy.io.mseed.headers import InternalMSEEDWarning
from slplayer import *

import faulthandler
faulthandler.enable()

sys.setrecursionlimit(100000)  # Adjust the recursion limit
load_dotenv("./.env")

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
seedlink_url = os.getenv('seedlink_url')
regional = os.getenv('regional_player')
SSH_HOST = os.getenv('ssh_host')
SSH_PORT = int(os.getenv('ssh_port'))
SSH_USERNAME = os.getenv('ssh_username')
SSH_PASSWORD = os.getenv('ssh_password')
MONGO_HOST = os.getenv('database_host')
MONGO_DB = os.getenv('database_name')
LOCAL_BIND_PORT = int(os.getenv('database_port'))
REMOTE_BIND_PORT = int(os.getenv('database_port'))
# Creating the Rocketry app
app = Rocketry(config={"task_execution": "async"})

pool = ThreadPool(10)
import threading

lock = threading.Lock()

# Create an event to signal when to stop the thread

# Function to serialize data to JSON format
def json_serializer(data):
    return json.dumps(data).encode('utf-8')
# Initialize a producer

import logging

# Define a custom logging handler
class ExceptionHandler(logging.Handler):
    def _init_(self, level=logging.ERROR):
        super()._init_()
        self.level = level

    def emit(self, record):
        if record.levelno >= self.level:
            raise RuntimeError(record.getMessage())

# Configure logging to capture messages at the ERROR level and above
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger('obspy.clients.seedlink')

# Add the custom exception handler to the specific logger
logger.addHandler(ExceptionHandler())

LOCAL_TRACE, LOCAL_TIMESTAMPS, LOCAL_DATALENGTH, LOCAL_ROOT = None, None, None, None
TIMESTAMP, DELTATIME = {}, {}

class MySeedLinkClient(EasySeedLinkClient):
    def __init__(self, server_url, autoconnect=True):
        super().__init__(server_url, autoconnect)
        # self.stream = Stream()  # Initialize an empty Stream object to accumulate traces

    def player_run(self, network, station, channel):
        key = '_'.join([network, station, channel+'.D'])
        while True:
            # _delay = 3  ## DEBUG
            # _offset = (1800) - (60 + 180) ## DEBUG
            t2 = UTCDateTime.now()
            # if LOCAL_TIMESTAMPS[key][0][1].strftime("%S") == t2.strftime("%S"):
            if True:
                delta_t = t2-LOCAL_TIMESTAMPS[key][0][1]
                # delta_t -= _offset ## DEBUG
                break

        for i in range(len(LOCAL_TIMESTAMPS[key])):
            t0, t1 =  LOCAL_TIMESTAMPS[key][i]
            try:
                tr =  LOCAL_TRACE[key].copy().trim(t0, t1).merge()[0]
                tr.stats.starttime = t0+delta_t
            except Exception as e:
                print("ERRORRRRRRRRR.........................!!!", e)
                try:
                    sleep(LOCAL_TIMESTAMPS[key][i+1][1] - LOCAL_TIMESTAMPS[key][i+1][0])
                except:
                    sleep(LOCAL_DATALENGTH[key])
                continue
            with lock:
                self.on_data(tr)
            print('============', network, station, channel, UTCDateTime.now()-tr.stats.endtime, '============')
            del tr
            endtime = datetime.now()
            global TIMESTAMP, DELTATIME
            if key not in DELTATIME.keys():
                DELTATIME[key] = round((endtime - datetime.strptime(TIMESTAMP[key], "%Y-%m-%d %H:%M:%S")).total_seconds(), 2)
                with open("timestamps.json", "w") as json_file:
                    json.dump(TIMESTAMP, json_file)
                with open("deltatime.json", "w") as json_file:
                    json.dump(DELTATIME, json_file)
            # sleep(np.random.uniform(1, 3))  ## DEBUG
            try:
                sleep(LOCAL_TIMESTAMPS[key][i+1][1] - LOCAL_TIMESTAMPS[key][i+1][0])
            except:
                sleep(LOCAL_DATALENGTH[key])
        sleep(3600)

    def on_data(self, trace):
        try:
            # if station_total_to_close == 0 :
                # print(f'Received trace for station {trace.stats.station}:')
                # print(trace)
                # self.stream += trace
                self.save_stream_to_mseed(trace)
            # else:
            #     self.conn.terminate()
        except Exception as e:
            self.on_seedlink_error()
        

    def on_terminate(self):
        try:
            print("Stopping")
            return super().on_terminate()
        except Exception as e:
            self.on_seedlink_error()
    
    def on_seedlink_error(self):
        print("Stopping by error")
        return super().on_terminate()

    
    def acked(self, err, msg):
        if err is not None:
            print(f"Failed to deliver message: {err.str()}")
        else:
            print(f"Message produced: {msg.value()}")
    
    def save_stream_to_mseed(self, trace):
        try:
            today = datetime.utcnow().date()

            path_save = "../archive_data_local/"+str(today)+"/"+trace.stats.network+"/"+trace.stats.station+"/"+trace.stats.channel
            path_save_day = "../archive_data_local/"+str(today)+"/"+trace.stats.network+"/"+trace.stats.station+"/"+trace.stats.channel+"/day_mseed"
            
            if not os.path.exists(path_save_day):
                os.makedirs(path_save_day)

            filename = trace.stats.network+"."+trace.stats.station+"."+trace.stats.location+"."+trace.stats.channel+".mseed"
            
            start_time_file = str(trace.stats.starttime).split("T")[1].replace("Z", "")[:-7].replace(":","")
            end_time_file = str(trace.stats.endtime).split("T")[1].replace("Z", "")[:-7].replace(":","")

            utc_year = str(today.year)
            utc_julian_day = str(today.strftime('%j'))

            # file_period_path_save = path_save+"/"+utc_year+"."+utc_julian_day+"_"+start_time_file+"__"+end_time_file+"_"+filename
            # # Format back to a string if needed
            # # trace.data = np.require(trace.data, dtype=np.float64)
            # trace.write(file_period_path_save, format='MSEED')

            # day_mseed_filename = trace.stats.network+"."+trace.stats.station+"."+trace.stats.location+"."+trace.stats.channel+"."+utc_year+"."+utc_julian_day+".mseed"
            # if os.path.isfile(path_save_day+"/"+day_mseed_filename) == False:
            #     trace.write(path_save_day+"/"+day_mseed_filename, format='MSEED')
            # else:
            #     pass

            # date = trace.stats.starttime.strftime("%Y.%j")
            # fmtstr = '/'.join(date.split('.')[:1]+[trace.id.split('.')[i] for i in [0,1,3]])+".D"
            # directory = f"../archive/{fmtstr}"
            # if not os.path.exists(directory):
            #     os.makedirs(directory)
                
            # # Check if the file exists to append or create a new one
            # filename1 = f"{directory}/{trace.id}.D.{date}"
            # if os.path.exists(filename1):
            #     st2 = read(filename1, format='MSEED')
            #     st2 += trace
            #     st2.write(filename1, format='MSEED')
            #     del st2
            # else:
            #     trace.write(filename1, format='MSEED')

            station_data = station_find_by_code_and_network_repository(db,trace.stats.station, trace.stats.network,)

            json_string = {
                "date":str(today),
                "starttime":str(trace.stats.starttime),
                "endtime":str(trace.stats.endtime),
                "sampling_rate": trace.stats.sampling_rate,
                # "record_length": trace.stats.number_of_records,
                "delta": trace.stats.delta,
                "location": trace.stats.location,
                "location_database":station_data["location"],
                "longitude":station_data["longitude"],
                "latitude":station_data["latitude"],
                "npts": trace.stats.npts,
                "station":trace.stats.station,
                "network":trace.stats.network,
                "channel":trace.stats.channel,
                "expiration_timestamp":int(time.time()) + 1800,
                "waveform":trace.data.tolist()
            }

            # print(f"Data for station {trace.stats.station,} written to {filename}")

            # channel = trace.stats.network+"."+trace.stats.station+"."+trace.stats.location+"."+trace.stats.channel
            
            # # Send a message
            # producer.send('waveform_seedlink-'+channel,json.dumps (json_string))
            # # Ensure all messages are sent and then close the producer
            # producer.flush()

            # Send a message
            producer.produce('waveform_player',json.dumps (json_string))
            # Ensure all messages are sent and then close the producer
            producer.flush()

            # publish_redis_message(channel, json.dumps (json_string))

        except Exception as e:
            print(str(e))
            gc.collect()

def run_client( 
                seedlink_url,
                network,
                station,
                channel):
    client = None
    warnings.filterwarnings("error", category=InternalMSEEDWarning)
    is_add = False
    while True:
        try:
            global TIMESTAMP
            starttime = datetime.now()
            TIMESTAMP['_'.join([network, station, channel+'.D'])] = starttime.strftime("%Y-%m-%d %H:%M:%S")
            if seedlink_url=='localhost':
                client = MySeedLinkClient(server_url=seedlink_url, autoconnect=False)
                client.player_run(network, station, channel)  
            else:
                client = MySeedLinkClient(server_url=seedlink_url) 
                client.select_stream(network, station, channel)
                        
                if is_add == False:
                    clients.append(client)       
                    is_add = True       
                client.run()
                client.close()
        
        except InternalMSEEDWarning as w:
            print(f"Warning caught as exception: {w}")
            import traceback
            traceback.print_exc()
        except Exception as e:
            print(f"Client run terminated with exception: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if client != None:
                client.close()
                del client
            gc.collect()
            print("Client run method exited.")
            import traceback
            traceback.print_exc()
            continue
        


db = get_database_connection(
    SSH_HOST,
    SSH_PORT,
    SSH_USERNAME,
    SSH_PASSWORD,
    MONGO_HOST,
    MONGO_DB,
    LOCAL_BIND_PORT,
    REMOTE_BIND_PORT,

)
import ctypes
def force_kill_thread(thread):
    # Try to raise a SystemExit exception in the target thread
    try:
        if thread.is_alive():
            # `SystemExit` raises a controlled exception to stop the thread
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread.ident), ctypes.py_object(SystemExit))
    except Exception as e:
        print(f"Failed to kill thread: {e}")


producer = Producer({
    'bootstrap.servers': kafka_host+":"+kafka_port,})

if os.path.isfile("./data/station.csv") == True:
    os.remove("./data/station.csv")

if os.path.isfile("./data/station_database.csv") == True:
    os.remove("./data/station_database.csv")

client_threads =[]
clients = []
stop_event = threading.Event()
# station_total_to_close = 0 
# Creating some tasks
@app.task(every("20 seconds"))
async def profile_process():
    
    # global client_thread
    global clients
    global client_threads
    # global station_total_to_close
    try:
        if regional != "":
            db_users = db["user"]
            user_data = db_users.find_one({
                "username": regional  # Assuming "regional" is a variable you defined elsewhere
            })
            station_ids = user_data["stations"]
            db_station = db["station"]

            networks = []
            stations = []
            channels = []
            station_datas = []
            for station_id in station_ids:
                station_data = db_station.find_one({
                    '_id': ObjectId(station_id)
                })
                station_datas.append(station_data)
        else:
            station_datas = db["station"]

        if not os.path.isfile("./data/station.csv"):    
            print("first pulling station")    

            df_database_station = pd.DataFrame.from_dict(station_datas)
            df_database_station.to_csv("./data/station.csv", index=False)
            print(df_database_station)

            seedlink_urls = df_database_station['server_seedlink'].unique().tolist()
            
            for seedlink_url in seedlink_urls:
                if seedlink_url=='localhost':
                    global LOCAL_TRACE, LOCAL_TIMESTAMPS, LOCAL_DATALENGTH, LOCAL_ROOT
                    LOCAL_TRACE, LOCAL_TIMESTAMPS, LOCAL_DATALENGTH, LOCAL_ROOT = get_local_archive()
               
                df_database_station_filtered1 = df_database_station[df_database_station["server_seedlink"]==seedlink_url]
                networks = df_database_station_filtered1["network"].to_list()
                for _, row in df_database_station_filtered1.iterrows():    
                    channels = row["channel"]
                    for channel in channels:
                        client_thread = threading.Thread(
                            target=run_client, 
                            args=(
                                seedlink_url,
                                row["network"], 
                                row["code"], 
                                channel
                                
                            ))
                        client_threads.append(client_thread)
                        client_thread.start()
                        client_thread.join(0)
                print("client for ", seedlink_url, "started")
        else:
            df_existing = pd.read_csv("./data/station.csv")

            df_database_station = pd.DataFrame.from_dict(station_datas)
            df_database_station.to_csv("./data/station_database.csv", index=False)
            df_database_station = pd.read_csv("./data/station_database.csv")

            print(df_existing)
            print(df_database_station)

            are_equal = False
            if df_existing.shape == df_database_station.shape:
        #         # Proceed with comparison if they have the same shape
                # are_equal = (df_existing.sort_index(axis=1).values == df_database_station.sort_index(axis=1).values).all()
                for col in df_existing.columns:
                    df_existing[col] = pd.to_numeric(df_existing[col], errors='coerce')
                for col in df_database_station.columns:
                    df_database_station[col] = pd.to_numeric(df_database_station[col], errors='coerce')

                
                are_equal = np.isclose(df_existing.sort_index(axis=1).fillna(0).values, 
                       df_database_station.sort_index(axis=1).fillna(0).values).all()
            else:
                # Handle the case where DataFrames have different shapes
                are_equal = False
            
            print(are_equal)
            
            if len(df_database_station) != len(df_existing) or are_equal == False:
        #         df_database_station = pd.DataFrame.from_dict(station_datas)
        #         df_database_station.to_csv("./data/station.csv", index=False)
        #         print(df_database_station)
        #         print("new station detected")
                print("len ", len(clients))
                # station_total_to_close = len(clients)
                for client in clients:
                    client.conn.terminate()

                for index, client_thread in enumerate(client_threads):
                    force_kill_thread(client_thread)
                    client_thread.join()
                    print("thread has stopped - ", str(index))
                clients = []
                print("all stopped")
                print()
                client_threads = []
                # station_total_to_close = 0

                if os.path.isfile("./data/station.csv") == True:
                    os.remove("./data/station.csv")

                if os.path.isfile("./data/station_database.csv") == True:
                    os.remove("./data/station_database.csv")
        gc.collect()
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("error:",e)
        gc.collect()

if __name__ == "__main__":
    # If this script is run, only Rocketry is run
    
    app.run()
