# Use the official ROCm image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy and install requirements (separated from dir copy to prevent multiple install on code changes)
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt --default-timeout=100

# Copy the current directory contents into the container at /app
COPY . .

# Run python when the container launches
CMD ["python", "-u", "pick-arrival_consumer.py"]