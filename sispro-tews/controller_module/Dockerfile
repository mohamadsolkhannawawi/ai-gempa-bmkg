# docker file
FROM python:3.10-slim

# set the working directory in the container
WORKDIR /app

# copy the dependencies file to the working directory
COPY ./requirement.txt /app/requirement.txt

# install dependencies
RUN pip install -r requirement.txt --progress-bar off --default-timeout=100

COPY . .

# command to run on container start
CMD [ "python", "controller_api_app.py" ]