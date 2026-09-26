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

def get_waveform_data_end_day(fdsn_url, network, station, channel):
    #get current date
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)

    print("checking for ", network," ",station, " ", channel )
    path_yesterday = "../archive_data/"+str(yesterday)+"/"+network+"/"+station+"/"+channel
    path_today = "../archive_data/"+str(today)+"/"+network+"/"+station+"/"+channel
    if os.path.exists(path_yesterday)== False:
        return
    if os.path.exists(path_today)== False:
        return

    if len(os.listdir(path_yesterday)) > 1  and len(os.listdir(path_today)) > 1 :
        
        files_with_extension_today = [file for file in os.listdir(path_today) if file.endswith(".mseed")]
        files_with_extension_yesterday = [file for file in os.listdir(path_yesterday) if file.endswith(".mseed")]

        today_waveform_files = sorted(files_with_extension_today, key=extract_sort_key)
        yesterday_waveform_files = sorted(files_with_extension_yesterday, key=extract_sort_key)
    
        today_waveform_files = natsort.natsorted(today_waveform_files)
        yesterday_waveform_files = natsort.natsorted(yesterday_waveform_files)

        today_utc_year = str(today.year)
        today_julian_day = str(today.strftime('%j'))

        yesterday_utc_year = str(yesterday.year)
        yesterday_julian_day = str(yesterday.strftime('%j'))


        yesterday_last_date_time = yesterday_waveform_files[-1].split("__")[1].split("_")[0]
        today_start_date_time = today_waveform_files[0].split("__")[0].split("_")[1]

        if "__00" not in yesterday_waveform_files[0]:
            start_time = str(yesterday)+"T"+f"{yesterday_last_date_time[:2]}:{yesterday_last_date_time[2:4]}:{yesterday_last_date_time[4:]}"

            end_time =  str(today) +"T"+f"{today_start_date_time[:2]}:{today_start_date_time[2:4]}:{today_start_date_time[4:]}"
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
                path_save_day = "../archive/"+str(yesterday.year)+"/"+network+"/"+station+"/"+channel+".D"
                
                utc_year = str(yesterday.year)
                utc_julian_day = str(yesterday.strftime('%j'))
            
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

                    file_period_path_save = path_yesterday+"/"+utc_year+"."+utc_julian_day+"_"+start_time_file+"__"+end_time_file+"_"+filename
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
        