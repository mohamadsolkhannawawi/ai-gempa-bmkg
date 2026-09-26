import asyncio
import uvicorn

from seedlink_scheduler_player import app as app_rocketry


class Server(uvicorn.Server):
    """Customized uvicorn.Server

    Uvicorn server overrides signals and we need to include
    Rocketry to the signals."""
    def handle_exit(self, sig: int, frame) -> None:
        app_rocketry.session.shut_down()
        return super().handle_exit(sig, frame)


async def app():
    "Run scheduler and the API"

    sched = asyncio.create_task(app_rocketry.serve())

    await asyncio.wait([sched, ])

if __name__ == "__main__":
    asyncio.run(app())