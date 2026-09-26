from obspy import read_inventory
from obspy.core.utcdatetime import UTCDateTime
import cmath
import json

def query_inventory(file_path, starttime=None, endtime=None, startbefore=None, startafter=None,
                    endbefore=None, endafter=None, network=None, station=None, location=None,
                    channel=None, minlatitude=None, maxlatitude=None, minlongitude=None,
                    maxlongitude=None, latitude=None, longitude=None, minradius=None,
                    maxradius=None, level="response", includerestricted=False,
                    includeavailability=False, updatedafter=None, matchtimeseries=False,
                    format="xml", nodata=204):
    """
    Query inventory based on the provided parameters and return details up to the Response level.
    
    Parameters:
    - file_path (str): Path to the inventory file (e.g., 'stations.xml').
    - starttime, endtime, etc.: Filters as described in the table.
    
    Returns:
    - Filtered inventory object.
    """
    # Load the inventory with the desired level
    inv = read_inventory(file_path, level=level)

    # Apply filters based on the input parameters
    if network:
        inv = inv.select(network=network)
    if station:
        inv = inv.select(station=station)
    if location:
        inv = inv.select(location=location)
    if channel:
        inv = inv.select(channel=channel)
    
    if minlatitude != None:
        minlatitude= int(minlatitude)
    
    if maxlatitude != None:
        maxlatitude= int(maxlatitude)
    
    if minlongitude != None:
        minlongitude= int(minlongitude)
        
    if maxlongitude != None:
        maxlongitude= int(maxlongitude)
    
    if latitude != None:
        latitude= int(latitude)
        
    if longitude != None:
        longitude= int(longitude)
    
    if minradius != None:
        minradius= int(minradius)
    
    if maxradius != None:
        maxradius= int(maxradius)
        
    # Apply geographic filters
    inv = inv.select(
        minlatitude=minlatitude,
        maxlatitude=maxlatitude,
        minlongitude=minlongitude,
        maxlongitude=maxlongitude,
        latitude=latitude,
        longitude=longitude,
        minradius=minradius,
        maxradius=maxradius
    )
    
    # Apply time filters
    if starttime or endtime:
        inv = inv.select(
            starttime=UTCDateTime(starttime) if starttime else None,
            endtime=UTCDateTime(endtime) if endtime else None
        )
    
    return inv
import json
import cmath

def export_inventory_details(inventory, format="text"):
    """
    Export detailed information of the inventory in a structured and readable format,
    including all Response details, based on the specified format.

    Parameters:
    - inventory: Filtered inventory object from query_inventory.
    - format (str): Format to return the data, can be 'text', 'xml', or 'json'.

    Returns:
    - str: Inventory details in the specified format.
    """
    # Generate the structured representation first
    inventory_details = []

    for network in inventory:
        network_info = {
            "network_code": network.code,
            "description": network.description,
            "stations": []
        }

        for station in network:
            station_info = {
                "station_code": station.code,
                "site_name": station.site.name,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "elevation": station.elevation,
                "channels": []
            }

            for channel in station:
                channel_info = {
                    "channel_code": channel.code,
                    "location_code": channel.location_code,
                    "latitude": channel.latitude,
                    "longitude": channel.longitude,
                    "elevation": channel.elevation,
                    "azimuth": channel.azimuth,
                    "dip": channel.dip,
                    "sample_rate": channel.sample_rate,
                    "response": None
                }

                if channel.response:
                    response = channel.response
                    response_info = {
                        "instrument_sensitivity": {
                            "gain": response.instrument_sensitivity.value,
                            "frequency": response.instrument_sensitivity.frequency
                        },
                        "response_stages": []
                    }

                    for i, stage in enumerate(response.response_stages, start=1):
                        stage_info = {
                            "stage_number": i,
                            "stage_gain": stage.stage_gain,
                            "stage_gain_frequency": stage.stage_gain_frequency,
                            "input_units": stage.input_units,
                            "output_units": stage.output_units,
                            "decimation": {
                                "input_sample_rate": stage.decimation_input_sample_rate,
                                "factor": stage.decimation_factor,
                                "delay": stage.decimation_delay,
                                "correction": stage.decimation_correction
                            },
                            "poles": [
                                {
                                    "real": pole.real,
                                    "imag": pole.imag,
                                    "abs": abs(complex(pole.real, pole.imag)),
                                    "phase": cmath.phase(complex(pole.real, pole.imag))
                                }
                                for pole in getattr(stage, 'poles', []) if stage.poles
                            ],
                            "zeros": [
                                {
                                    "real": zero.real,
                                    "imag": zero.imag,
                                    "abs": abs(complex(zero.real, zero.imag)),
                                    "phase": cmath.phase(complex(zero.real, zero.imag))
                                }
                                for zero in getattr(stage, 'zeros', []) if stage.zeros
                            ]
                        }
                        response_info["response_stages"].append(stage_info)
                    channel_info["response"] = response_info

                station_info["channels"].append(channel_info)

            network_info["stations"].append(station_info)

        inventory_details.append(network_info)

    # Convert the structured representation to the requested format
    if format == "text":
        return json.dumps(inventory_details, indent=4)
    elif format == "json":
        response = {
            "success": True,
            "message": "get station success",
            "data": inventory_details
        }
        return response

    elif format == "xml":
        # Convert structured representation to XML
        xml_output = ["<InventoryDetails>"]
        for network in inventory_details:
            xml_output.append(f"  <Network code=\"{network['network_code']}\">")
            xml_output.append(f"    <Description>{network['description']}</Description>")
            for station in network['stations']:
                xml_output.append(f"    <Station code=\"{station['station_code']}\">")
                xml_output.append(f"      <SiteName>{station['site_name']}</SiteName>")
                xml_output.append(f"      <Latitude>{station['latitude']}</Latitude>")
                xml_output.append(f"      <Longitude>{station['longitude']}</Longitude>")
                xml_output.append(f"      <Elevation>{station['elevation']}</Elevation>")
                for channel in station['channels']:
                    xml_output.append(f"      <Channel code=\"{channel['channel_code']}\" location=\"{channel['location_code']}\">")
                    xml_output.append(f"        <Latitude>{channel['latitude']}</Latitude>")
                    xml_output.append(f"        <Longitude>{channel['longitude']}</Longitude>")
                    xml_output.append(f"        <Elevation>{channel['elevation']}</Elevation>")
                    xml_output.append(f"        <Azimuth>{channel['azimuth']}</Azimuth>")
                    xml_output.append(f"        <Dip>{channel['dip']}</Dip>")
                    xml_output.append(f"        <SampleRate>{channel['sample_rate']}</SampleRate>")
                    if channel['response']:
                        response = channel['response']
                        xml_output.append(f"        <Response>")
                        xml_output.append(f"          <InstrumentSensitivity>")
                        xml_output.append(f"            <Gain>{response['instrument_sensitivity']['gain']}</Gain>")
                        xml_output.append(f"            <Frequency>{response['instrument_sensitivity']['frequency']}</Frequency>")
                        xml_output.append(f"          </InstrumentSensitivity>")
                        for stage in response['response_stages']:
                            xml_output.append(f"          <Stage number=\"{stage['stage_number']}\">")
                            xml_output.append(f"            <StageGain>{stage['stage_gain']}</StageGain>")
                            xml_output.append(f"            <StageGainFrequency>{stage['stage_gain_frequency']}</StageGainFrequency>")
                            xml_output.append(f"            <InputUnits>{stage['input_units']}</InputUnits>")
                            xml_output.append(f"            <OutputUnits>{stage['output_units']}</OutputUnits>")
                            xml_output.append(f"            <Decimation>")
                            xml_output.append(f"              <InputSampleRate>{stage['decimation']['input_sample_rate']}</InputSampleRate>")
                            xml_output.append(f"              <Factor>{stage['decimation']['factor']}</Factor>")
                            xml_output.append(f"              <Delay>{stage['decimation']['delay']}</Delay>")
                            xml_output.append(f"              <Correction>{stage['decimation']['correction']}</Correction>")
                            xml_output.append(f"            </Decimation>")
                            if stage['poles']:
                                xml_output.append(f"            <Poles>")
                                for pole in stage['poles']:
                                    xml_output.append(f"              <Pole>")
                                    xml_output.append(f"                <Real>{pole['real']}</Real>")
                                    xml_output.append(f"                <Imag>{pole['imag']}</Imag>")
                                    xml_output.append(f"                <Abs>{pole['abs']}</Abs>")
                                    xml_output.append(f"                <Phase>{pole['phase']}</Phase>")
                                    xml_output.append(f"              </Pole>")
                                xml_output.append(f"            </Poles>")
                            if stage['zeros']:
                                xml_output.append(f"            <Zeros>")
                                for zero in stage['zeros']:
                                    xml_output.append(f"              <Zero>")
                                    xml_output.append(f"                <Real>{zero['real']}</Real>")
                                    xml_output.append(f"                <Imag>{zero['imag']}</Imag>")
                                    xml_output.append(f"                <Abs>{zero['abs']}</Abs>")
                                    xml_output.append(f"                <Phase>{zero['phase']}</Phase>")
                                    xml_output.append(f"              </Zero>")
                                xml_output.append(f"            </Zeros>")
                            xml_output.append(f"          </Stage>")
                        xml_output.append(f"        </Response>")
                    xml_output.append(f"      </Channel>")
                xml_output.append(f"    </Station>")
            xml_output.append(f"  </Network>")
        xml_output.append("</InventoryDetails>")
        xml_response_output =  "".join(xml_output).strip()
        xml_response_output = xml_response_output.replace("\"", "")
        xml_response_output = xml_response_output.replace("\n", "")
        
        return xml_response_output
    else:
        raise ValueError("Invalid format. Supported formats are 'text', 'xml', or 'json'.")

# Example Usage
# filtered_inventory = query_inventory(
#     file_path="stations.xml",
#     starttime="2024-01-01",
#     endtime="2024-12-31",
#     network="IA",
#     station="AAFM",
#     channel="SHE",
#     minlatitude=-90.0,
#     maxlatitude=90.0,
#     minlongitude=-180.0,
#     maxlongitude=180.0,
#     level="response"
# )

# # Print structured and detailed information
# print_inventory_details(filtered_inventory)
