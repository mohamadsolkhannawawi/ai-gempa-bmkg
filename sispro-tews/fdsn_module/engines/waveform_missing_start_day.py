from kafka import KafkaProducer
import os, json
from datetime import date, datetime, timedelta
from dotenv import load_dotenv
import natsort
from configuration.redis import publish_redis_message
import natsort
from obspy.clients.seedlink.easyseedlink import EasySeedLinkClient
from obspy import Stream
from obspy.clients.fdsn import Client as FDSNClient
from obspy import UTCDateTime
from obspy import read
from utils.util import get_gmt_7_time
from utils.util import check_and_make_existing_path
from utils.util import extract_sort_key

load_dotenv("./.env")

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
seedlink_url = os.getenv('seedlink_url')
regional = os.getenv('regional')

def json_serializer(data):
    return json.dumps(data).encode('utf-8')

producer = KafkaProducer(bootstrap_servers=kafka_host+":"+kafka_port, value_serializer=json_serializer)

def get_waveform_data_start_day(fdsn_url, network, station, channel):
    #get current date
    today = datetime.utcnow().date()
    
    print("checking for ", network," ",station, " ", channel )
    path = "../archive_data/"+str(today)+"/"+network+"/"+station+"/"+channel
    if os.path.exists(path)== False:
        return

    if len(os.listdir(path)) > 1:
        
        files_with_extension = [file for file in os.listdir(path) if file.endswith(".mseed")]

        waveform_files = sorted(files_with_extension, key=extract_sort_key)
    
        waveform_files = natsort.natsorted(files_with_extension)
        utc_year = str(today.year)
        utc_julian_day = str(today.strftime('%j'))
        file_name_start_day = utc_year+"."+utc_julian_day+"_000000"
        

        if file_name_start_day not in waveform_files[0]:
            file_name_end_time = waveform_files[0].split("__")
            end_time_only = waveform_files[0].split("__")[0].split("_")[1]
            start_time = str(today) +"T00:00:00"
            end_time =  str(today) +"T"+f"{end_time_only[:2]}:{end_time_only[2:4]}:{end_time_only[4:]}"
            end_time1_obj = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
            start_time2_obj = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")

            starttime = UTCDateTime(end_time1_obj)
            endtime = UTCDateTime(start_time2_obj)

            client = FDSNClient(fdsn_url)
            try:
                st = client.get_waveforms(
                    network=network, 
                    station=station, 
                    location="",
                    channel=channel, 
                    starttime=starttime, 
                    endtime=endtime)
                print(st)
                # Save waveform to file, optional
                path_save_day = "../archive/"+str(today.year)+"/"+network+"/"+station+"/"+channel+".D"
                
                utc_year = str(today.year)
                utc_julian_day = str(today.strftime('%j'))
            
                day_mseed_filename = network+"."+station+".."+channel+".D."+utc_year+"."+utc_julian_day+""
                if os.path.isfile(path_save_day+"/"+day_mseed_filename) == True:

                    st1 = read(path_save_day+"/"+day_mseed_filename)
                    try:
                        existing_traces = [tr for tr in st1 if tr.stats.station == st[0].stats.station and
                                                tr.stats.network == st[0].stats.network and
                                                tr.stats.starttime == st[0].stats.starttime and
                                                tr.stats.endtime == st[0].stats.endtime]

                        if existing_traces:
                                    # Replace the existing trace(s) with the new trace
                            for tr in existing_traces:
                                st1.traces.remove(tr)
                                st1.append(st[0])
                                st1.sort(keys=['starttime'])
                                st.sort(keys=['starttime'])
                        else:
                                    # Simply append the new trace if no identical trace exists
                            st1.append(st[0])
                            st1.sort(keys=['starttime'])
                            st.sort(keys=['starttime'])

                        st1.write(path_save_day+"/"+day_mseed_filename, format='MSEED')
                    except Exception as e:
                        print("ASU")
                        print(f"An error occurred while merging: {e}")

                            
                    waveform2 = st[0].data

                            # start_time_respond = str(st[0].stats.starttime).split("T")[1].replace("Z", "")
                            # end_time_respond= str(st[0].stats.endtime).split("T")[1].replace("Z", "")

                    start_time_file = str(st[0].stats.starttime).split("T")[1].replace("Z", "")[:-7].replace(":","")
                    end_time_file = str(st[0].stats.endtime).split("T")[1].replace("Z", "")[:-7].replace(":","")
                    filename = st[0].stats.network+"."+st[0].stats.station+"."+st[0].stats.location+"."+st[0].stats.channel+".mseed"
            
                    import time
                    json_string = {
                        "date":str(today),
                        "time_start":st[0].stats.starttime,
                        "time_end":st[0].stats.endtime,
                        "sampling_rate": st[0].stats.sampling_rate,
                                # "record_length": trace.stats.number_of_records,
                        "delta": st[0].stats.delta,
                        "location": st[0].stats.location,
                        "npts": st[0].stats.npts,
                        "station":st[0].stats.station,
                        "network":st[0].stats.network,
                        "channel":st[0].stats.channel,
                        "expiration_timestamp":int(time.time()) + 1800,
                        "waveform":waveform2.tolist()
                    }

                    file_period_path_save = path+"/"+utc_year+"."+utc_julian_day+"_"+start_time_file+"__"+end_time_file+"_"+filename
                            # Format back to a string if needed
                            # trace.data = np.require(trace.data, dtype=np.float64)
                    print("saved")
                    st.write(file_period_path_save, format='MSEED')
                        
                            # st.write(path+"/"+file_waveform_times1[1]+"_"+file_waveform_times2[0]+"_"+network+"."+station+"."+channel+".mseed", format="MSEED")
                        
                             # Send a message
                    producer.send('waveform_seedlink',json.dumps (json_string))
                            # Ensure all messages are sent and then close the producer
                    producer.flush()

                    channel = network+"."+station+".."+channel
                    publish_redis_message(channel, json.dumps (json_string))
        
            except Exception as e:
                print("An error occurred:", e)
        