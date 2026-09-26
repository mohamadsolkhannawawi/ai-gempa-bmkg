from repositories.auto_gempa_repo import get_auto_gempa_repo
import xml.etree.ElementTree as ET
from utils.util import get_response
from datetime import datetime, timezone, timedelta

def get_auto_gempa_service(db, format):

    arrival_data = get_auto_gempa_repo(db)
    utc_time_str =  str(arrival_data["origin_data"]["origin_time"])
    utc_time = datetime.fromisoformat(utc_time_str).replace(tzinfo=timezone.utc)
    gmt7_time = utc_time + timedelta(hours=7)
    gmt7_time_str = gmt7_time.strftime("%Y-%m-%d %H:%M:%S")

    # gmt7_time = gmt7_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    if format == 'json':
        custom_response = {
            "Infogempa":{
                "gempa":{
                    "Tanggal": str(gmt7_time_str).split(" ")[0],
                    "Jam":  str(gmt7_time_str).split(" ")[1] +" WIB",
                    "DateTime": arrival_data["origin_data"]["origin_time"],
                    "Coordinates":  str(arrival_data["origin_data"]["latitude"])+","+str(arrival_data["origin_data"]["longitude"]),
                    "Lintang": str(abs(arrival_data["origin_data"]["latitude"]))+' LS' if arrival_data["origin_data"]["latitude"] < 0 else str(abs(arrival_data["origin_data"]["latitude"]))+' LU',
                    "Bujur": str(abs(arrival_data["origin_data"]["longitude"]))+' BB' if arrival_data["origin_data"]["longitude"] < 0 else str(abs(arrival_data["origin_data"]["longitude"])) +' BT',
                    "Magnitude": str(round(arrival_data["origin_data"]["magnitudes"][0]["value"],1)),
                    "Kedalaman": str(int(arrival_data["origin_data"]["depth"]))+" km",
                    # "Wilayah": "Pusat gempa berada di laut 96 km barat daya Gunung Kidul",
                    # "Potensi": "Gempa ini dirasakan untuk diteruskan pada masyarakat",
                    # "Dirasakan": "III Gunungkidul, III Bantul, III Kulon Progo, III Yogyakarta, III Sleman, III Kebumen, III Purworejo, II Klaten, II Pacitan, II Trenggalek, II Karangkates",
                    # "Shakemap": "20250201074014.mmi.jpg"
                }
            }
        }
    elif format == 'xml':
        infogempa = ET.Element("Infogempa")
        gempa = ET.SubElement(infogempa, "gempa")

        ET.SubElement(gempa, "Tanggal").text = str(gmt7_time_str).split(" ")[0]
        ET.SubElement(gempa, "Jam").text = str(gmt7_time_str).split(" ")[1] +" WIB"
        ET.SubElement(gempa, "DateTime").text = str(arrival_data["origin_data"]["origin_time"]).replace(" ", "T")

        point = ET.SubElement(gempa, "point")
        ET.SubElement(point, "coordinates").text = f"{arrival_data['origin_data']['latitude']},{arrival_data['origin_data']['longitude']}"

        ET.SubElement(gempa, "Lintang").text = f"{abs(arrival_data['origin_data']['latitude'])} LS" if arrival_data["origin_data"]["latitude"] < 0 else f"{arrival_data['origin_data']['latitude']} LU"
        ET.SubElement(gempa, "Bujur").text = f"{abs(arrival_data['origin_data']['longitude'])} BT" if arrival_data["origin_data"]["longitude"] > 0 else f"{arrival_data['origin_data']['longitude']} BB"
        ET.SubElement(gempa, "Magnitude").text = str(round(arrival_data["origin_data"]["magnitudes"][0]["value"], 1))
        ET.SubElement(gempa, "Kedalaman").text = f"{int(arrival_data['origin_data']['depth'])} km"
        # ET.SubElement(gempa, "Wilayah").text = "Pusat gempa berada di laut 96 km barat daya Gunung Kidul"
        # ET.SubElement(gempa, "Potensi").text = "Gempa ini dirasakan untuk diteruskan pada masyarakat"
        # ET.SubElement(gempa, "Dirasakan").text = "III Gunungkidul, III Bantul, III Kulon Progo, III Yogyakarta, III Sleman, III Kebumen, III Purworejo, II Klaten, II Pacitan, II Trenggalek, II Karangkates"
        # ET.SubElement(gempa, "Shakemap").text = "20250201074014.mmi.jpg"

        # Mengubah ke format string XML
        custom_response = ET.tostring(infogempa, encoding="unicode")

    if arrival_data != None:
        return custom_response

    return get_response(False, "cannot get arrival detail", None)