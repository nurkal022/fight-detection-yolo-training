#!/bin/bash

echo "=================================="
echo "Universal Detection System"
echo "=================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
mkdir -p app/logs
mkdir -p app/static/uploads
mkdir -p app/static/events
mkdir -p instance

# Run application
echo ""
echo "Starting application..."
echo "Access the web interface at: http://localhost:5001"
echo ""

python app/run.py


