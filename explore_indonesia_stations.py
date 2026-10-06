#!/usr/bin/env python3
"""
Explore Indonesia seismic stations from audit results.
Find all stations in Indonesia bounding box (-11.5 to 6.5 lat, 94.5 to 141.5 lon)
and recommend which ones to add to station_indonesia.csv for real-time streaming.
"""

import json
from collections import defaultdict

# Indonesia bounding box
INDO_BBOX = {
    'min_lat': -11.5,
    'max_lat': 6.5,
    'min_lon': 94.5,
    'max_lon': 141.5
}

def main():
    # Load audit results
    try:
        with open('seedlink_audit_v2_evidence/results.json') as f:
            d = json.load(f)
    except FileNotFoundError:
        print("ERROR: seedlink_audit_v2_evidence/results.json not found")
        return

    print("=" * 80)
    print("AUDIT RESULTS - INDONESIA SEISMIC STATIONS EXPLORER")
    print("=" * 80)
    print()

    # 1. Show top-level structure
    print("1. AUDIT DATA STRUCTURE:")
    print()
    for k in sorted(d.keys()):
        v = d[k]
        v_type = type(v).__name__
        if isinstance(v, list):
            print(f"   {k:45s} : {v_type:10s} ({len(v):4d} items)")
        elif isinstance(v, dict):
            print(f"   {k:45s} : {v_type:10s} ({len(v):4d} keys)")
        else:
            print(f"   {k:45s} : {v_type:10s}")

    print()
    print("=" * 80)
    print("2. FINDING STATION LISTS")
    print("=" * 80)
    print()

    # Find all station lists (list of dicts with network/code)
    candidates = []

    for key, val in d.items():
        # Direct list of dicts
        if isinstance(val, list) and len(val) > 0:
            if isinstance(val[0], dict):
                first_keys = list(val[0].keys())
                if 'network' in first_keys and 'code' in first_keys:
                    candidates.append((key, val))
                    print(f"   Found: {key}")
                    print(f"     Count: {len(val)}")
                    print(f"     Keys: {', '.join(first_keys[:6])}")
                    print()
        
        # Nested dict -> list of dicts
        elif isinstance(val, dict):
            for subkey, subval in val.items():
                if isinstance(subval, list) and len(subval) > 0:
                    if isinstance(subval[0], dict):
                        first_keys = list(subval[0].keys())
                        if 'network' in first_keys and 'code' in first_keys:
                            candidates.append((f"{key}.{subkey}", subval))
                            print(f"   Found: {key}.{subkey}")
                            print(f"     Count: {len(subval)}")
                            print(f"     Keys: {', '.join(first_keys[:6])}")
                            print()

    print("=" * 80)
    print("3. FILTERING INDONESIA BBOX STATIONS")
    print("=" * 80)
    print()

    all_indo_stations = []

    for key, stations in candidates:
        indo_in_this_key = []
        
        for s in stations:
            lat = s.get('latitude') or s.get('lat')
            lon = s.get('longitude') or s.get('lon')
            
            if lat is None or lon is None:
                continue
            
            # Check bounding box
            if (INDO_BBOX['min_lat'] <= lat <= INDO_BBOX['max_lat'] and
                INDO_BBOX['min_lon'] <= lon <= INDO_BBOX['max_lon']):
                indo_in_this_key.append(s)
        
        if indo_in_this_key:
            print(f"   From {key}: {len(indo_in_this_key)} stations")
            all_indo_stations.extend(indo_in_this_key)

    print()
    print(f"   Total (with duplicates): {len(all_indo_stations)}")
    print()

    # Deduplicate by network.code
    seen = set()
    unique_indo = []

    for s in all_indo_stations:
        key = (s.get('network'), s.get('code'))
        if key not in seen:
            seen.add(key)
            unique_indo.append(s)

    print(f"   Total (unique): {len(unique_indo)}")
    print()

    print("=" * 80)
    print("4. STATIONS BY NETWORK")
    print("=" * 80)
    print()

    by_network = defaultdict(list)
    for s in unique_indo:
        by_network[s.get('network')].append(s)

    for net in sorted(by_network.keys()):
        stations = by_network[net]
        print(f"   {net}: {len(stations)} stations")
        for s in stations:
            code = s.get('code', '?')
            lat = s.get('latitude') or s.get('lat') or 0
            lon = s.get('longitude') or s.get('lon') or 0
            loc = s.get('location', '') or ''
            country = s.get('country_code') or s.get('country') or '?'
            print(f"      {net}.{code:6s}  loc={loc:3s}  lat={lat:7.3f} lon={lon:8.3f}  ({country})")

    print()
    print("=" * 80)
    print("5. RECOMMENDATIONS")
    print("=" * 80)
    print()

    # Filter by country_code == 'ID'
    id_only = [s for s in unique_indo if s.get('country_code') == 'ID']

    if id_only:
        print(f"   ✓ Stations geocoded as Indonesia (country_code='ID'): {len(id_only)}")
        print()
        for s in id_only:
            net = s.get('network')
            code = s.get('code')
            lat = s.get('latitude') or s.get('lat')
            lon = s.get('longitude') or s.get('lon')
            loc = s.get('location', '00') or '00'
            name = s.get('name', code)
            print(f"      {net}.{code:6s}  {name}")
            print(f"        Position: {lat:.3f}, {lon:.3f}")
            print(f"        Location code: {loc}")
            print()
    else:
        print("   ⚠ No stations with country_code='ID'")
        print("   Fallback: Using all stations in Indonesia bbox:")
        print()
        for s in unique_indo[:15]:
            net = s.get('network')
            code = s.get('code')
            lat = s.get('latitude') or s.get('lat')
            lon = s.get('longitude') or s.get('lon')
            loc = s.get('location', '00') or '00'
            country = s.get('country_code') or s.get('country') or '?'
            name = s.get('name', code)
            print(f"      {net}.{code:6s}  {name}")
            print(f"        Position: {lat:.3f}, {lon:.3f} ({country})")
            print(f"        Location code: {loc}")
            print()

    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Choose stations from above list")
    print("2. Edit: sispro-tews/controller_module/data/station_indonesia.csv")
    print("3. Commit & push to GitHub")
    print("4. Restart controller (auto-seed chosen stations)")
    print()

if __name__ == '__main__':
    main()
