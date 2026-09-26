import asyncio
import uvicorn

from seedlink_scheduler_roy import main as app_rocketry


if __name__ == "__main__":
    asyncio.run(app_rocketry())