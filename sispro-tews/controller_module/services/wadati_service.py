
from repositories.wadati_repository import get_wadati_data_repo
from utils.util import get_response
import dateutil.parser
from passlib.context import CryptContext
from datetime import datetime, timedelta

from jose import jwt, JWTError
from bson import ObjectId, json_util
from datetime import datetime, timedelta
import json

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
import dateutil.parser
import io
import base64
# run the following on terminal to generate a secret key
# openssl rand -hex 32
SECRET_KEY = "3e8a3f31aab886f8793176988f8298c9265f84b8388c9fef93635b08951f379b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_station_colors(num_stations):
    """
    This function is used to give different color for every station
    """
    return plt.cm.Spectral(np.linspace(0, 1, num_stations))

def plot_wadati(data):
    """
    This function is used to plot wadati diagram using a datetime of Arrival of P wave versus Differential between Arrival S-wave and P-Wave
    """
    try:
        for i in range(len(data)):
            data[i] = data[i].split()

        Ppha = []
        Spha = []
        staP = []
        staS = []
        arrP = []
        arrS = []
        Ptime = []
        Stime = []
        i = 0
        while i < len(data):
            if len(data[i]) > 0 and data[i][4] == 'P':
                staP.append(data[i][0])
                Ppha.append(data[i][4])
                arrP.append(f"{data[i][6][0:4]}-{data[i][6][4:6]}-{data[i][6][6:8]}T{data[i][7][0:2]}:{data[i][7][2:4]}:{data[i][8]}")
            elif len(data[i]) > 0 and data[i][4] == 'S':
                staS.append(data[i][0])
                Spha.append(data[i][4])
                arrS.append(f"{data[i][6][0:4]}-{data[i][6][4:6]}-{data[i][6][6:8]}T{data[i][7][0:2]}:{data[i][7][2:4]}:{data[i][8]}")
            i += 1

        # Sort P and S arrivals
        sorted_indices = np.argsort(arrP)
        staP_sorted = np.array(staP)[sorted_indices]
        arrP_sorted = np.array(arrP)[sorted_indices]

        sorted_indices = np.argsort(arrS)
        staS_sorted = np.array(staS)[sorted_indices]
        arrS_sorted = np.array(arrS)[sorted_indices]

        # Find stations with both P and S arrivals
        common_stations = np.intersect1d(staP_sorted, staS_sorted)

        for i, station in enumerate(common_stations):
            p_index = np.where(staP_sorted == station)[0][0]
            s_index = np.where(staS_sorted == station)[0][0]
            Ptime_diff = (datetime.strptime(arrP_sorted[p_index], '%Y-%m-%dT%H:%M:%S.%f') - datetime.strptime(arrP_sorted[0], '%Y-%m-%dT%H:%M:%S.%f')).total_seconds()
            Stime_diff = (datetime.strptime(arrS_sorted[s_index], '%Y-%m-%dT%H:%M:%S.%f') - datetime.strptime(arrP_sorted[p_index], '%Y-%m-%dT%H:%M:%S.%f')).total_seconds()
            Ptime.append(Ptime_diff)
            Stime.append(Stime_diff)

        x = np.array(Ptime)
        y = np.array(Stime)
        m, c = np.polyfit(x, y, 1)
        xideal = [0, max(x)]
        yideal = [c, max(x) * 0.73 + c]

        ratio = m + 1
        plt.figure(figsize=(10, 6))
        # Convert x axis to datetime
        x_datetime = [datetime.strptime(arrP_sorted[0], '%Y-%m-%dT%H:%M:%S.%f') + timedelta(seconds=val) for val in x]
        x_ideal_datetime = [datetime.strptime(arrP_sorted[0], '%Y-%m-%dT%H:%M:%S.%f') + timedelta(seconds=val) for val in xideal]
        colors = create_station_colors(len(common_stations))
        plt.scatter(x_datetime, y, c=colors, label="Station Data")
        plt.plot(x_datetime, m * x + c, label=f"Best Fit Line (Slope={m:.4f})", color="blue")
        plt.plot(x_ideal_datetime, yideal, linewidth=10, alpha=0.2, label="Ideal Vp/Vs Line", color="gray")
        plt.title(f"Wadati Diagram\nVp/Vs ratio: {ratio:.4f}")
        plt.xlabel('P arrival time')
        plt.ylabel('S-P arrival time')
        for i, sta in enumerate(common_stations):
            plt.text(x_datetime[i], y[i], sta, color='black', fontsize=9, alpha=0.7)

        plt.legend()
        plt.grid()
        

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        # plt.show()

    
        return image_base64
    except Exception as e:
        print(f"Error: {e}")
def wadati_plot_service(db, origin_id, current_user):
    try:

        wadati_data = get_wadati_data_repo(db, origin_id)
        
        result_dict = json.loads(json.dumps(wadati_data, default=json_util.default))
        
        datas = []
        for arrival_data in result_dict[0]["arrivals"]:
            # date_str = arrival_data["timestamp"]['$date']
            # date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            # formatted_date = date_obj.strftime('%Y%m%d %H%M %S.%f')[:-3]

            if arrival_data["checked"] == False:
                continue
            timestamp = arrival_data["timestamp"]
            if isinstance(timestamp, dict) and '$date' in timestamp:
                # For the MongoDB style `{'$date': '2024-12-03T18:29:08.790Z'}` 
                iso_string = timestamp['$date']
            elif isinstance(timestamp, str):
                # Directly handle if timestamp is an ISO formatted string
                iso_string = timestamp
            else:
                # Invalid format, handle error case
                raise ValueError("Unsupported timestamp format")

            # Parse the string into a datetime object using dateutil.parser
            dt = dateutil.parser.isoparse(iso_string)

            # Format the output as YYYYMMDD HHMM SS.SSS
            formatted_timestamp = f"{dt.strftime('%Y%m%d')} {dt.strftime('%H%M')} {dt.strftime('%S.%f')[:-3]}"


            
            data_to_append = arrival_data["station"]["code"]+" ? "+arrival_data["station"]["channel"][0]+" e "+arrival_data["phase_type"]+" c "+formatted_timestamp+" GAU 0.0 0.0 0.0 0.0"
            datas.append(data_to_append)
            
        image_base64 = plot_wadati(datas)
        
        wadati_data = {
            "image": image_base64,
        }
        return get_response(True, "get wadati plot successfully", wadati_data)
    except Exception as e:
        return get_response(False, "get wadati plot failed", str(e))
        

