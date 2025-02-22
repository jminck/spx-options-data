
## fetch_xDTE_prices_with_IB_calculations_V2.py

### Options Market Data Collector

A Python script for collecting and processing real-time options market data via the Tradier API. The script focuses on gathering comprehensive options chain data and calculating various derivative strategy values.

## Features

### Core Data Collection
- Real-time market prices for underlying symbol, VIX, and VIX1D
- Complete options chains for multiple expiration dates
- Configurable Days Till Expiration (DTE) range
- Data collection frequency: Every 25 seconds during market hours

### Market Calculations
- **Strategy Values:**
  - Straddle values
  - Iron Butterfly (IB) values (20-wide and 40-wide)
  - Vertical spread values (10-wide calls and puts)
- **Option Metrics:**
  - Intrinsic and extrinsic values
  - Greeks (Delta, Gamma, Theta, Vega, Rho, Phi)
  - Bid-ask spreads and midpoints

### Data Management
- Separate CSV files for each DTE
- Daily log rotation
- Organized output directory structure
- Comprehensive error handling and logging

### Market Hours Management
- Optional market hours checking (9:30 AM - 4:00 PM ET)
- Weekend and holiday handling
- Configurable market hours enforcement

## Installation

1. Clone the repository
2. Install required dependencies:

pip install requests pandas pytz

3. Create a `.api_key` file in the script directory with your Tradier API key

## Usage

python fetch_xDTE_prices_with_IB_calculations_V2.py


### Command Line Options
- `--symbol`: Trading symbol (default: SPX)
- `--dte_days`: Maximum DTE to collect (default: 7)
- `--output_dir`: Output directory (default: data2)
- `--check_market_hours`: Only collect during market hours

## Output Data

The script generates CSV files containing:

### Market Data
- Timestamp
- Symbol price
- VIX and VIX1D values

### Option Details
- Strike price and type
- Bid/Ask/Last prices
- Trading volume and open interest
- Option Greeks
- Contract specifications

### Calculated Values
- Straddle values
- Iron Butterfly values
- Vertical spread values
- Intrinsic/Extrinsic values

### Additional Metrics
- Market statistics
- Exchange information
- Trading volumes
- Price changes and percentages

## Logging

- Detailed logging system with both file and console output
- Daily log rotation
- Error tracking and debugging information

## Requirements
- Python 3.6+
- Tradier API key
- Required Python packages:
  - requests
  - pandas
  - pytz
  - logging


---



## fetch_SPX_1min_data.py

### Market Data Fetcher

A Python script for fetching and processing minute-by-minute market data from the Tradier API for specified market indices (SPX, VIX, VIX1D).

## Features

### Data Collection
- Fetches 1-minute interval market data for configured symbols
- Supports multiple trading days of historical data
- Handles market hours (9:30 AM - 4:15 PM ET)
- Validates complete trading days (ensures no missing minutes)

### Data Processing
- Converts timestamps to Eastern Time
- Processes OHLC (Open, High, Low, Close) prices
- Flags after-hours trading periods
- Validates data completeness for each trading day

### Data Management
- Saves data in CSV format
- Organizes files by symbol and date
- Marks files as 'complete' or 'partial' based on data coverage
- Creates separate files for each trading day

## Installation

1. Clone the repository
2. Install required dependencies:

pip install requests pandas pytz

3. Create a `.api_key` file in the script directory with your Tradier API key


### API Authentication
- Requires a Tradier API key stored in `.api_key` file
- File should be placed in the same directory as the script

## Usage

python fetch_SPX_1min_data.py [options]
Options:
--days INTEGER Number of trading days to fetch (default: 10)
--output_dir TEXT Output directory for CSV files (default: 'data')

## Output Format

### CSV Files
Files are named using the pattern: `{SYMBOL}_min_{DATE}_{STATUS}.csv`
- SYMBOL: Market symbol (e.g., SPX)
- DATE: Trading date (YYYYMMDD format)
- STATUS: 'complete' or 'partial'

### Data Columns
- Time: Timestamp in format 'YYYY-MM-DDTHH:MM:SS-0500'
- Symbol: Market symbol
- Price: Current price
- Open: Opening price
- High: High price
- Low: Low price
- Close: Closing price
- Afterhours: Binary flag (1 for after-hours, 0 for regular hours)

## Dependencies
- pandas
- requests
- pytz
- pandas_market_calendars
- logging
- pathlib

## Error Handling
- Comprehensive logging system
- API error handling
- Data validation checks
- Market calendar verification

## Market Hours
- Regular trading hours: 9:30 AM - 4:15 PM ET
- Handles market holidays using NYSE calendar
- Supports historical data retrieval
- Validates trading day completeness

## Logging
- Detailed logging of operations
- Error tracking and reporting
- Data validation messages
- Processing status updates

## Example Output

csv
Time,Symbol,Price,Open,High,Low,Close,Afterhours
2024-03-20T09:31:00-0500,SPX,5224.42,5224.42,5224.42,5224.42,5224.42,0
2024-03-20T09:32:00-0500,SPX,5225.16,5225.16,5225.16,5224.42,5225.16,0

## Functions Overview

### Main Functions

#### `fetch_all_available_data(output_dir: str, days_window: int = 0)`
Main function to fetch and process data for all configured symbols.

#### `fetch_market_data(symbol: str, start_date: str, end_date: str)`
Fetches raw market data from Tradier API.

#### `process_market_data(data: List[Dict], symbol: str)`
Processes raw API data into formatted DataFrame.

#### `is_complete_trading_day(df: pd.DataFrame, date: str)`
Validates if all minutes are present for a trading day.

### Helper Functions

#### `get_trading_dates_range(days_window: int)`
Calculates the date range for data collection.

#### `is_trading_day(date: datetime)`
Checks if a given date is a trading day.

#### `save_daily_data(df: pd.DataFrame, symbol: str, date: str, output_dir: str)`
Saves processed data to CSV files.

## Error Messages

Common error messages and their meanings:
- "API key file not found" - Missing `.api_key` file
- "No data found for {symbol}" - No data available for the specified period
- "Missing data for {date} at times" - Incomplete minute data for a trading day

## Troubleshooting

1. **Missing API Key**
   - Ensure `.api_key` file exists in script directory
   - Verify API key is valid and not expired

2. **No Data Retrieved**
   - Check if requested date is a trading day
   - Verify market hours for the requested period
   - Confirm symbol is valid and active

3. **Incomplete Data**
   - Check for market holidays or early closures
   - Verify API service status
   - Check for network connectivity issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request


## Docker Support

The repository includes Docker support files to run the Python scripts in a containerized environment, though this is optional and not required to use the scripts:

- `Dockerfile` - Defines the container image with Python and required dependencies
- `buildcontainer.sh` - Shell script to build and run the Docker container

## ELK Integration 

The following files enable pushing the scripts' output data to an ELK (Elasticsearch, Logstash, Kibana) cluster for visualization and analysis:

- `logstash.conf` - Logstash configuration for processing and forwarding data
- `*template.json` files - Elasticsearch index templates for mapping data fields

Using ELK integration is optional - by default the scripts will save data locally to CSV files.



