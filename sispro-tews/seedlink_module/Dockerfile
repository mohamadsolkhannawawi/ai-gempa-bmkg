FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY ./requirement.txt /app/requirement.txt

# Install dependencies
RUN pip install -r requirement.txt --progress-bar off

# Prepare cronjob
RUN apt-get update && \
    apt-get install -y cron procps nano && \
    touch /etc/crontab /etc/cron.*/*

COPY --chmod=0644 ./crontab /etc/cron.d/crontab

# Apply crontab
RUN crontab /etc/cron.d/crontab

# Copy other files
COPY . .

# Add chmod and mkdir logs
RUN chmod +x /app/start_seedlink.sh && \
    mkdir -p /app/logs/ && \
    mkdir -p /app/data/ && \
    touch /app/logs/seedlink.log

# Create an entrypoint script
COPY --chmod=0755 entrypoint.sh /app/entrypoint.sh

# Command to run on container start
ENTRYPOINT ["/app/entrypoint.sh"]
