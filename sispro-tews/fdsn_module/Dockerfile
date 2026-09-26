# docker file
FROM python:3.10-slim-bullseye

# set the working directory in the container
WORKDIR /app

# copy the dependencies file to the working directory
COPY ./requirement.txt /app/requirement.txt

# install dependencies
RUN pip install -r requirement.txt --progress-bar off

COPY . .

# command to run on container start
CMD [ "python", "fdsn_scheduler_app.py" ]