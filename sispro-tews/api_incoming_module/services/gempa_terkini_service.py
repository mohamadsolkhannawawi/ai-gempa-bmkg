from repositories.gempa_terkini_repo import get_gempa_terkini_repo
import xml.etree.ElementTree as ET
from utils.util import get_response
from datetime import datetime, timezone, timedelta
import pandas as pd
def get_gempa_terkini_service(db, format):

    arrival_datas = get_gempa_terkini_repo(db)
    gempa_list = []
    for arrival_data in arrival_datas:
        
        utc_time_str =  str(arrival_data["origin_data"]["origin_time"])
        utc_time = datetime.fromisoformat(utc_time_str).replace(tzinfo=timezone.utc)
        gmt7_time = utc_time + timedelta(hours=7)
        gmt7_time_str = gmt7_time.strftime("%Y-%m-%d %H:%M:%S")
        gempa ={
            "Tanggal": str(gmt7_time_str).split(" ")[0],
            "Jam":  str(gmt7_time_str).split(" ")[1] +" WIB",
            "DateTime": arrival_data["origin_data"]["origin_time"],
            "Coordinates":  str(arrival_data["origin_data"]["latitude"])+","+str(arrival_data["origin_data"]["longitude"]),
            "Lintang": str(abs(arrival_data["origin_data"]["latitude"]))+' LS' if arrival_data["origin_data"]["latitude"] < 0 else str(abs(arrival_data["origin_data"]["latitude"]))+' LU',
            "Bujur": str(abs(arrival_data["origin_data"]["longitude"]))+' BB' if arrival_data["origin_data"]["longitude"] < 0 else str(arrival_data["origin_data"]["longitude"]) +' BT',
            "Magnitude": str(round(arrival_data["magnitude_data"]["value"],1)),
            "Kedalaman": str(int(arrival_data["origin_data"]["depth"]))+" km",
        } 
        gempa_list.append(gempa)
    

    # # gmt7_time = gmt7_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    if format == 'json':
        custom_response = {
            "Infogempa":{
                "gempa":gempa_list
            }
        }
    elif format == 'xml':
        df = pd.DataFrame(gempa_list, columns=["Tanggal", "Jam", "DateTime", 'Coordinates', 'Lintang', 'Bujur', 'Magnitude', 'Kedalaman'])
        root = ET.Element("Infogempa")

        # Looping DataFrame dan memasukkan data ke XML
        for _, row in df.iterrows():
            gempa = ET.SubElement(root, "gempa")
            
            ET.SubElement(gempa, "Tanggal").text = row["Tanggal"]
            ET.SubElement(gempa, "Jam").text = row["Jam"]
            ET.SubElement(gempa, "DateTime").text = str(row["DateTime"])
            
            # Menambahkan Coordinates dalam <point>
            point = ET.SubElement(gempa, "point")
            ET.SubElement(point, "Coordinates").text = row["Coordinates"]
            
            ET.SubElement(gempa, "Lintang").text = row["Lintang"]
            ET.SubElement(gempa, "Bujur").text = row["Bujur"]
            ET.SubElement(gempa, "Magnitude").text = str(row["Magnitude"])
            ET.SubElement(gempa, "Kedalaman").text = row["Kedalaman"]

        # Mengubah objek XML menjadi string
        custom_response = ET.tostring(root, encoding="utf-8").decode()

        # Step 3: Convert DataFrame to XML string
        # custom_response = df.to_xml(root_name="Infogempa", row_name="gempa").replace("\n", "").strip()
       

    if arrival_data != None:
        return custom_response

    return get_response(False, "cannot get arrival detail", None)