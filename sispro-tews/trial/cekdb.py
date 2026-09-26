from sshtunnel import SSHTunnelForwarder
from pymongo import MongoClient
from bson.objectid import ObjectId
# SSH tunnel settings
SSH_HOST = '194.195.92.242'
SSH_USERNAME = 'root'
SSH_PASSWORD = 'JakartaBersih12#'  # or use private_key='path/to/private/key'
MONGO_HOST = '127.0.0.1'  # Localhost from the server's perspective
MONGO_DB = 'sispro-tews'

# Local port to bind the remote MongoDB port
LOCAL_BIND_PORT = 23982  # Can be any available port
REMOTE_BIND_PORT = 23982  # Default MongoDB port

tunnel = SSHTunnelForwarder(
    (SSH_HOST, 22),  # Remote SSH server configuration
    ssh_username=SSH_USERNAME,
    ssh_password=SSH_PASSWORD,  # or use ssh_private_key='path/to/private/key'
    remote_bind_address=(MONGO_HOST, REMOTE_BIND_PORT),
    local_bind_address=('0.0.0.0', LOCAL_BIND_PORT)
)

tunnel.start()

client = MongoClient(host='127.0.0.1', port=tunnel.local_bind_port)
    
# Access the specific database
db = client[MONGO_DB]
    
# Perform database operations
print(db.list_collection_names())
    
# Close the MongoDB connection

db_users = db["user"]


user_data = db_users.find_one({
    "username":"regional_java"
})
station_ids = user_data["stations"]
print(station_ids)


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
client.close()

