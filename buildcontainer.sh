docker remove -f spx_collector
# Build the image
docker build -t spx_collector .

mkdir -p /data/web_log_upload/trades
touch /data/web_log_upload/trades/.sincedb
chmod 777 /data/web_log_upload/trades/.sincedb
mkdir -p /data/web_log_upload/spxdata
touch /data/web_log_upload/spxdata/.sincedb
chmod 777 /data/web_log_upload/spxdata/.sincedb
# Run the container with mounts and specify the script to run
docker run -d \
  --name spx_collector \
  --restart unless-stopped \
  --network elastic \
  -v /mnt/c/code/spx-options-data:/app \
  -v /data/web_log_upload/spxdata:/data/spxdata \
  spx_collector \
  python "/app/fetch_xDTE_prices_with_IB_calculations_V2.py" --symbol SPX --dte_days 7 --output_dir /data/spxdata --check_market_hours