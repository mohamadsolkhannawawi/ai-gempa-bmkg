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
from datetime import datetime, timedelta
from sshtunnel import SSHTunnelForwarder
from pymongo import MongoClient
from bson.objectid import ObjectId
# SSH tunnel settings

load_dotenv("./.env")

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
seedlink_url = os.getenv('seedlink_url')
SSH_HOST = os.getenv('ssh_host')
SSH_PORT = int(os.getenv('ssh_port'))
SSH_USERNAME = os.getenv('ssh_username')
SSH_PASSWORD = os.getenv('ssh_password')
MONGO_HOST = os.getenv('database_host')
MONGO_DB = os.getenv('database_name')
LOCAL_BIND_PORT = int(os.getenv('database_port'))
REMOTE_BIND_PORT = int(os.getenv('database_port'))
regional = os.getenv('location')
output_filename_pattern = "output_{network}_{station}_{channel}.mseed"


# Function to serialize data to JSON format
def json_serializer(data):
    return json.dumps(data).encode('utf-8')
# Initialize a producer
producer = KafkaProducer(bootstrap_servers=kafka_host+":"+kafka_port, value_serializer=json_serializer)


class MyClient(EasySeedLinkClient):
    def __init__(self, server_url, network, station, channel, output_filename):
        super().__init__(server_url)
        self.stream = Stream()  # Initialize an empty Stream object to accumulate traces
        self.network = network
        self.station = station
        self.channel = channel
        self.output_filename = output_filename
        
        
    def on_data(self, trace):
        print(f'Received trace for station {self.station}:')
        print(trace)
        self.stream += trace

        # Save condition - here you might need more sophisticated logic
        if len(self.stream) >= 1:  # Simple condition for demonstration
            self.save_stream_to_mseed(self.output_filename.format(
                network = self.network,
                station=self.station,
                channel=self.channel))
            self.stream = Stream()  # Reinitialize the stream for new data
            self.on_terminate()
            

    def on_terminate(self):
        print("Stopping")
        return super().on_terminate()
    
    def acked(self, err, msg):
        if err is not None:
            print(f"Failed to deliver message: {err.str()}")
        else:
            print(f"Message produced: {msg.value()}")
    
    def save_stream_to_mseed(self, filename):
        try:
            today = date.today()
            path_save = "../archive_data/"+str(today)
            if os.path.exists(path_save) == False:
                os.mkdir(path_save)

            
            time_start = str(self.stream).split(" | ")[1].split(" - ")[0].split("T")[1].replace("Z", "")[:-7]
            time_end= str(self.stream).split(" | ")[1].split(" - ")[1].split("T")[1].replace("Z", "")[:-7]


            # Parse the string to a datetime object
            time_obj = datetime.strptime(time_start, "%H:%M:%S")

            # Add 7 hours
            new_time_obj = time_obj + timedelta(hours=7)

            # Format back to a string if needed
            new_time_start = new_time_obj.strftime("%H:%M:%S")

            # Parse the string to a datetime object
            time_obj = datetime.strptime(time_end, "%H:%M:%S")

            # Add 7 hours
            new_time_obj = time_obj + timedelta(hours=7)

            # Format back to a string if needed
            new_time_end = new_time_obj.strftime("%H:%M:%S")

            self.stream.write(path_save+"/"+new_time_start+"_"+new_time_end+"_"+filename, format='MSEED')
            st = read(path_save+"/"+new_time_start+"_"+new_time_end+"_"+filename)
            waveform2 = st[0].data/1000
            json_string = {
                "date":str(today),
                "time_start":new_time_start,
                "time_end":new_time_end,
                "station":self.station,
                "network":self.network,
                "channel":self.channel,
                "waveform":waveform2.tolist()
            }
            print(f"Data for station {self.station} written to {filename}")

            # Send a message
            producer.send('test', json_string)

            # Ensure all messages are sent and then close the producer
            producer.flush()

        except Exception as e:
            print(str(e))

def run_client_for_station(server_url, network, station, channel, output_filename_pattern):
    output_filename = output_filename_pattern.format(
        network=network,
        station=station,
        channel=channel)
    client = MyClient(server_url,network, station, channel, output_filename)
    client.select_stream(network, station, channel)
    client.run()

    client.close()

# Configuration
tunnel = SSHTunnelForwarder(
    (SSH_HOST, 22),  # Remote SSH server configuration
    ssh_username=SSH_USERNAME,
    ssh_password=SSH_PASSWORD,  # or use ssh_private_key='path/to/private/key'
    remote_bind_address=(MONGO_HOST, REMOTE_BIND_PORT),
    local_bind_address=('0.0.0.0', LOCAL_BIND_PORT)
)
tunnel.start()
client = MongoClient(host=MONGO_HOST, port=tunnel.local_bind_port)
# Access the specific database
db = client[MONGO_DB]
print(db.list_collection_names())
db_users = db["user"]
user_data = db_users.find_one({
    "username":regional
})
station_ids = user_data["stations"]

db_station = db["station"]
networks = []
stations = []
channels = []
for station_id in station_ids:
    station_data =db_station.find_one({
        '_id': ObjectId(station_id)
    })
    networks.append(station_data["network"])
    stations.append(station_data["code"])
    channels.append(station_data["channel"])
print(networks)
print(stations)
print(channels)


print("Data acquisition for all stations complete.")
