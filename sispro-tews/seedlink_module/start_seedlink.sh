#!/bin/bash
# Kill seedlink app
pkill -f -9 seedlink_scheduler_app.py

# Define the script directory
SCRIPT_DIR="/app/"

# Change to the script directory
cd $SCRIPT_DIR || { echo "Failed to change directory to $SCRIPT_DIR"; exit 1; }

# Run the Python script in the background
/usr/local/bin/python -u seedlink_scheduler_app.py &

# Optional: Add a message indicating the script has started
echo "seedlink_scheduler_app.py has been started in the background."

# Deactivate the Anaconda environment if necessary
# conda deactivate
