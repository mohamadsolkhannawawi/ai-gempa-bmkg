#!/bin/bash
# Kill fdsn app
pkill -f -9 fdsn_scheduler_app.py

# Define the script directory
SCRIPT_DIR="/workspace/sispro-tews/fdsn_module"

# Change to the script directory
cd $SCRIPT_DIR || { echo "Failed to change directory to $SCRIPT_DIR"; exit 1; }

# Run the Python script in the background
python3 fdsn_scheduler_app.py &

# Optional: Add a message indicating the script has started
echo "fdsn_scheduler_app.py has been started in the background."

# Deactivate the Anaconda environment if necessary
# conda deactivate
