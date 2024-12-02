#!/bin/bash

# Find the Sequin container ID
CONTAINER_ID=$(docker ps --filter "name=sequin" --format "{{.ID}}")

if [ -z "$CONTAINER_ID" ]; then
    echo "Error: Sequin container not found"
    exit 1
fi

# Execute remote IEx connection
docker exec -it $CONTAINER_ID /bin/bash -c "./prod/rel/sequin/bin/sequin remote" 