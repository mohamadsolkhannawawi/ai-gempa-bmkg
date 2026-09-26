import asyncio
import uvicorn

from api_incoming_module import app as app_fastapi

class Server(uvicorn.Server):
    """Customized uvicorn.Server

    Uvicorn server overrides signals and we need to include
    Rocketry to the signals."""
    def handle_exit(self, sig: int, frame) -> None:
        return super().handle_exit(sig, frame)


async def app():
    "Run scheduler and the API"
    server = Server(config=uvicorn.Config(app_fastapi, 
                                          workers=32, 
                                          reload=True, 
                                          loop="asyncio", 
                                          host="0.0.0.0", 
                                          port = "8007"))

    api = asyncio.create_task(server.serve())

    await asyncio.wait([api])

if __name__ == "__main__":
    asyncio.run(app())