#!/bin/bash

cd "$(dirname "$0")/myapp/deploy"

# Build Docker Images in Order
for file in debian.base.Dockerfile 1-service.Dockerfile 2-service.Dockerfile 3-service.Dockerfile 4-service.Dockerfile 6-service.Dockerfile; do
    count=0
    while [ $count -lt 2 ]; do
        docker build --no-cache -t ${file%.*}:latest -f $file .
        if [ $? -eq 0 ]; then
            count=0
            break
        else
            echo "Docker build failed for $file, retrying..."
            let count++
        fi
    done
    if [ $count -ge 2 ]; then
        echo "Docker build failed for $file twice, aborting."
        exit 1
    fi
done

# Change directory to run docker-compose
cd ..
docker-compose up --build
