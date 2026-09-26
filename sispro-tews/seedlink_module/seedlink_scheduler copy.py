from rocketry import Rocketry
from rocketry.conds import every, after_success
import json
import os
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
from kafka import KafkaProducer
from bson.objectid import ObjectId
from utils.util import get_gmt_7_time
from utils.util import check_and_make_existing_path
from configuration.database import get_database_connection
# SSH tunnel settings
import threading
from time import sleep
from configuration.redis import publish_redis_message

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

class MySeedLinkClient(EasySeedLinkClient):
    def __init__(self, server_url):
        super().__init__(server_url)
        self.stream = Stream()  # Initialize an empty Stream object to accumulate traces
        
        
    def on_data(self, trace):
        try:
            print(f'Received trace for station {trace.stats.station}:')
            print(trace)
            self.stream += trace
            self.save_stream_to_mseed(trace)
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
        if os.path.isfile("./data/station.csv") == True:
            os.remove("./data/station.csv")

        if os.path.isfile("./data/station_database.csv") == True:
            os.remove("./data/station_database.csv")
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
            trace.data = np.require(trace.data, dtype=np.float64)
            trace.write(file_period_path_save, format='MSEED')

            st = read(file_period_path_save)

            day_mseed_filename = trace.stats.network+"."+trace.stats.station+"."+trace.stats.location+"."+trace.stats.channel+"."+utc_year+"."+utc_julian_day+".mseed"
            if os.path.isfile(path_save_day+"/"+day_mseed_filename) == False:
                trace.write(path_save_day+"/"+day_mseed_filename, format='MSEED')
            else:
                st1 = read(path_save_day+"/"+day_mseed_filename)
                existing_traces = [
                    tr for tr in st1 if tr.stats.station == trace.stats.station and
                    tr.stats.network == trace.stats.network and
                    tr.stats.starttime == trace.stats.starttime and
                    tr.stats.endtime == trace.stats.endtime]

                if existing_traces:
                                    # Replace the existing trace(s) with the new trace
                    for tr in existing_traces:
                        st1.traces.remove(tr)
                        st1.append(trace)
                else:
                    st1.append(trace)

                st1.sort(keys=['starttime'])
                st1.write(path_save_day+"/"+day_mseed_filename, format='MSEED') # iki tak gabung
            
            # print("update mseed day data")
            date = trace.stats.starttime.strftime("%Y.%j")
            fmtstr = '/'.join(date.split('.')[:1]+[trace.id.split('.')[i] for i in [0,1,3]])+".D"
            directory = f"../archive/{fmtstr}"
            if not os.path.exists(directory):
                os.makedirs(directory)
                
            filename1 = f"{directory}/{trace.id}.D.{date}"
            # Check if the file exists to append or create a new one
            if os.path.exists(filename1):
                st2 = read(filename1)

                existing_traces = [
                    tr for tr in st2 if tr.stats.station == trace.stats.station and
                    tr.stats.network == trace.stats.network and
                    tr.stats.starttime == trace.stats.starttime and
                    tr.stats.endtime == trace.stats.endtime]

                if existing_traces:
                                    # Replace the existing trace(s) with the new trace
                    for tr in existing_traces:
                        st2.traces.remove(tr)
                        st2.append(trace)
                else:
                    st2.append(trace)
                
                st2.sort(keys=['starttime'])
                st2.write(filename1, format='MSEED')
            else:
                trace.write(filename1, format='MSEED')


            waveform2 = st[0].data
            json_string = {
                "date":str(today),
                "starttime":str(trace.stats.starttime),
                "endtime":str(trace.stats.endtime),
                "sampling_rate": trace.stats.sampling_rate,
                # "record_length": trace.stats.number_of_records,
                "delta": trace.stats.delta,
                "location": trace.stats.location,
                "npts": trace.stats.npts,
                "station":trace.stats.station,
                "network":trace.stats.network,
                "channel":trace.stats.channel,
                "waveform":waveform2.tolist()
            }

            print(f"Data for station {trace.stats.station,} written to {filename}")

            # Send a message
            producer.send('waveform_seedlink',json.dumps (json_string))
            # Ensure all messages are sent and then close the producer
            producer.flush()

            #Push to redis message
            channel = trace.stats.network+"."+trace.stats.station+"."+trace.stats.location+"."+trace.stats.channel
            publish_redis_message(channel, json.dumps (json_string))

        except Exception as e:
            print(str(e))

def run_client( client,
                seedlink_url,
                networks,
                stations,
                channels):
    try:
        client.run()
        client.close()
    except Exception as e:
        print(f"Client run terminated with exception: {e}")
        client = MySeedLinkClient(server_url=seedlink_url) 
        for channel in channels:
            if channels != None:
                if len(channels) > 0:
                    for channel in channels:
                        client.select_stream(
                        networks, 
                        stations, 
                        channel)
        run_client(
            client,
            seedlink_url,
            networks,
            stations,
            channels)
    finally:
        print("Client run method exited.")
        if os.path.isfile("./data/station.csv") == True:
            os.remove("./data/station.csv")

        if os.path.isfile("./data/station_database.csv") == True:
            os.remove("./data/station_database.csv")


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
producer = KafkaProducer(bootstrap_servers=kafka_host+":"+kafka_port, value_serializer=json_serializer)
if os.path.isfile("./data/station.csv") == True:
    os.remove("./data/station.csv")

if os.path.isfile("./data/station_database.csv") == True:
    os.remove("./data/station_database.csv")

# Creating some tasks
@app.task(every("20 seconds"))
async def profile_process():
    global client  # Declare client as global within this function
    # global client_thread
    global clients
    global client_threads
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
            client_threads =[]
            clients = []

            if len(clients) > 0:
                for client in clients:
                    client.conn.terminate()
            if len(client_threads) > 0:
                for client_thread in client_threads:
                    client_thread.join()

            for seedlink_url in seedlink_urls:
               
                df_database_station_filtered1 = df_database_station[df_database_station["server_seedlink"]==seedlink_url]
                networks = df_database_station_filtered1["network"].to_list()
                
                for _, row in df_database_station_filtered1.iterrows():
                    client = MySeedLinkClient(server_url=seedlink_url) 
                    print(row["name"])
                    channels = row["channel"]
                    for channel in channels:
                         if channels != None:
                            if len(channels) > 0:
                                for channel in channels:
                                    client.select_stream(
                                        row["network"], 
                                        row["code"], 
                                        channel)
                # clients.append(client)
                # client_thread = Process(target=run_client, args=(client,))
                # client_threads.append(client_thread)
                # client_thread.start()
                
                    client_thread = threading.Thread(
                        target=run_client, 
                        args=(
                            client, 
                            seedlink_url,
                            row["network"], 
                            row["code"], 
                            channels
                              
                        ))
                    clients.append(client)
                    client_threads.append(client_thread)
                    client_thread.start()
                    client_thread.join(0)
                print("client for ", seedlink_url, "started")
        else:
            df_existing = pd.read_csv("./data/station.csv")

            df_database_station = pd.DataFrame.from_dict(station_datas)
            df_database_station.to_csv("./data/station_database.csv", index=False)
            df_database_station = pd.read_csv("./data/station_database.csv")

            are_equal = False
            if df_existing.shape == df_database_station.shape:
                # Proceed with comparison if they have the same shape
                are_equal = (df_existing.sort_index(axis=1).values == df_database_station.sort_index(axis=1).values).all()
            else:
                # Handle the case where DataFrames have different shapes
                are_equal = False
            
            

            if len(df_database_station) != len(df_existing) or are_equal == False:
                df_database_station = pd.DataFrame.from_dict(station_datas)
                df_database_station.to_csv("./data/station.csv", index=False)
                print(df_database_station)
                print("new station detected")

                for client in clients:
                    client.conn.terminate()
                for client_thread in client_threads:
                    client_thread.join()
                    print("thread has stopped")
                print()
                seedlink_urls = df_database_station['server_seedlink'].unique().tolist()
                client_threads =[]
                clients = []

                for seedlink_url in seedlink_urls:
                    
                    df_database_station_filtered1 = df_database_station[df_database_station["server_seedlink"]==seedlink_url]

                    for _, row in df_database_station_filtered1.iterrows():
                        client = MySeedLinkClient(server_url=seedlink_url) 
                        print(row["name"])
                        channels = row["channel"]
                        for channel in channels:
                            if channels != None:
                                if len(channels) > 0:
                                    for channel in channels:
                                        client.select_stream(
                                            row["network"], 
                                            row["code"], 
                                            channel)

                        # clients.append(client)
                        # client_thread = Process(target=run_client, args=(client,))
                        # client_threads.append(client_thread)
                        # client_thread.start()                
                        client_thread = threading.Thread(
                            target=run_client, 
                            args=(
                                client, 
                                seedlink_url,
                                row["network"], 
                                row["code"], 
                                channels
                              
                        ))
                        clients.append(client)
                        client_threads.append(client_thread)
                        client_thread.start()
                    print("client for ", seedlink_url, "started")
          
    except Exception as e:
        print("error",str(e))
        for client in clients:
            client.conn.terminate()
        for client_thread in client_threads:
            client_thread.join()
        if os.path.isfile("./data/station.csv") == True:
            os.remove("./data/station.csv")

        if os.path.isfile("./data/station_database.csv") == True:
            os.remove("./data/station_database.csv")

        
if __name__ == "__main__":
    # If this script is run, only Rocketry is run
    
    app.run()

