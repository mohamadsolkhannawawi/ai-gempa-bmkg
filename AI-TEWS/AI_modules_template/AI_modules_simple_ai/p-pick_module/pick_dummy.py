import os
import random
import time
import obspy
from obspy.clients.filesystem.sds import Client
from obspy import UTCDateTime

ARCHIVE_DIR = "../../archive"

class DummySDSConsumer():
    def __init__(self, pull_time, delay):
        self.pull_time = pull_time
        self.delay = delay
        self.client_sds = None
        self.data = []
        self.network = None
        self.station = None
        self.location = None
        self.channel = None

    def set_client(self,
                   year: int,
                   network: str,
                   station: str,
                   channel: str,
                   sds_type: str,
                   location: str,
                   doy: int):
        
        # Init selfs
        self.network = network
        self.station = station
        self.location = location
        self.channel = channel

        # Define SDS filename
        doy = "{:03d}".format(doy) # must be 3-digit int
        sds_filename = f"{year}/{network}/{station}/{channel}.{sds_type}/{network}.{station}.{location}.{channel}.{sds_type}.{year}.{doy}"
        
        # Get current SDS mseed available data
        stream = obspy.read(f"{ARCHIVE_DIR}/"+sds_filename)

        # Initialize SDS Client if data exists
        if len(stream) != 0:
            print("Available data: ")
            print(stream)
            Client.FMTSTR = sds_filename
            
            self.client_sds = Client(sds_root=os.path.abspath(f'{ARCHIVE_DIR}'))
        else:
            print("Failed to initialize SDS Client: No data available")

    def fill_data(self, starttime: UTCDateTime, endtime: UTCDateTime):
        if self.client_sds != None:
            st = self.client_sds.get_waveforms(
                network=self.network,
                station=self.station,
                location=self.location,
                channel=self.channel,
                starttime=starttime, 
                endtime=endtime
            )

            future = []
            for trace in st:
                curr_time = trace.stats.starttime
                
                while curr_time <= trace.stats.endtime:
                    pull = random.uniform(self.pull_time-1, self.pull_time+1) # second
                    new_time = curr_time + pull
                    data = trace.slice(curr_time, new_time)
                    data_dict = {
                        "date":curr_time.day,
                        "starttime":str(data.stats.starttime),
                        "endtime":str(data.stats.endtime),
                        "sampling_rate": data.stats.sampling_rate,
                        # "record_length": data.stats.number_of_records,
                        "delta": data.stats.delta,
                        "location": data.stats.location,
                        "npts": data.stats.npts,
                        "station":data.stats.station,
                        "network":data.stats.network,
                        "channel":data.stats.channel,
                        "waveform":data.data.tolist()
                    }
                    if random.randint(0, 1) == 1:
                        self.data.append(data_dict)
                    else:
                        future.append(data_dict)
                    curr_time = new_time
            
            self.data += future
        else:
            print("Client unavailable")

    def __iter__(self):
        return iter(self.data)



# for trace in obspy.read("../sispro-tews/archive/"+filename):

# 10s[11-20s] 20s (last processed 20)
# GE.JAGI.BHE: [31-40s] 40s ()
# [4s]
# [6s]
# [8s]
# [1-10s] #1 - 10 diproses dapet titik 5 (atau 1-10) (last processed 10)
# [3-12s] #2 - 11, 3 - 12, (last processed 12)
# [14S] #4 - 13, 5 - 14, (last processed 14)
# [17s] #7 - 16, 8 - 17

# GE.JAGI.BHE: [10s]
# GE.JAGI.BHN: [10s]
# GE.JAGI.BHZ: [10s]


# Event association (pick buffer)
# id: {station_detail, timestamp} # timeout 100 detik
# id: {station_detail, timestamp}
# id: {station_detail, timestamp}
# id: {station_detail, timestamp}

# Client.FMTSTR= year+'/'+network+'/'+station+'/'+channel+'.'+sds_type+'/'+network+'.'+station+'.'+location+'.'+channel+'.'+sds_type+'.'+year+'.'+doy

# client_sds = Client(sds_root=os.path.abspath('./archive'))
# print(year+'/'+network+'/'+station+'/'+channel+'.'+sds_type+'/'+network+'.'+station+'.'+location+'.'+channel+'.'+sds_type+'.'+year+'.'+doy)
# st = client_sds.get_waveforms(
#     network=network, 
#     station=station, 
#     location=location, 
#     channel=channel, 
#     starttime=UTCDateTime(starttime), 
#     endtime=UTCDateTime(endtime)
# )

# if (len(st) != 0):
#     json_string = {
#         "time_start":str(st[0].stats.starttime),
#         "time_end":str(st[0].stats.endtime),
#         "sampling_rate": st[0].stats.sampling_rate,
#             # "record_length": trace.stats.number_of_records,
#         "delta": st[0].stats.delta,
#         "location": st[0].stats.location,
#         "npts": st[0].stats.npts,
#         "station":st[0].stats.station,
#         "network":st[0].stats.network,
#         "channel":st[0].stats.channel,
#         "waveform":(st[0].data/1000).tolist()
#     }
#     print(json_string)
# else:
#     print("Empty data")



# Redis dan