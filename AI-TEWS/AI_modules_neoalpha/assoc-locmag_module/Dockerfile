# Use the official Tensorflow image
# FROM pytorch/pytorch:2.4.1-cuda12.4-cudnn9-runtime
# FROM rocm/dev-ubuntu-22.04

# TODO: Temporary because of server limitations, define a good base image here 
FROM python:3.10-slim
RUN pip install --no-cache-dir torch==2.4.1 --default-timeout=300

# Set the working directory in the container
WORKDIR /app

# Copy skydrifter_file from parent dir to working dir
# Separates big file copy for faster deployment while dev
COPY ./skydrifter_file /app/skydrifter_file

# Copy and install requirements (separated from dir copy to prevent multiple install on code changes)
COPY ./assoc-locmag_module/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt --default-timeout=300

# Copy the current directory contents into the container at /app
COPY ./assoc-locmag_module/ .

# Run python when the container launches
CMD ["python3", "-u", "assoc-locmag_consumer.py"]