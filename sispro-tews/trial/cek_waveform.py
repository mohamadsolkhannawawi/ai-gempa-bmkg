from obspy import read
from obspy.core import UTCDateTime

sts = read("../archive/2024/IA/AAI/HNE.D/IA.AAI..HNE.D.2024.187.mseed")
# sts = read("../archive_data/2024-03-24/GE/JAGI/BHN/day_mseed/GE.JAGI..BHN.2024.084.mseed")
sts.sort(keys=['starttime'])
print(sts[0].stats)
# print(st)  
for st in sts:
    print(st)
for st in sts:
    print(st.stats.starttime)



# start_time = UTCDateTime("2024-03-24T16:04:05")  # Adjust date to match your data
# end_time = UTCDateTime("2024-03-24T16:07:53") 

# filtered_stream = sts.slice(starttime=start_time, endtime=end_time)
# filtered_stream.sort(keys=['starttime'])
# filtered_stream.merge(method=1, interpolation_samples=0)
# # print(filtered_stream.merge(method=1, fill_value='interpolate', interpolation_samples=0))
# print()
# # Print the filtered stream summary
# print(filtered_stream)
# print(filtered_stream[0].data)
# print(len(filtered_stream))

# print(st[0].stats) 

# for k, v in sorted(st[0].stats.mseed.items()):
#     print("'%s': %s" % (k, str(v))) 

# print(st[0].data)
# print(len(st[0].data))