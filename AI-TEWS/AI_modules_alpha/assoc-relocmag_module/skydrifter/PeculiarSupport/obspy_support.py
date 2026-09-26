from skydrifter.Utils.nonpartisan import *
from skydrifter.Utils.partisan import *

import obspy as op

def convert_timestamp(tr):
    st_timestamp = (tr.stats.starttime).timestamp
    et_timestamp = (tr.stats.endtime).timestamp
    n = tr.stats.npts
    delta = tr.stats.delta
    t_timestamp = [st_timestamp+(delta*i) for i in range(0,n)]
    return t_timestamp

def core_merge_overlap_traces(st):
    # Get Logical Variable
    logic_true = []
    logic_false = []
    logic = []
    for i in range(0,len(st)-1):
        t1 = st[i].stats.starttime.timestamp
        t2 = st[i].stats.endtime.timestamp
        t3 = st[i+1].stats.starttime.timestamp
        if (t3 > t1 and t3 < t2) == True:
            logic_true.append(i)
        elif (t3 > t1 and t3 < t2) == False:
            logic_false.append(i)
        logic.append((t3 > t1 and t3 < t2))
    # Make Indexer Container
    start_index = []
    end_index = []
    # For Start Indexer
    if logic[0] == True:
        start_index.append(0)
    # After First Indexer
    for i in range(0,len(logic)-1):
        if logic[i] == False and logic[i+1] == True:
            start_index.append(i+1)
        elif logic[i] == True and logic[i+1] == False:
            end_index.append(i+1)
    # For Last Indexer
    if logic[-1] == True:
        end_index.append(len(logic))
    # Merge Overlap Trace and Assign It In New Stream
    overlap_traces = []
    all_overlap_index = []
    for i in range(0,len(start_index)):
        traces = [st[i].copy() for i in range(start_index[i],end_index[i]+1)]
        all_overlap_index.append([i for i in range(start_index[i],end_index[i]+1)])
        stn = op.Stream(traces=traces)
        stn.merge()
        overlap_traces.append(stn[0])
    new_stream = op.Stream(traces=overlap_traces)
    # Reinput All Non Overlap Traces
    if len(all_overlap_index) == 0:
        raise Exception("Sorry, you don't have any overlapping traces in this stream")
    overlap_index = merge_list(all_overlap_index)
    non_overlap_index = []
    for i in range(0,len(st)):
        if find_index_list(i,overlap_index) == None:
            non_overlap_index.append(i)
    for i in non_overlap_index:
        new_stream += st[i].copy()
    new_stream.sort()
    # Check Logical Again
    logic_true = []
    logic_false = []
    logic = []
    for i in range(0,len(new_stream)-1):
        t1 = new_stream[i].stats.starttime.timestamp
        t2 = new_stream[i].stats.endtime.timestamp
        t3 = new_stream[i+1].stats.starttime.timestamp
        if (t3 > t1 and t3 < t2) == True:
            logic_true.append(i)
        elif (t3 > t1 and t3 < t2) == False:
            logic_false.append(i)
        logic.append((t3 > t1 and t3 < t2))
    # Return New Stream
    return new_stream,sum(logic)

def merge_overlap_traces(st):
    logic = 1
    while logic != 0:
        st,logic = core_merge_overlap_traces(st)
    new_stream = st.copy()
    return new_stream