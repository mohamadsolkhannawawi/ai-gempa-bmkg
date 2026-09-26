import numpy as np
from obspy import Trace
import skydrifter as sd
from skydrifter.SeisPreProcess.Algorithm.BandPass import BandPass

def trace_processing(data, sampling_rate):
    header = {
        'network': data['network'],
        'station': data['station'],
        'location': data['location'], 
        'channel': data['channel'],
        'starttime': data['starttime'], 
        'endtime': data['endtime'], 
        'sampling_rate': data['sampling_rate'], 
        'delta': data['delta'],
        'npts': data['npts'],
    }
    trace = Trace(data=np.array(data['waveform']), header=header)
    if trace.stats.sampling_rate!=sampling_rate:
        trace.interpolate(sampling_rate)
    return trace

def waveform_preprocessing(trace):
    preprocessor = sd.SeisPreProcess(stream=trace, algo=BandPass())
    trace = preprocessor.execute()
    return trace