from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from threading import Event
import os
from datetime import datetime

class MySeedLinkClient(EasySeedLinkClient):
    def init(self, *args, **kwargs):
        super().init(*args, **kwargs)

    def on_data(self, trace):
        # Custom data handling logic here
        # For example, save the trace to a file
    
        # Check if the stop signal is set
        self.save_trace(trace)

    def on_terminate(self):
        print("Stopping")
        
    def save_trace(self, trace):
        # Example function to save the trace data
        print(trace)
        filename = f"{trace.stats.network}.{trace.stats.station}.{trace.stats.channel}.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.mseed"
        trace.write(filename, format="MSEED")


import threading
from time import sleep

def run_client(client):
    try:
        client.run()
        client.close()
    except Exception as e:
        print(f"Client run terminated with exception: {e}")
    finally:
        print("Client run method exited.")

# Initialize the custom EasySeedLinkClient
client = MySeedLinkClient(server_url='geofon.gfz-potsdam.de:18000')

networks = ["GE"]
stations = ["SMRI", "JAGI"]
channels = ["BHN", "BHE"]

for network in networks:
    for station in stations:
        for channel in channels:
            client.select_stream(network, station, channel)

# Run the client in a separate thread
client_thread = threading.Thread(target=run_client, args=(client,))
client_thread.start()

# Wait for a while before stopping (e.g., 30 seconds)
sleep(20)

# Signal the client to stop and wait for the thread to finish
print("stopping")
client.conn.terminate()
client_thread.join()

print("Client has been stopped and thread has joined. Exiting.")