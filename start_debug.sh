#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the application with verbose logging
python run.py agent.py --verbose > debug.log 2>&1
