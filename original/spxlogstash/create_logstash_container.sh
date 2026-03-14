#!/bin/bash
docker remove -f spxlogstash
# Build the image
docker build -t spxlogstash .

mkdir -p /mnt/d/spxdata
touch /mnt/d/spxdata/.sincedb
chmod 777 /mnt/d/spxdata/.sincedb
mkdir -p /mnt/d/trades
touch /mnt/d/trades/.sincedb
chmod 777 /mnt/d/trades/.sincedb

# Environment variables - replace these with your actual values
T3_LOGSTASH_PATH="/mnt/c/code/spx-options-data/spxlogstash/config"
T3_LOGSTASH_CONFIG_PATH="/mnt/c/code/spx-options-data/spxlogstash/logstash.yml"
ELASTICSEARCH_USER="elastic"
ELASTICSEARCH_PASSWORD="FBpMiseXxHvBXotfwYlo"

# Create elastic network if it doesn't exist
docker network inspect elastic >/dev/null 2>&1 || docker network create elastic

# Run the Logstash container
docker run -d \
  --name spxlogstash \
  --network elastic \
  -v "${T3_LOGSTASH_PATH}:/usr/share/logstash/pipeline" \
  -v "${T3_LOGSTASH_CONFIG_PATH}:/usr/share/logstash/config/logstash.yml" \
  -v "/mnt/d/spxdata:/data/spxdata" \
  -v "/mnt/d/trades:/data/trades" \
  -e "LL_ES_HOST=elastic01" \
  -e "ES_USER=${ELASTICSEARCH_USER}" \
  -e "ES_PASSWORD=${ELASTICSEARCH_PASSWORD}" \
  --restart always \
  docker.elastic.co/logstash/logstash:8.7.1 