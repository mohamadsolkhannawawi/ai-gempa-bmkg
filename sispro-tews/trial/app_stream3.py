from concurrent.futures import ThreadPoolExecutor, as_completed
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy import Stream
import obspy
import os
from datetime import date
from obspy import read
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
import pandas as pd
load_dotenv("./.env")

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
seedlink_url = os.getenv('seedlink_url')
regional = os.getenv('location')
SSH_HOST = os.getenv('ssh_host')
SSH_PORT = int(os.getenv('ssh_port'))
SSH_USERNAME = os.getenv('ssh_username')
SSH_PASSWORD = os.getenv('ssh_password')
MONGO_HOST = os.getenv('database_host')
MONGO_DB = os.getenv('database_name')
LOCAL_BIND_PORT = int(os.getenv('database_port'))
REMOTE_BIND_PORT = int(os.getenv('database_port'))


# Function to serialize data to JSON format
def json_serializer(data):
    return json.dumps(data).encode('utf-8')
# Initialize a producer

class MySeedLinkClient(EasySeedLinkClient):
    def __init__(self, server_url):
        super().__init__(server_url)
        self.stream = Stream()  # Initialize an empty Stream object to accumulate traces
        
        
    def on_data(self, trace):
        print(f'Received trace for station {trace.stats.station}:')
        print(trace)
        self.stream += trace
        self.save_stream_to_mseed(trace)

    def on_terminate(self):
        print("Stopping")
        return super().on_terminate()
    
    def acked(self, err, msg):
        if err is not None:
            print(f"Failed to deliver message: {err.str()}")
        else:
            print(f"Message produced: {msg.value()}")
    
    def save_stream_to_mseed(self, trace):
        try:
            today = date.today()
            path_save = "../archive_data/"+str(today)
            check_and_make_existing_path(path_save)

            path_save = "../archive_data/"+str(today)+"/"+trace.stats.network
            check_and_make_existing_path(path_save)

            path_save = "../archive_data/"+str(today)+"/"+trace.stats.network+"/"+trace.stats.station
            check_and_make_existing_path(path_save)

            path_save = "../archive_data/"+str(today)+"/"+trace.stats.network+"/"+trace.stats.station+"/"+trace.stats.channel
            check_and_make_existing_path(path_save)
            
            filename = trace.stats.network+"."+trace.stats.station+"."+trace.stats.channel+".mseed"
            
            time_start = str(trace.stats.starttime).split("T")[1].replace("Z", "")[:-7]
            time_end= str(trace.stats.endtime).split("T")[1].replace("Z", "")[:-7]
            # Format back to a string if needed

            new_time_start = get_gmt_7_time(time_start)
            new_time_end = get_gmt_7_time(time_end)

            self.stream.write(path_save+"/"+new_time_start+"_"+new_time_end+"_"+filename, format='MSEED')
            st = read(path_save+"/"+new_time_start+"_"+new_time_end+"_"+filename)
            waveform2 = st[0].data/1000
            json_string = {
                "date":str(today),
                "time_start":new_time_start,
                "time_end":new_time_end,
                "station":trace.stats.station,
                "network":trace.stats.network,
                "channel":trace.stats.channel,
                "waveform":len(waveform2.tolist())
            }
            print(f"Data for station {trace.stats.station,} written to {filename}")

            # Send a message
            producer.send('test', json_string)
            # Ensure all messages are sent and then close the producer
            producer.flush()

        except Exception as e:
            print(str(e))

def run_client(client):
    try:
        client.run()
        client.close()
    except Exception as e:
        print(f"Client run terminated with exception: {e}")
    finally:
        print("Client run method exited.")


producer = KafkaProducer(bootstrap_servers=kafka_host+":"+kafka_port, value_serializer=json_serializer)
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

# while True:
#     db_users = db["user"]
#     user_data = db_users.find_one({
#         "username":regional
#     })

#     station_ids = user_data["stations"]
#     db_station = db["station"]
#     networks = []
#     stations = []
#     channels = []
#     for station_id in station_ids:
#         station_data =db_station.find_one({
#             '_id': ObjectId(station_id)
#         })
#         networks.append(station_data["network"])
#         stations.append(station_data["code"])
#         channels.append(station_data["channel"])
    
#     # Wait for a while before stopping (e.g., 30 seconds)
#     sleep(30)

#     # Signal the client to stop and wait for the thread to finish
#     print("stopping")
#     client.conn.terminate()
#     client_thread.join()
# read text file into pandas DataFrame
networks = []
stations = []
channels = []
station_locs = pd.read_csv("stations.csv", sep="\t")
for x in station_locs["station"]:
    x = x.split(".")

    networks.append(x[0])
    stations.append(x[1],)
    channels.append(x[-1] + "?")
print(networks)
print(stations)
print(channels)
client = MySeedLinkClient(server_url='rtserve.iris.washington.edu:18000',)
for network,station, channel in zip(networks, stations, channels):
    client.select_stream(network, station, channel)

client.run()


print("Data acquisition for all stations complete.")


 

