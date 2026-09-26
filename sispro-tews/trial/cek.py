from obspy import UTCDateTime
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
# Subclass the client class
class MyClient(EasySeedLinkClient):
    # Implement the on_data callback
    def on_data(self, trace):
        print('Received trace:')
        # Get the current UTC time
        current_time = UTCDateTime.now()
        print(trace,current_time)

# Connect to a SeedLink server
client = MyClient('geofon.gfz-potsdam.de:18000')

# Retrieve INFO:STREAMS
streams_xml = client.get_info('STREAMS')
# print(streams_xml)

# Select a stream and start receiving data
client.select_stream('GE', 'BBJI', 'BHZ')
client.run()