# docker file
FROM python:3.10-slim

# set the working directory in the container
WORKDIR /app

# Disable OpenBLAS threading to avoid pthread_create failures in nested containers
ENV OPENBLAS_NUM_THREADS=1
# Use non-interactive matplotlib backend to avoid thread creation in FontManager
ENV MPLBACKEND=Agg

# copy the dependencies file to the working directory
COPY ./requirement.txt /app/requirement.txt

# install dependencies
RUN pip install -r requirement.txt --progress-bar off --default-timeout=100

COPY . .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Health check (runs during build, not runtime - use container healthcheck below)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import pymongo; pymongo.MongoClient('mongodb://mongodb:27017/').admin.command('ping')" || exit 1

# command to run on container start (use entrypoint instead of direct python)
ENTRYPOINT ["/app/entrypoint.sh"]
