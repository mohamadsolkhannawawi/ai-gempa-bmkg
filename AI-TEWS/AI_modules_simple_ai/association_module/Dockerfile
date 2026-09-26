# Use the official ROCm image
FROM rocm/dev-ubuntu-22.04

# Set the working directory in the container
WORKDIR /app

# Install python
RUN apt-get update 2>/dev/null || true && \
    apt-get install -y python3 python3-pip 2>/dev/null || true

# Copy and install requirements (separated from dir copy to prevent multiple install on code changes)
COPY ./requirements.txt /app/requirements.txt
RUN pip install --progress-bar off --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app

# Run python when the container launches
CMD ["python3", "-u", "association_consumer.py"]