# Use the official ROCm image
FROM python:3.10-slim-bullseye
# FROM rocm/dev-ubuntu-22.04

# Set the working directory in the container
WORKDIR /app

# Install python
# RUN apt-get update && \
#     apt-get install -y python3 python3-pip

# Copy and install requirements (separated from dir copy to prevent multiple install on code changes)
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
# Separates big file copy for faster deployment while dev
COPY . .

# Run python when the container launches
CMD ["python3", "-u", "assoc-locmag_consumer.py"]