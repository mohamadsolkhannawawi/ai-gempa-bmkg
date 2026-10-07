from obspy.clients.seedlink import Client

SERVER = "geofon.gfz-potsdam.de"
PORT = 18000

client = Client(SERVER, PORT, timeout=30)

# Get STATION list langsung
print("Testing get_info('STATIONS')...")
stations_info = client.get_info('STATIONS')
print(f"Type: {type(stations_info)}")
print(f"Content: {stations_info[:1000] if stations_info else 'empty'}")

print("\n" + "="*60)
print("Testing get_info('STREAMS')...")
streams_info = client.get_info('STREAMS')
print(f"Type: {type(streams_info)}")
print(f"Content: {streams_info[:1000] if streams_info else 'empty'}")

print("\n" + "="*60)
print("Testing get_info('NETWORK')...")
network_info = client.get_info('NETWORK')
print(f"Type: {type(network_info)}")
print(f"Content (first 2000 chars):")
if network_info:
    if isinstance(network_info, list):
        print('\n'.join(network_info[:10]))
    else:
        print(network_info[:2000])
