# Use the official Tensorflow image
# FROM tensorflow/tensorflow:2.10.0-gpu
# FROM rocm/dev-ubuntu-22.04

# TODO: Temporary because of server limitations, define a good base image here 
FROM python:3.10-slim-bullseye
RUN pip install --no-cache-dir torch==2.4.1

# Set the working directory in the container
WORKDIR /app

# Copy skydrifter_file from parent dir to working dir
# Separates big file copy for faster deployment while dev
COPY ./skydrifter_file /app/skydrifter_file

# Copy and install requirements (separated from dir copy to prevent multiple install on code changes)
COPY ./assoc-relocmag_module/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY ./assoc-relocmag_module .

# Run terminal
CMD ["python3", "-u", "assoc-relocmag_consumer.py"]