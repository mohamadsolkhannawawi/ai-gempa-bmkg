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
from repositories.station_repository import station_find_by_code_and_network_repository
load_dotenv("./.env")

kafka_host = os.getenv('kafka_host')
kafka_port = os.getenv('kafka_port')
seedlink_url = os.getenv('seedlink_url')
regional = os.getenv('regional')

def json_serializer(data):
    return json.dumps(data).encode('utf-8')

producer = KafkaProducer(bootstrap_servers=kafka_host+":"+kafka_port, value_serializer=json_serializer)

def get_waveform_data(db,fdsn_urls, network, station, location, channel):
    #get current date
    today = datetime.utcnow().date()
    
    utc_year = str(today.year)
    utc_julian_day = today.strftime('%j')
    path_save_day = "../archive/"+str(today.year)+"/"+network+"/"+station+"/"+channel+".D"
    day_mseed_filename = f"{network}.{station}.{location}.{channel}.D.{utc_year}.{utc_julian_day}.mseed"
    day_mseed_filepath = os.path.join(path_save_day, day_mseed_filename)
    print(day_mseed_filepath)
    print()
    if os.path.isfile(day_mseed_filepath):
        print("checking for ", network," ",station, " ", location, " ", channel )
        sts = read(day_mseed_filepath)
        # sts = read("../archive_data/2024-03-24/GE/JAGI/BHN/day_mseed/GE.JAGI..BHN.2024.084.mseed")
        sts.sort(keys=['starttime'])
        
        for index in range(len(sts)):
            print(sts[index].stats.starttime)
            if index != len(sts) - 1:
                if sts[index].stats.endtime !=  sts[index+1].stats.starttime:
                    for fdsn_url in fdsn_urls:
                        client = FDSNClient(fdsn_url)
                        try:
                            st = client.get_waveforms(
                                network=network, 
                                station=station, 
                                location=location,
                                channel=channel, 
                                starttime=sts[index].stats.endtime , 
                                endtime=sts[index+1].stats.starttime)
                            print(st)
                            
                            if os.path.isfile(path_save_day+"/"+day_mseed_filename) == True:

                                print("in come")
                                try:

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
                                        waveform2 = st[0].data

                                        import time
                                        station_data = station_find_by_code_and_network_repository(db, st[0].stats.station, st[0].stats.network,)

                                        json_string = {
                                            "date":str(today),
                                            "starttime":str(st[0].stats.starttime),
                                            "endtime":str(st[0].stats.endtime),
                                            "sampling_rate": st[0].stats.sampling_rate,
                                            # "record_length": trace.stats.number_of_records,
                                            "delta": st[0].stats.delta,
                                            "location": st[0].stats.location,
                                            "location_database":station_data["location"],
                                            "longitude":station_data["longitude"],
                                            "latitude":station_data["latitude"],
                                            "npts": st[0].stats.npts,
                                            "station":st[0].stats.station,
                                            "network":st[0].stats.network,
                                            "channel":st[0].stats.channel,
                                            "expiration_timestamp":int(time.time()) + 1800,
                                            "waveform":waveform2.tolist()
                                        }

                                        producer.send('waveform_seedlink',json.dumps (json_string))
                                        # Ensure all messages are sent and then close the producer
                                        producer.flush()
                    
                                        trace = st[0].interpolate(sampling_rate=5) 
                                        waveform3 = trace.data
                                        json_string = {
                                            "date":str(today),
                                            "starttime":str(trace.stats.starttime),
                                            "endtime":str(trace.stats.endtime),
                                            "sampling_rate": trace.stats.sampling_rate,
                                            # "record_length": trace.stats.number_of_records,
                                            "delta": trace.stats.delta,
                                            "location": trace.stats.location,
                                            "location_database":station_data["location"],
                                            "longitude":station_data["longitude"],
                                            "latitude":station_data["latitude"],
                                            "npts": trace.stats.npts,
                                            "station":trace.stats.station,
                                            "network":trace.stats.network,
                                            "channel":trace.stats.channel,
                                            "expiration_timestamp":int(time.time()) + 1800,
                                            "waveform":waveform3.tolist()
                                        }
                                        channel = trace.stats.network+"."+trace.stats.station+"." + trace.stats.location + "."+ trace.stats.channel
                                        
                                      
                                        publish_redis_message(channel, json.dumps(json_string))
                                        print("file missing filled")
                                    except Exception as e:
                                        print("ASU")
                                        print(f"An error occurred while merging: {e}")
                                except UserWarning as w:
                                    
                                    print("warnning "+str(w))
                                except Exception as e:
                                    print("ASU")
                                    print(f"An error occurred while merging: {e}")

                        except UserWarning as w:
                            print("warnning "+str(w))
                            continue
                        except Exception as e:
                            print("An error occurred:", e)
                            continue