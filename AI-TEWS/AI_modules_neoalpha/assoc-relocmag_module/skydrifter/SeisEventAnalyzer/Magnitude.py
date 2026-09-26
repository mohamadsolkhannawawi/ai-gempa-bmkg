import numpy as np
import obspy as op 
from obspy.geodetics import gps2dist_azimuth
from math import log10

def determine_local_magnitude(dfa,trace,inventory):
    # Documentation
    """
        Purpose :
        Calculate local magnitude use only vertical component data, we remove response first and we simulate the trace to wood anderson seismogram

        Parameter Input Definition :
        - dfa (pandas.core.series.Series, requried column = ['Station','P','Latitude','Longitude','Depth'])
        - trace (obspy.core.stream.Stream, please just input one trace in stream data)
        - inventory(obspy.core.inventory.inventory.Inventory, contain file like lat, long, depth, or intrument data of station)
        - **args --> nope
        - **kwargs --> nope

        Parameter Output Definition :
        - magnitude (scalar, float)
        
        Example :
        >> nope
        >> nope
        >> nope
        >> nope
    """
    # Part 1
    try:
        station = inventory.select(station=dfa['Station'], channel='**Z')[0][0]
        sta_lat = station.latitude
        sta_lon = station.longitude
    except IndexError:
        raise ValueError(f"No station information found for {dfa['Station']}")
    # Part 2
    dist, az, baz = gps2dist_azimuth(dfa['Latitude'], dfa['Longitude'], sta_lat, sta_lon)
    dist = dist / 1000
    dist = np.sqrt(dist ** 2 + dfa['Depth'] ** 2)
    # Part 3
    paz_wa = {'sensitivity': 2800, 'zeros': [0j], 'gain': 1,'poles': [-6.2832 - 4.7124j, -6.2832 + 4.7124j]}
    trace.detrend(type='demean')
    trace.taper(max_percentage=0.005, type='hann', side='both')
    trace.remove_response(inventory=inventory, water_level=True)
    trace.simulate(paz_simulate=paz_wa)
    # Part 4
    ampl_z = max(abs(trace[0].data))
    ampl = np.nanmax([ampl_z])
    # Part 5
    distance = 15
    distance2 = 60
    E, F, G, H = [1, 0, 0.0180, 1.77 + 0.1]
    I, J, K, L = [1, 0, 0.0038, 2.62 + 0.1]
    if dist <= distance:
        magnitude = np.NaN
    elif dist > distance and dist <= distance2:
        magnitude = E * log10(ampl * 1000) + F * log10(dist) + G * dist + H
    else:
        magnitude = I * log10(ampl * 1000) + J * log10(dist) + K * dist + L
    return magnitude

def determine_station_magnitude_m100(dfa,trace,inventory,distance_type='epicentral',trim_after_s=100):
    # Documentation
    """
        Purpose :
        Calculate local magnitude use only vertical component data, we remove response first

        Parameter Input Definition :
        - dfa (pandas.core.series.Series, requried column = ['Station','P','Latitude','Longitude','Depth'])
        - trace (obspy.core.stream.Stream, please just input one trace in stream data)
        - inventory(obspy.core.inventory.inventory.Inventory, contain file like lat, long, depth, or intrument data of station)
        - distance_type (string, we cann choose between hypocentral and epicentral)
        - trim_after_s (float or int, we must cut waveform some seconds after S arrival and we set it 100s by default)
        - **args --> nope
        - **kwargs --> nope

        Parameter Output Definition :
        - magnitude (scalar, float)
        
        Example :
        >> nope
        >> nope
        >> nope
        >> nope
    """
    # Part 1
    try:
        station = inventory.select(station=dfa['Station'], channel='**Z')[0][0]
        sta_lat = station.latitude
        sta_lon = station.longitude
    except IndexError:
        raise ValueError(f"No station information found for {dfa['Station']}")
    # Part 2
    if distance_type == 'epicentral':
        dist, az, baz = gps2dist_azimuth(dfa['Latitude'], dfa['Longitude'], sta_lat, sta_lon)
        dist = dist / 1000
    elif distance_type == 'hypocentral':
        dist, az, baz = gps2dist_azimuth(dfa['Latitude'], dfa['Longitude'], sta_lat, sta_lon)
        dist = dist / 1000
        dist = np.sqrt(dist ** 2 + dfa['Depth'] ** 2)
    # Part 
    # trace.trim(starttime=op.UTCDateTime(dfa['S']),endtime=op.UTCDateTime(dfa['S'])+trim_after_s)
    trace.detrend(type='demean')
    trace.taper(max_percentage=0.005, type='hann', side='both')
    trace.remove_response(inventory=inventory, water_level=True)
    # Part 4
    ampl = max(abs(trace[0].data))
    # Part 5
    a, b, c = 1.23, 1.24, 6.64
    magnitude = a * log10(ampl) + b * log10(dist) + c
    return magnitude