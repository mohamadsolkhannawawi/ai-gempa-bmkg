#!/bin/bash

# Put all env to be accessible by cron
printenv >> /etc/environment

# Start cron in the background
service cron start

# Run the start_archiving.sh script and log output
/app/start_archiving.sh >> /app/logs/archiving.log 2>&1 &

# Tail the log file to keep the container running
tail -f /app/logs/archiving.log