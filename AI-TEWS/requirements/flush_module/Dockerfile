# Use the official ROCm image
FROM python:3.10-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY ./requirements.txt /app/requirements.txt

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir --progress-bar off -r requirements.txt

COPY . .

# Run python when the container launches
CMD ["python", "-u", "flush_scheduler_app.py"]