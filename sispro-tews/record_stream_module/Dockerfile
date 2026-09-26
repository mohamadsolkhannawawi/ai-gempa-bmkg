# docker file
FROM python:3.10-slim-bullseye

# set the working directory in the container
WORKDIR /app

# Disable OpenBLAS threading to avoid pthread_create failures in nested containers
ENV OPENBLAS_NUM_THREADS=1
# Use non-interactive matplotlib backend to avoid thread creation in FontManager
ENV MPLBACKEND=Agg

# copy the dependencies file to the working directory
COPY ./requirement.txt /app/requirement.txt

# install dependencies
RUN pip install -r requirement.txt --progress-bar off

COPY . .

# command to run on container start
CMD [ "python", "record_stream_api_app.py" ]