import os
import obspy
import numpy as np
import pandas as pd
from tqdm import tqdm
from obspy import read
import matplotlib.pyplot as plt
from obspy import Trace, Stream
from obspy.signal.filter import bandpass
from obspy.signal.trigger import classic_sta_lta

def get_stalta(data, window=80, sr=20, plotting=False):
    # Create a Trace object
    tr = Trace(data=data)
    # Additional metadata can be set as needed, for instance:
    tr.stats.sampling_rate = 20.0  # Sample rate in Hz
    tr.stats.station = "ABC"  # Station name
    tr.stats.network = "XY"  # Network code
    # If you want to group this trace with others in a Stream:
    st = Stream([tr])

    def running_mean_high_pass(data, window_length):
        running_mean = np.convolve(data, np.ones(window_length)/window_length, mode='same')
        return data - running_mean

    def inverse_taper(data, window_length):
        taper = np.hanning(window_length * 2)[window_length:]  # Using second half of hanning window for ITAPER
        # Apply taper at the start and end of the data
        data[:window_length] *= taper
        data[-window_length:] *= taper[::-1]
        return data

    # Read the mseed data
    trace = st[0]
    data = trace.data

    # Apply RMHP
    data_rmhp = running_mean_high_pass(data, 10)

    # Apply ITAPER
    data_itaper = inverse_taper(data_rmhp, 30)

    # Apply Butterworth bandpass filter
    data_bw = bandpass(data_itaper, 0.7, 2, trace.stats.sampling_rate, corners=4, zerophase=True)

    if plotting:
        # For visualization, let's plot the original and processed data
        plt.figure(figsize=(4, 1))
        plt.plot(trace.times(), data, label='Original')
        plt.plot(trace.times(), data_bw, label='Processed', linewidth=2)
        plt.legend()
        plt.show()

    tr.data = data_bw

    # Configuration
    trigger_on = 3.0  # Threshold to activate pick
    trigger_off = 1.5  # Threshold to deactivate pick
    T_minOffset = trigger_on  # Similar to the trigger threshold by default
    T_dead = 30  # Example dead time; adjust as needed

    # Compute STA/LTA ratio
    sta_length = int(2 * sr)  # Example 1-second STA window; adjust as needed (2)
    lta_length = int(window * sr)  # Example 10-second LTA window; adjust as needed (80)
    ratio = classic_sta_lta(tr.data, sta_length, lta_length)

    # Detect triggers
    triggers = []
    active = False
    last_pick_time = None

    for i, value in enumerate(ratio):
        if not active and value >= trigger_on:
            triggers.append(tr.times()[i])
            active = True
            last_pick_time = tr.times()[i]
        elif active and value <= trigger_off:
            active = False

        # Reactivate re-picker based on conditions
        if last_pick_time:
            dt = tr.times()[i] - last_pick_time
            if T_dead > 0:
                threshold = T_minOffset + (tr.data[i] * np.exp(-(dt / T_dead)**2))
            else:
                threshold = T_minOffset
            if value < trigger_off and tr.data[i] >= threshold:
                active = True

    return triggers