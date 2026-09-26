FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY ./requirement.txt /app/requirement.txt

# Install dependencies
RUN pip install -r requirement.txt --progress-bar off

# Install system utilities (skip cron due to apt errors)
RUN apt-get update 2>/dev/null || true && \
    apt-get install -y procps nano 2>/dev/null || true

# Copy other files
COPY . .

# Add chmod and mkdir logs
RUN chmod +x /app/start_seedlink.sh && \
    mkdir -p /app/logs/ && \
    mkdir -p /app/data/ && \
    touch /app/logs/seedlink.log

# Create an entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod 0755 /app/entrypoint.sh

# Command to run on container start
ENTRYPOINT ["/app/entrypoint.sh"]
