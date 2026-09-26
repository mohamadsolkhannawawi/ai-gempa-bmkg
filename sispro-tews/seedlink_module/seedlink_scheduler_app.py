import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['MPLBACKEND'] = 'Agg'

import asyncio
import uvicorn

from seedlink_scheduler_roy import main as app_rocketry


if __name__ == "__main__":
    asyncio.run(app_rocketry())