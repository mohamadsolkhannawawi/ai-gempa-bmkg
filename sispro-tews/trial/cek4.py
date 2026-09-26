from multiprocessing import Process
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy import Stream
from multiprocessing.pool import ThreadPool


class MyClient(EasySeedLinkClient):
    def __init__(self, server_url, station, output_filename):
        super().__init__(server_url)
        self.stream = Stream()
        self.station = station
        self.output_filename = output_filename
        
    def on_data(self, trace):
        print(f'Received trace for station {self.station}:')
        print(trace)
        self.stream += trace

        # Placeholder condition for demonstration
        if len(self.stream) >= 2:
            self.save_stream_to_mseed(self.output_filename.format(self.station))
            # Consider if you want to clear the stream after saving
            # self.stream.clear()
            
    def save_stream_to_mseed(self, filename):
        self.stream.write(filename, format='MSEED')
        print(f"Data for station {self.station} written to {filename}")

def run_client_for_station(server_url, network, station, channel, output_filename):
    client = MyClient(server_url, station, output_filename)
    try:
        
        client.select_stream(network, station, channel)
        client.run()
    except KeyboardInterrupt:
        print(f"Stopped by user for station {station}")
        if not client.stream.isEmpty():
            client.save_stream_to_mseed(output_filename.format(station))

# Configuration
server_url = 'geofon.gfz-potsdam.de:18000'
network = "GE"
stations = ['BBJI', 'BKB', 'BNDI', 'JAGI', 'FAKI', 'GSI', 'LHMI', 'LUWI', 'MNAI', 'PLAI', 'SANI', 'SMRI', 'SOEI', 'TNTI', 'TOLI2', 'PMBI']
channel = "BHZ"
output_filename_pattern = "output_{}.mseed"


pool = ThreadPool(64)

for station in stations:
    print(station)
    pool.apply_async(run_client_for_station, args=(server_url, network, station, channel, output_filename_pattern))


# Create and start a process for each station
# processes = []
# for station in stations:
#     process = Process(target=run_client_for_station, args=(server_url, network, station, channel, output_filename_pattern))
#     process.start()
#     processes.append(process)

# # Wait for all processes to complete
# for process in processes:
#     process.join()

print("Data acquisition for all stations complete.")
