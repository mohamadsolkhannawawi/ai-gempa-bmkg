#!/bin/bash

# Put all env to be accessible by cron
printenv >> /etc/environment

# Start cron in the background
service cron start

# Run the start_seedlink.sh script and log output
/app/start_seedlink.sh >> /app/logs/seedlink.log 2>&1 &

# Tail the log file to keep the container running
tail -f /app/logs/seedlink.log