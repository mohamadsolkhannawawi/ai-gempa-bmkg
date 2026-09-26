
from datetime import datetime, timedelta
import os

def get_gmt_7_time(time):
    # Parse the string to a datetime object
    time_obj = datetime.strptime(time, "%H:%M:%S")

    # Add 7 hours
    new_time_obj = time_obj + timedelta(hours=7)

    # Format back to a string if needed
    new_time = new_time_obj.strftime("%H:%M:%S")

    return new_time

def check_and_make_existing_path(path):
    if os.path.exists(path) == False:
        os.mkdir(path)