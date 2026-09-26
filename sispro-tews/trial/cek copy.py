from obspy.clients.fdsn import Client as FDSNClient
from datetime import datetime, timedelta
import time
current_dateTime_before = datetime.now() - timedelta(seconds=10)
current_dateTime = datetime.now()
print(str(current_dateTime_before))
print(str(current_dateTime))

times = str(current_dateTime).split(".")[0].replace(" ", "T")
time_before = str(current_dateTime_before).split(".")[0].replace(" ", "T")
print(times)
print(time_before)
client = FDSNClient("GFZ")
while True:
    
    try:
        st = client.get_waveforms(network="GE", station="BBJI", location="",
                                channel="BHZ", starttime=time_before, endtime=times)
        print(st)
                                    # Save waveform to file, optional  
        st.write("test.mseed", format="MSEED")
    except Exception as e:
        print("An error occurred:", e)
    time.sleep(10)