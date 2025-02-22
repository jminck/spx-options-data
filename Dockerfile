FROM python:3.9-slim

# Install cron and required packages
RUN apt-get update && apt-get install -y cron

# Install required packages
RUN pip install requests pandas pytz pandas_market_calendars

# Create directory for the mounted data
RUN mkdir -p /data/spxdata

# Create the cron job file
RUN echo "0 22 * * 1-5 cd /app && python fetch_SPX_1min_data.py --output_dir /data/spxdata --days 0 >> /var/log/cron.log 2>&1" > /etc/cron.d/spx_cron
RUN chmod 0644 /etc/cron.d/spx_cron

# Apply the cron job
RUN crontab /etc/cron.d/spx_cron

# Create log file
RUN touch /var/log/cron.log

# Set working directory
WORKDIR /app

# Command to run when container starts
CMD ["python", "fetch_xDTE_prices_with_IB_calculations_V2.py"]