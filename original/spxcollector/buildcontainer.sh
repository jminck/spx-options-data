docker remove -f spxcollector
# Build the image
docker build -t spxcollector .

mkdir -p  /mnt/d/data/web_log_upload/trades
touch  /mnt/d/data/web_log_upload/trades/.sincedb
chmod 777  /mnt/d/data/web_log_upload/trades/.sincedb
mkdir -p  /mnt/d/data/web_log_upload/spxdata
touch  /mnt/d/data/web_log_upload/spxdata/.sincedb
chmod 777  /mnt/d/data/web_log_upload/spxdata/.sincedb
# Run the container with mounts and specify the script to run
docker run -d \
  --name spxcollector \
  --restart unless-stopped \
  --network elastic \
  -v /mnt/c/code/spx-options-data/spxcollector:/app \
  -v  /mnt/d/spxdata:/data/spxdata \
  spxcollector \
  python "/app/fetch_xDTE_prices_with_IB_calculations_V2.py" --symbol SPX --dte_days 7 --output_dir /data/spxdata --check_market_hours