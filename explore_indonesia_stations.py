#!/usr/bin/env python3
"""
Explore Indonesia seismic stations from audit results - FIXED VERSION
Deep recursive search for nested station data.
"""

import json
from collections import defaultdict

INDO_BBOX = {'min_lat': -11.5, 'max_lat': 6.5, 'min_lon': 94.5, 'max_lon': 141.5}

def find_station_lists(obj, path="", depth=0):
    """Recursively find station lists."""
    results = []
    if depth > 5:
        return results
    
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                first_keys = list(v[0].keys())
                if ('network' in first_keys and 'code' in first_keys) or 'stations' in k.lower():
                    results.append((new_path, v))
            results.extend(find_station_lists(v, new_path, depth+1))
    elif isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], dict):
        first_keys = list(obj[0].keys())
        if 'network' in first_keys and 'code' in first_keys:
            results.append((f"{path}[list]", obj))
    return results

def main():
    try:
        with open('seedlink_audit_v2_evidence/results.json') as f:
            d = json.load(f)
    except FileNotFoundError:
        print("ERROR: results.json not found")
        return

    print("="*80)
    print("INDONESIA STATIONS EXPLORER (Deep Search)")
    print("="*80)
    print()
    
    candidates = find_station_lists(d)
    print(f"Found {len(candidates)} station lists:\n")
    
    for path, stations in candidates:
        print(f"  {path}: {len(stations)} stations")
        if stations:
            s = stations[0]
            print(f"    Example: {s.get('network','?')}.{s.get('code','?')}")
    
    print("\n" + "="*80)
    print("FILTERING INDONESIA BBOX")
    print("="*80 + "\n")
    
    all_indo = []
    for path, stations in candidates:
        indo = []
        for s in stations:
            lat = s.get('latitude') or s.get('lat')
            lon = s.get('longitude') or s.get('lon')
            if lat and lon:
                if INDO_BBOX['min_lat'] <= lat <= INDO_BBOX['max_lat'] and \
                   INDO_BBOX['min_lon'] <= lon <= INDO_BBOX['max_lon']:
                    indo.append(s)
        if indo:
            print(f"  {path}: {len(indo)} Indonesia stations")
            all_indo.extend(indo)
    
    seen = set()
    unique = []
    for s in all_indo:
        key = (s.get('network'), s.get('code'))
        if key not in seen:
            seen.add(key)
            unique.append(s)
    
    print(f"\nTotal unique: {len(unique)}\n")
    
    if not unique:
        print("⚠ No stations found. Debugging first 2 lists:\n")
        for path, stations in candidates[:2]:
            print(f"{path} sample:")
            for s in stations[:2]:
                print(f"  {s.get('network','?')}.{s.get('code','?')}  lat={s.get('latitude','?')} lon={s.get('longitude','?')}")
        return
    
    print("="*80)
    print("BY NETWORK")
    print("="*80 + "\n")
    
    by_net = defaultdict(list)
    for s in unique:
        by_net[s.get('network')].append(s)
    
    for net in sorted(by_net.keys()):
        print(f"{net}: {len(by_net[net])} stations")
        for s in by_net[net]:
            code = s.get('code','?')
            lat = s.get('latitude') or s.get('lat') or 0
            lon = s.get('longitude') or s.get('lon') or 0
            country = s.get('country_code') or '?'
            print(f"  {net}.{code:6s}  {lat:7.3f},{lon:8.3f}  ({country})")
    
    print("\n" + "="*80)
    print("CSV FORMAT (for station_indonesia.csv)")
    print("="*80 + "\n")
    
    id_only = [s for s in unique if s.get('country_code') == 'ID']
    target = id_only if id_only else unique
    
    print("_id,name,code,network,channel,location,longitude,latitude,elevation,server_seedlink,server_fdsn")
    for s in target:
        _id = s.get('_id', 'gen_'+s.get('code','x'))
        name = s.get('name', s.get('code',''))
        code = s.get('code')
        net = s.get('network')
        chan = str(s.get('channel', ['BHZ','BHN','BHE']))
        loc = s.get('location', '00') or '00'
        lon = s.get('longitude') or s.get('lon') or 0
        lat = s.get('latitude') or s.get('lat') or 0
        elev = s.get('elevation') or 0
        srv_sl = s.get('server_seedlink', 'rtserve.earthscope.org:18000')
        srv_fdsn = s.get('server_fdsn', 'EARTHSCOPE')
        print(f'{_id},"{name}",{code},{net},"{chan}",{loc},{lon},{lat},{elev},{srv_sl},{srv_fdsn}')
    
    print("\n" + "="*80)

if __name__ == '__main__':
    main()
