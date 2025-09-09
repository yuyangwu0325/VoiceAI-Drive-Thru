#!/bin/bash

# Build and integrate the frontend with the backend

# Navigate to the frontend directory
cd frontend

# Install dependencies
echo "Installing frontend dependencies..."
npm install

# Build the frontend
echo "Building frontend..."
npm run build

# Create the build directory in the main project if it doesn't exist
mkdir -p ../frontend/build

# Copy the build files to the main project
echo "Copying build files to frontend/build directory..."
cp -r build/* ../frontend/build/

echo "Frontend build complete!"
echo "You can now run the application with: python run.py agent.py"
