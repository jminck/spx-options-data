FROM python:3.11-slim

# Install required packages
COPY requirements.txt .
RUN pip install -r requirements.txt

# Create directory for the mounted data
RUN mkdir -p /data/spxdata

# Set working directory
WORKDIR /app

# Default command (overridden by container)
CMD ["python3", "fetch_SPX_1min_data-csv.py"]
