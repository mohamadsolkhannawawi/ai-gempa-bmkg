FROM python:3.10-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY ./requirement.txt /app/requirement.txt

# Install dependencies
RUN pip install -r requirement.txt --progress-bar off

# Prepare cronjob (skip packages that are 404 in bullseye security repo)
RUN apt-get update && \
    (apt-get install -y procps || true) && \
    mkdir -p /etc/cron.d

# Copy other files
COPY . .

# Add chmod and mkdir logs
RUN chmod 644 ./crontab && \
    mkdir -p /etc/cron.d && \
    cp ./crontab /etc/cron.d/crontab && \
    chmod +x /app/start_archiving.sh && \
    mkdir -p /app/logs/ && \
    touch /app/logs/archiving.log || true

# Create an entrypoint script
COPY --chmod=0755 entrypoint.sh /app/entrypoint.sh

# Command to run on container start
ENTRYPOINT ["/app/entrypoint.sh"]
