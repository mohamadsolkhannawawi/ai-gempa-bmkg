from skydrifter.Utils.partisan import *
from skydrifter.Utils.nonpartisan import *

import numpy as np

from scipy.signal import hilbert, chirp
from obspy.signal.trigger import classic_sta_lta

class TraceAttribute:
    def __init__(self,trace):
        self.trace = trace

    def instantaneous_amplitude(self):
        new_trace = self.trace.copy()
        new_trace.detrend()
        hilbert_transform = hilbert(self.trace.data)
        new_trace.data = np.abs(hilbert_transform)
        return new_trace

    def first_envelope_derivative(self):
        new_trace = TraceAttribute.instantaneous_amplitude(self)
        new_trace.detrend()
        attribute = np.gradient(new_trace.times(), new_trace.data)
        new_trace.data = np.array(attribute)
        return new_trace

    def second_envelope_derivative(self):
        new_trace = TraceAttribute.first_envelope_derivative(self)
        new_trace.detrend()
        attribute = np.gradient(new_trace.times(), new_trace.data)
        new_trace.data = np.array(attribute)
        return new_trace
        
    def instantaneous_phase(self):
        new_trace = self.trace.copy()
        new_trace.detrend()
        hilbert_transform = hilbert(self.trace.data)
        new_trace.data = np.unwrap(np.angle(hilbert_transform))
        return new_trace

    def instantaneous_frequency(self):
        new_trace = TraceAttribute.instantaneous_phase(self)
        new_trace.detrend()
        attribute = np.gradient(new_trace.times(), new_trace.data)
        new_trace.data = np.array(attribute)
        return new_trace

    def instantaneous_acceleration(self):
        new_trace = TraceAttribute.instantaneous_frequency(self)
        new_trace.detrend()
        attribute = np.gradient(new_trace.times(), new_trace.data)
        new_trace.data = np.array(attribute)
        return new_trace

    def cosine_phase(self):
        new_trace = TraceAttribute.instantaneous_phase(self)
        new_trace.detrend()
        attribute = (np.cos(new_trace.data))
        new_trace.data = np.array(attribute)
        return new_trace

    def classic_sta_lta(self,sta=5,lta=20):
        new_trace = self.trace.copy()
        new_trace.detrend()
        nsta = int(sta * new_trace.stats.sampling_rate)  
        nlta = int(lta * new_trace.stats.sampling_rate)
        new_trace.data = classic_sta_lta(new_trace.data, nsta, nlta)
        return new_trace