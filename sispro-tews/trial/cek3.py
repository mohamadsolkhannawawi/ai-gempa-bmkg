from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy import Stream
import obspy

class MyClient(EasySeedLinkClient):
    def __init__(self, server_url):
        super().__init__(server_url)
        self.stream = Stream()  # Initialize an empty Stream object to accumulate traces
        
    def on_data(self, trace):
        print('Received trace:')
        print(trace)
        self.stream += trace  # Add the received trace to the stream

        # Here you can implement a condition to save and clear the stream
        # For example, save every hour or when the stream reaches a certain size
        # This is a simple placeholder condition
        if len(self.stream) >= 2:  # Arbitrary condition for demonstration
            self.save_stream_to_mseed("output.mseed")
            # self.stream.clear()  # Clear the stream after saving
            
    def save_stream_to_mseed(self, filename):
        self.stream.write(filename, format='MSEED')
        print(f"Data written to {filename}")

# Usage
server_url = 'geofon.gfz-potsdam.de:18000'
client = MyClient(server_url)
network = "GE"
station = "BBJI"
channel = "BHZ"

client.select_stream(network, station, channel)

try:
    client.run()
except KeyboardInterrupt:
    print("Stopped by user")
    if not client.stream.isEmpty():
        client.save_stream_to_mseed("output_final.mseed")
