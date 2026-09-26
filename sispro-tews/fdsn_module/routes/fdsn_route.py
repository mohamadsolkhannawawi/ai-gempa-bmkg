from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from obspy import UTCDateTime
from obspy.clients.filesystem.sds import Client
from io import BytesIO

app = FastAPI()


from fastapi import APIRouter, Depends, status, Request, Form, UploadFile, File
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from services.fdsn_services import export_inventory_details
from services.fdsn_services import query_inventory


#exception and validation
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



origins = ["*"]

SECRET_KEY = "3e8a3f31aab886f8793176988f8298c9265f84b8388c9fef93635b08951f379b"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24


# Dummy database of users
fake_users_db = {
    "recordstreamtews": {
        "username": "recordstreamtews",
        "hashed_password": pwd_context.hash("recordstreamtews12#"),
    }
}


router = APIRouter(
    prefix ="/fdsnws"
)


# Serve static files for WADL documents
@router.get('/dataselect/1/application.wadl')
async def serve_dataselect_wadl():
    return FileResponse('static/dataselect/application.wadl')

@router.get('/event/1/application.wadl')
async def serve_event_wadl():
    return FileResponse('static/event/application.wadl')

@router.get('/station/1/application.wadl')
async def serve_station_wadl():
    return FileResponse('static/station/application.wadl')

@router.get('/dataselect/1/query')
async def query(starttime: str = Query(None), 
                endtime: str = Query(None), 
                network: str = Query(None), 
                station: str = Query(None), 
                location: str = Query(None), 
                channel: str = Query(None)):
    
    Client.FMTSTR= '{year}/{network}/{station}/{channel}.{sds_type}/{network}.{station}.{location}.{channel}.{sds_type}.{year}.{doy:03d}.mseed'
    client_sds = Client(sds_root="/archive")
    st = client_sds.get_waveforms(network=network, 
                                  station=station, 
                                  location=location.replace('--',''), 
                                  channel=channel, 
                                  starttime=UTCDateTime(starttime), 
                                  endtime=UTCDateTime(endtime))
    
    print(st)
    if len(st) == 0:
        # Return 204 No Content when no data is available
        return Response(status_code=204, content="No data available for request.")
    # Create an in-memory BytesIO object
    in_memory_file = BytesIO()

    # Write the ObsPy stream to the in-memory BytesIO object
    st.write(in_memory_file, format="MSEED")

    # Reset the position to the beginning of the BytesIO object
    in_memory_file.seek(0)
    
    # Use a StreamingResponse for efficient file serving
    # response = StreamingResponse(in_memory_file, media_type="application/octet-stream")
    # response.headers["Content-Disposition"] = "attachment; filename=fdsn.mseed"
    # return response
    return Response(content=in_memory_file.getvalue(), media_type='application/octet-stream', 
                    headers={"Content-Disposition": "attachment; filename=fdsn.mseed"})






@router.get('/station/1/query')
async def query(starttime: str = Query(None), 
                endtime: str = Query(None), 
                startbefore: str = Query(None), 
                startafter: str = Query(None), 
                endbefore: str = Query(None), 
                endafter: str = Query(None),
                network: str = Query(None),
                station : str = Query(None),
                location: str = Query(None),
                channel: str = Query(None),
                minlatitude : str = Query(None),
                maxlatitude : str = Query(None),
                minlongitude : str = Query(None),
                maxlongitude : str = Query(None),
                latitude : str = Query(None),
                longitude : str = Query(None),
                minradius: str = Query(None),
                maxradius : str = Query(None),
                level: str = Query(None),
                includerestricted: str = Query(None),
                includeavailability : str = Query(None),
                updatedafter: str = Query(None),
                matchtimeseries: str = Query(None),
                format:str = Query(None),
                nodata: str = Query(None)
    
            
            ):
    
                    
    filtered_inventory = query_inventory(
        file_path="./data/stations.xml",
        starttime = starttime,
        endtime = endtime,
        startbefore= startbefore,
        startafter = startafter,
        endbefore= endbefore,
        endafter= endafter,
        network= network,
        station = station,
        location = location,
        channel= channel,
        minlatitude = minlatitude,
        maxlatitude = maxlatitude,
        minlongitude = minlongitude,
        maxlongitude = maxlongitude,
        latitude = latitude,
        longitude = longitude,
        minradius = minradius,
        maxradius = maxradius,
        level = level,
        includerestricted = includerestricted,
        includeavailability = includeavailability,
        updatedafter = updatedafter,
        matchtimeseries = matchtimeseries,
        format = format,
        nodata = nodata
    )
    
    if format == "text":
        text_output = export_inventory_details(filtered_inventory, format="text")
        return text_output
    
    if format == "json":
        json_output = export_inventory_details(filtered_inventory, format="json")
        return json_output

    if format == "xml":
        xml_output = export_inventory_details(filtered_inventory, format="xml")
        return xml_output


