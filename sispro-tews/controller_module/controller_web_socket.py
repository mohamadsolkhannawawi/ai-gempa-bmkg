from fastapi import FastAPI, WebSocket
from dotenv import load_dotenv
from module_websockets.picking_websocket import picking_send_messages
from module_websockets.arrival_picking_websocket import arrival_pick_send_messages
from module_websockets.cluster_websocket import cluster_send_messages
from module_websockets.event_websocket import event_send_messages
from fastapi.middleware.cors import CORSMiddleware
import asyncio
# Load environment variables
load_dotenv()

app = FastAPI()
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/wspicking")
async def websocket_picking(websocket: WebSocket):
    await picking_send_messages(websocket)

@app.websocket("/wsarrivalpick")
async def websocket_arrival_pick(websocket: WebSocket):
    await arrival_pick_send_messages(websocket)

@app.websocket("/wscluster")
async def websocket_cluster(websocket: WebSocket):
    await cluster_send_messages(websocket)

@app.websocket("/wsevent")
async def websocket_event(websocket: WebSocket):
    await event_send_messages(websocket)

# Add this part if running the app directly with Uvicorn or another ASGI server
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8004)
