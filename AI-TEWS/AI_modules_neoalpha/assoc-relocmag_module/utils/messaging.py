import json
import pymongo
from obspy import UTCDateTime
from config import *
from bson import ObjectId
from datetime import datetime
from typing import Tuple, List, Dict, Any

# Function to serialize data to JSON format
def json_serializer(message):
    if type(message)==type({}):
        return message
    elif type(message) == str:
        return json.loads(message)
    return json.loads(message.value.decode('utf-8'))

def send_magnitudes_to_db(
    magnitudes: List[Dict[str, Any]], 
    user_id: str, 
    created_at: datetime, 
    magnitude_col: pymongo.collection.Collection, 
    modified_at: datetime = None
) -> List[ObjectId]:
    """
    Inserts magnitude data into the database and returns the inserted IDs.
    
    Parameters
    ----------
    magnitudes : list
        A list of dictionaries, each containing magnitude data.
    user_id : str
        The ID of the user who modified the magnitude data.
    created_at : datetime
        The timestamp when the data is created.
    magnitude_col : pymongo.collection.Collection
        The collection for magnitude data in the database.
    modified_at : datetime, optional
        The timestamp when the data is modified.

    Returns
    -------
    List[ObjectId]
        The IDs of the inserted magnitude data.
    """
    # Insert magnitude data and returns the ids
    db_magnitudes_data = [
        {
            **magnitude,
            'modified_by': user_id,
            'created_at': created_at,
            'modified_at': modified_at
        }
        for magnitude in magnitudes
    ]
    
    return magnitude_col.insert_many(db_magnitudes_data).inserted_ids

# Function to insert station magnitude data into the database and return the inserted IDs
def send_station_magnitudes_to_db(
    station_magnitudes_per_type: List[Dict[str, Any]], 
    user_id: str, 
    created_at: datetime, 
    station_magnitude_col: pymongo.collection.Collection, 
    modified_at: datetime = None
) -> List[Dict[str, Any]]:
    """
    Inserts station magnitude data into the database and returns the inserted IDs per type.
    
    Parameters
    ----------
    station_magnitudes_per_type : List[Dict[str, Any]]
        A list of dictionaries, each containing the station magnitude data for a specific type.
    user_id : str
        The ID of the user who modified the station magnitude data.
    created_at : datetime
        The timestamp when the data is created.
    station_magnitude_col : pymongo.collection.Collection
        The collection for station magnitude data in the database.
    modified_at : datetime, optional
        The timestamp when the data is modified.

    Returns
    -------
    List[Dict[str, Any]]
        A list of dictionaries, each containing the type and corresponding station magnitude IDs.
    """
    # Initialize an empty list to store station magnitude data per type
    db_station_magnitudes_ids_per_type = []
    
    # Iterate over each type of station magnitude data
    for station_magnitudes in station_magnitudes_per_type:
        # Add station magnitude modifier and creation time
        db_station_magnitudes_data = [
            {
                **station_magnitude,
                'modified_by': user_id,
                'created_at': created_at,
                'modified_at': modified_at
            }
            for station_magnitude in station_magnitudes['station_magnitudes']
        ]

        # Insert the station magnitude data into the database and get the inserted IDs
        db_station_magnitudes_ids = station_magnitude_col.insert_many(db_station_magnitudes_data).inserted_ids
        
        # Append the type and corresponding station magnitude IDs to the list
        db_station_magnitudes_ids_per_type.append({
            'type': station_magnitudes['type'],
            'station_magnitude_ids': db_station_magnitudes_ids
        })        
    
    # Return the list of station magnitude data per type
    return db_station_magnitudes_ids_per_type