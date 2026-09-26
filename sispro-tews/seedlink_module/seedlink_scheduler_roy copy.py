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
from obspy import Stream
import os
from datetime import date, datetime
from obspy import read
from multiprocessing import Process, set_start_method
from dotenv import load_dotenv
import json
from confluent_kafka import Producer
from kafka import KafkaProducer
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing.pool import Pool
from multiprocessing.pool import ThreadPool
import traceback


sys.setrecursionlimit(100000)  # Adjust the recursion limit
load_dotenv("./.env")

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
seedlink_url = os.getenv('seedlink_url')
regional = os.getenv('regional')
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


LOCAL_STATION_LIST = []

class MySeedLinkClient(EasySeedLinkClient):
    def __init__(self, server_url, autoconnect=True):
        self.threadpool = ThreadPoolExecutor(max_workers=total_core)
        self.threads = []
        super().__init__(server_url, autoconnect)
        
    def player_run(self):
        pass

    def on_data(self, trace):
        try:
            # if station_total_to_close == 0 :
            print(f'Received trace for station {trace.stats.station}:')
            print(trace)

            self.threadpool.submit(self.save_stream_to_mseed, trace)
            # self.threads.append(thread)
            # print(len(self.threads))
            # if len(self.threads) == total_core:
            #     for thread in self.threads:
            #         thread.result()
            #     self.threads.clear()
            #     self.threads = []
        except Exception as e:
            print(e)
            self.on_seedlink_error()

    def on_terminate(self):
        try:
            print("Stopping")
            
            return super().on_terminate()
        except Exception as e:
            print(e)
            self.on_seedlink_error()
    
    def on_seedlink_error(self):

        print("Stopping by error")
        # if os.path.isfile("./data/station.csv") == True:
        #     os.remove("./data/station.csv")

        # if os.path.isfile("./data/station_database.csv") == True:
        #     os.remove("./data/station_database.csv")
        
        return super().on_terminate()

    
    def acked(self, err, msg):
        if err is not None:
            print(f"Failed to deliver message: {err.str()}")
        else:
            print(f"Message produced: {msg.value()}")
        
    
    def save_stream_to_mseed(self, trace):
        try:
            today = datetime.utcnow().date()
            
            
            path_save = "../archive_data/"+str(today)+"/"+trace.stats.network+"/"+trace.stats.station+"/"+trace.stats.channel
            path_save_day = "../archive_data/"+str(today)+"/"+trace.stats.network+"/"+trace.stats.station+"/"+trace.stats.channel+"/day_mseed"
            
            if not os.path.exists(path_save_day):
                os.makedirs(path_save_day)

            filename = trace.stats.network+"."+trace.stats.station+"."+trace.stats.location+"."+trace.stats.channel+".mseed"
            
            start_time_respond = str(trace.stats.starttime).split("T")[1].replace("Z", "")
            end_time_respond= str(trace.stats.endtime).split("T")[1].replace("Z", "")

            start_time_file = str(trace.stats.starttime).split("T")[1].replace("Z", "")[:-7].replace(":","")
            end_time_file = str(trace.stats.endtime).split("T")[1].replace("Z", "")[:-7].replace(":","")

            utc_year = str(today.year)
            utc_julian_day = str(today.strftime('%j'))

            file_period_path_save = path_save+"/"+utc_year+"."+utc_julian_day+"_"+start_time_file+"__"+end_time_file+"_"+filename
            # Format back to a string if needed
            # trace.data = np.require(trace.data, dtype=np.float64)
            # trace.write(file_period_path_save, format='MSEED')

            # try:

            #     st = read(file_period_path_save, format='MSEED', details=True, loose=True)
            # except Exception as e:
            #     print(f"Error while reading MiniSEED file st: {e}")

            waveform2 = trace.data
            import time
            station_data = station_find_by_code_and_network_repository(db,trace.stats.station, trace.stats.network,)
            
            
            
            # trace.interpolate(sampling_rate=5) 
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
                "waveform":waveform2.tolist()
            }

            # Send a message
            producer.send('waveform_seedlink', json.dumps(json_string).encode())
            # Ensure all messages are sent and then close the producer
            producer.flush()
    
            
            trace = trace.interpolate(sampling_rate=5) 
            waveform3 = trace.data
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
                "waveform":waveform3.tolist()
            }
            print(f"Data for station {trace.stats.station,} written to {filename}")

            channel = trace.stats.network+"."+trace.stats.station+"." + trace.stats.location + "."+ trace.stats.channel
            
            # asyncio.run(publish_redis_message(channel, json.dumps (json_string)))

            # threading.Thread(target=publish_redis_message, args=(channel, json.dumps (json_string))).start()
            publish_redis_message(channel, json.dumps(json_string))
            # Send a message

            # producer.produce(topic, value=data, callback=delivery_report)
            # producer.flush() 

            # kafka_prod.produce('waveform_seedlink-'+channel,json.dumps (json_string))
            # Ensure all messages are sent and then close the producer
            # kafka_prod.flush()

            
           
            # day_mseed_filename = trace.stats.network+"."+trace.stats.station+"."+trace.stats.location+"."+trace.stats.channel+"."+utc_year+"."+utc_julian_day+".mseed"
            # if os.path.isfile(path_save_day+"/"+day_mseed_filename) == False:
            #     trace.write(path_save_day+"/"+day_mseed_filename, format='MSEED')
            # else:

            #     try:
            #         import io
            #         reclen = 512
            #         with open(path_save_day+"/"+day_mseed_filename, 'rb') as fh:
            #             data = []
            #             block = fh.read(reclen)
            #             while block:
            #                 data.append(block)
            #                 block = fh.read(reclen)
                    
            #         data = io.BytesIO(b''.join(data))
            #         data.seek(0)

            #         st1 = read(data , format='MSEED')
            #         existing_traces = [
            #             tr for tr in st1 if tr.stats.station == trace.stats.station and
            #             tr.stats.network == trace.stats.network and
            #             tr.stats.starttime == trace.stats.starttime and
            #             tr.stats.endtime == trace.stats.endtime
            #         ]

            #         if existing_traces:
            #             # Replace the existing trace(s) with the new trace
            #             for tr in existing_traces:
            #                 st1.remove(tr)
            #             st1.append(trace)
            #         else:
            #             # Append the new trace if no matching traces are found
            #             st1.append(trace)

            #         st1.sort(keys=['starttime'])
            #         st1.write(path_save_day+"/"+day_mseed_filename, format='MSEED') # iki tak gabung
            #         # pass
            #     except UserWarning as e:
            #         print(f"Caught an exception: {e}")
            #     except Exception as e:
            #         print(f"Error while reading MiniSEED file st1: {e}")
                
            # # print("update mseed day data")
            # date = trace.stats.starttime.strftime("%Y.%j")
            # fmtstr = '/'.join(date.split('.')[:1]+[trace.id.split('.')[i] for i in [0,1,3]])+".D"
            # directory = f"../archive/{fmtstr}"
            # if not os.path.exists(directory):
            #     os.makedirs(directory)
                
            # filename1 = f"{directory}/{trace.id}.D.{date}"
            # # Check if the file exists to append or create a new one
            # if os.path.exists(filename1):

            #     try:
            #         # Read the data while ignoring any corrupted records
            #         # st2 = read(filename1, format='MSEED', details=True, headonly=True, loose=True)
            #         import io
            #         reclen = 512
            #         with open(filename1, 'rb') as fh:
            #             data = []
            #             block = fh.read(reclen)
            #             while block:
            #                 data.append(block)
            #                 block = fh.read(reclen)
                    
            #         data = io.BytesIO(b''.join(data))
            #         data.seek(0)

            #         st2 = read(data, format='MSEED')

            #         existing_traces = [
            #             tr for tr in st2 if tr.stats.station == trace.stats.station and
            #             tr.stats.network == trace.stats.network and
            #             tr.stats.starttime == trace.stats.starttime and
            #             tr.stats.endtime == trace.stats.endtime]

            #         if existing_traces:
            #                             # Replace the existing trace(s) with the new trace
            #             for tr in existing_traces:
            #                 st2.remove(tr)
            #             st2.append(trace)
            #         else:
            #             st2.append(trace)
                    
            #         st2.sort(keys=['starttime'])
            #         st2.write(filename1, format='MSEED')
            #         # pass
            #     except UserWarning as e:
            #         print(f"Caught an exception: {e}")
            #     except Exception as e:
            #         print(f"Error while reading MiniSEED file st2: {e}")

                

               
            # else:
                # trace.write(filename1, format='MSEED')

            
           
        except Exception as e:
            print(str(e))
            

def run_client( 
                seedlink_url,
                network,
                station,
                channels):
    client = None
    warnings.filterwarnings("error", category=InternalMSEEDWarning)
    is_add = False
    while True:
        try:
            client = None
            client = MySeedLinkClient(server_url=seedlink_url) 
            for channel in channels:
                client.select_stream(network, station, channel)
                        
                    
            if is_add == False:
                clients.append(client)       

            client.run()
        
        except InternalMSEEDWarning as w:
            print("Warning caught as exception "+station+"  "+str(w))
        except Exception as e:
            print("Client run terminated with exception "+station+"  "+str(e))
        finally:
            if client:
                client.close()
                del client
            
            gc.collect()
            print("Client run method exited.")
            continue
        
def run_clients(arr_datas):
    with ThreadPoolExecutor(max_workers=len(arr_datas) * 2) as executor:
        future_to_client = {executor.submit(run_client, data['seedlink_url'], data['network'], data['station'], data['channel']): data for data in arr_datas}
        for future in as_completed(future_to_client):
            data = future_to_client[future]
            try:
                future.result()
            except Exception as e:
                print(f"Task failed for {data['station']}: {e}")

def batch_run_client(arr_datas):
    client = None
    warnings.filterwarnings("error", category=InternalMSEEDWarning)
    is_add = False
    while True:
        try:
            client = None
            client = MySeedLinkClient(server_url=arr_datas[0]['seedlink_url']) 
            for data in arr_datas:
                network = data['network']
                station = data['station']
                for channel in data['channel']:
                    client.select_stream(network, station, channel)
            station = ""
            if is_add == False:
                clients.append(client)       

            client.run()
        except InternalMSEEDWarning as w:
            print("Warning caught as exception "+station+"  "+str(w))
        except Exception as e:
            print("Client run terminated with exception "+station+"  "+str(e))
        finally:
            if client:
                client.close()
                del client
            
            gc.collect()
            print("Client run method exited.")
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

producer = KafkaProducer(bootstrap_servers=kafka_host+":"+kafka_port)
            
# kafka_prod = Producer({
#     'bootstrap.servers': kafka_host+":"+kafka_port,})

if os.path.isfile("./data/station.csv") == True:
    os.remove("./data/station.csv")

if os.path.isfile("./data/station_database.csv") == True:
    os.remove("./data/station_database.csv")

client_threads =[]
clients = []
stop_event = threading.Event()

MAX_CLIENT_PROCESS = 100
total_core = 30
pool = ThreadPool(MAX_CLIENT_PROCESS)

def split_array(arr, chunk_size):
    return [arr[i:i + chunk_size] for i in range(0, len(arr), chunk_size)]
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
                station_will_runs = []         
                
                df_database_station_filtered1 = df_database_station[df_database_station["server_seedlink"]==seedlink_url]
                networks = df_database_station_filtered1["network"].to_list()
                for _, row in df_database_station_filtered1.iterrows():    
                    channels = row["channel"]
                    # for channel in channels:
                    station_will_run = {
                        "seedlink_url" : seedlink_url,
                        "network": row["network"], 
                        "station": row["code"], 
                        "channel": channels
                    }
                    # clients.append(client)
                    station_will_runs.append(station_will_run)
            

                arr_results = split_array(station_will_runs, MAX_CLIENT_PROCESS)
                from multiprocessing.pool import Pool
                # with Pool(total_core) as pool:
                #     pool.map_async(run_clients, arr_results)

                pool.imap_unordered(batch_run_client, arr_results)
                # for arr_data in arr_results:
                # print("all client started")

                # ThreadPoolExecutor
                # executor = ThreadPoolExecutor(max_workers=len(arr_results))
                # jobs = []
                # for chunk in arr_results:
                #     job = executor.submit(batch_run_client, chunk)
                #     jobs.append(job)

                # for job in jobs:
                #     job.result()

                print(f"Server {seedlink_url} used {len(arr_results)} client!")
        else:
            df_existing = pd.read_csv("./data/station.csv")

            df_database_station = pd.DataFrame.from_dict(station_datas)
            df_database_station.to_csv("./data/station_database.csv", index=False)
            df_database_station = pd.read_csv("./data/station_database.csv")

            print(df_existing)
            print(df_database_station)

            are_equal = False
            if df_existing.shape == df_database_station.shape:
                # Proceed with comparison if they have the same shape
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

            del df_existing
            del df_database_station
            del are_equal
            del station_datas
            gc.collect() 
    except Exception as e:
        print("error",str(e))
        
        # for client in clients:
        #     if client != None:
                
        #         client.conn.terminate()
        # for client_thread in client_threads:
        #     client_thread.join()
        # if os.path.isfile("./data/station.csv") == True:
        #     os.remove("./data/station.csv")

        # if os.path.isfile("./data/station_database.csv") == True:
        #     os.remove("./data/station_database.csv")

        
if __name__ == "__main__":
    # If this script is run, only Rocketry is run
    
    app.run()

