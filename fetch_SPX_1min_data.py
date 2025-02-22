import pandas_market_calendars as mcal
import requests
import logging
from datetime import datetime, timedelta
import pytz
import pandas as pd
import os
from typing import List, Dict
from pathlib import Path
import json

# Setup logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
log_file = f'{log_dir}/market_data_{datetime.now().strftime("%Y%m%d")}.log'

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Setup file handler
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)

# Setup console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Configuration

BASE_URL = 'https://api.tradier.com/v1/markets'

SYMBOLS = {
    'SPX': 'S&P 500 Index',
    'VIX': 'Volatility Index',
    'VIX1D': '1-Day VIX'
}

# Add this at the top of the script, after the imports
def load_api_key() -> str:
    """
    Load API key from .api_key file in the script's directory
    """
    try:
        # Get the directory where the script is located
        script_dir = Path(__file__).parent.absolute()
        api_key_path = script_dir / '.api_key'
        
        # Read API key from file
        with open(api_key_path, 'r') as f:
            api_key = f.read().strip()
            
        if not api_key:
            raise ValueError("API key file is empty")
            
        return api_key
        
    except FileNotFoundError:
        logger.error(f"API key file not found. Please create .api_key file in {script_dir}")
        raise
    except Exception as e:
        logger.error(f"Error reading API key: {e}")
        raise

# Replace the API_KEY constant with this
try:
    API_KEY = load_api_key()
except Exception as e:
    logger.error("Failed to load API key. Exiting.")
    exit(1)
    
def is_complete_trading_day(df: pd.DataFrame, date: str) -> bool:
    """
    Check if we have data for every minute between 9:30-16:15 EST for a given date.
    If incomplete, prints the missing minutes.
    """
    # Expected number of minutes (6 hours and 45 minutes = 405 minutes)
    EXPECTED_MINUTES = 404
    
    # Filter data for the given date
    day_data = df[df['Time'].str.startswith(date)]
    
    # Generate expected times
    start_time = pd.Timestamp(f"{date} 09:31:00-0500")
    expected_times = pd.date_range(start_time, periods=EXPECTED_MINUTES, freq='1min')
    expected_times = expected_times.strftime('%Y-%m-%dT%H:%M:%S-0500').tolist()
    
    # Get actual times
    actual_times = day_data['Time'].tolist()
    
    # Find missing times
    missing_times = set(expected_times) - set(actual_times)
    
    if missing_times:
        logger.warning(f"Missing data for {date} at times:")
        for time in sorted(missing_times):
            logger.warning(f"  {time}")
        return False
        
    return True

def fetch_market_data(symbol: str, start_date: str, end_date: str) -> List[Dict]:
    """
    Fetch market data for a given symbol and date range
    """
    try:
        params = {
            'symbol': symbol,
            'interval': '1min',
            'start': start_date,
            'end': end_date,
            'session_filter': 'all'
        }
        
        response = requests.get(
            f'{BASE_URL}/timesales',
            params=params,
            headers={'Authorization': f'Bearer {API_KEY}', 'Accept': 'application/json'},
            timeout=30
        )
        
        response.raise_for_status()
        data = response.json()
        
        if 'series' in data and 'data' in data['series']:
            return data['series']['data']
        logger.warning(f"No data found for {symbol}")
        return []
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return []

def process_market_data(data: List[Dict], symbol: str) -> pd.DataFrame:
    """
    Process raw market data into a formatted DataFrame
    """
    if not data:
        return pd.DataFrame()
    
    try:
        df = pd.DataFrame(data)
        
        # Debug logging
        logger.info(f"Received columns: {df.columns.tolist()}")
        
        # Convert time to datetime with timezone
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize('US/Eastern')
        
        # Format time as specified
        df['Time'] = df['time'].dt.strftime('%Y-%m-%dT%H:%M:%S-0500')
        
        # Add Symbol column
        df['Symbol'] = symbol
        
        # Add Price column (using close price)
        df['Price'] = df['close'] if 'close' in df.columns else None
        
        # Ensure all required columns exist
        for col in ['open', 'high', 'low', 'close']:
            if col not in df.columns:
                df[col] = None
        
        # Add Afterhours column
        df['hour'] = df['time'].dt.hour
        df['minute'] = df['time'].dt.minute
        df['time_value'] = df['hour'] * 100 + df['minute']
        df['Afterhours'] = ((df['time_value'] < 930) | (df['time_value'] > 1615)).astype(int)
        
        # Drop temporary columns
        df = df.drop(['hour', 'minute', 'time_value'], axis=1)
        
        # Select and rename columns
        result_df = pd.DataFrame()
        result_df['Time'] = df['Time']
        result_df['Symbol'] = df['Symbol']
        result_df['Price'] = df['Price']
        result_df['Open'] = df['open']
        result_df['High'] = df['high']
        result_df['Low'] = df['low']
        result_df['Close'] = df['close']
        result_df['Afterhours'] = df['Afterhours']
        
        # Convert price columns to float
        price_columns = ['Price', 'Open', 'High', 'Low', 'Close']
        for col in price_columns:
            result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
        
        return result_df
        
    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        logger.error(f"Data sample: {data[:1] if data else 'No data'}")
        raise
def get_trading_date(days_ago: int) -> tuple[str, str]:
    """
    Get the trading date range for a specific day
    Args:
        days_ago (int): Number of days ago (1 = today, 2 = yesterday, etc.)
    Returns:
        tuple: (start_time, end_time) in format 'YYYY-MM-DD HH:MM'
    """
    et_tz = pytz.timezone('US/Eastern')
    current_date = datetime.now(et_tz)
    target_date = current_date - timedelta(days=days_ago-1)
    
    # Format dates
    date_str = target_date.strftime('%Y-%m-%d')
    start_time = f"{date_str} 09:30"
    end_time = f"{date_str} 16:15"
    
    return start_time, end_time

def is_trading_day(date: datetime) -> bool:
    """
    Check if the given date is a trading day
    """
    nyse = mcal.get_calendar('NYSE')
    schedule = nyse.schedule(start_date=date.date(), end_date=date.date())
    return len(schedule) > 0

def get_last_trading_day() -> datetime:
    """
    Get the most recent trading day
    """
    nyse = mcal.get_calendar('NYSE')
    et_tz = pytz.timezone('US/Eastern')
    current_date = datetime.now(et_tz)
    
    # Get the last 10 trading days (more than enough to find the last one)
    schedule = nyse.schedule(
        start_date=current_date - timedelta(days=10),
        end_date=current_date
    )
    
    if schedule.empty:
        raise ValueError("Could not find recent trading day")
        
    return schedule.index[-1].to_pydatetime().replace(tzinfo=et_tz)

def get_trading_dates_range(days_window: int) -> tuple[str, str]:
    """
    Get the trading date range for a window of days
    Args:
        days_window (int): Number of trading days to fetch (0 = today only, 1 = today and yesterday, etc.)
    Returns:
        tuple: (start_time, end_time) in format 'YYYY-MM-DD HH:MM'
    """
    et_tz = pytz.timezone('US/Eastern')
    current_date = datetime.now(et_tz)
    
    # Check if current date is a trading day
    if not is_trading_day(current_date):
        current_date = get_last_trading_day()
        logger.info(f"Current date is not a trading day. Using last trading day: {current_date.date()}")
    
    nyse = mcal.get_calendar('NYSE')
    
    if days_window == 0:
        # Just get the single trading day
        date_str = current_date.strftime('%Y-%m-%d')
        start_time = f"{date_str} 09:30"
        end_time = f"{date_str} 16:15"
    else:
        # Get schedule for a larger window to ensure we have enough trading days
        calendar_days = min(days_window * 2, 30)  # Double the days to account for weekends/holidays
        start_date = current_date - timedelta(days=calendar_days)
        
        schedule = nyse.schedule(start_date=start_date, end_date=current_date)
        trading_days = schedule.index[-days_window:] if len(schedule) >= days_window else schedule.index
        
        if len(trading_days) == 0:
            raise ValueError("No trading days found in the specified range")
            
        start_time = f"{trading_days[0].strftime('%Y-%m-%d')} 09:30"
        end_time = f"{trading_days[-1].strftime('%Y-%m-%d')} 16:15"
    
    logger.info(f"Calculating data range for {days_window} trading days:")
    logger.info(f"Current ET time: {current_date}")
    logger.info(f"Date range: {start_time} to {end_time}")
    
    return start_time, end_time

def fetch_all_available_data(output_dir: str, days_window: int = 0):
    """
    Fetch all available data for all symbols for a window of trading days
    """
    os.makedirs(output_dir, exist_ok=True)

    try:
        start_str, end_str = get_trading_dates_range(days_window)
    except ValueError as e:
        logger.error(f"Error with date range: {e}")
        return
    
    for symbol in SYMBOLS:
        logger.info(f"Fetching {symbol} ({SYMBOLS[symbol]}) data from {start_str} to {end_str}")
        
        # Fetch and process data
        raw_data = fetch_market_data(symbol, start_str, end_str)
        if raw_data:  # Add this check
            df = process_market_data(raw_data, symbol)
            
            if not df.empty:
                # Get unique dates in the data
                dates = sorted(df['Time'].str[:10].unique())
                
                # Log the actual trading days found
                logger.info(f"Found data for {len(dates)} trading days:")
                for date in dates:
                    logger.info(f"  - {date}")
                
                # Save separate file for each date
                for date in dates:
                    save_daily_data(df, symbol, date, output_dir)
            else:
                logger.warning(f"No data available for {symbol}")
        else:
            logger.warning(f"No raw data returned for {symbol}")

def save_daily_data(df: pd.DataFrame, symbol: str, date: str, output_dir: str):
    """
    Save data for a single day with appropriate filename
    """
    # Format date for filename
    date_formatted = date.replace('-', '')
    
    # Check if data is complete
    is_complete = is_complete_trading_day(df, date)
    
    # Create filename
    filename = f"{symbol}_min_{date_formatted}_{'complete' if is_complete else 'partial'}.ndjson"
    filepath = os.path.join(output_dir, filename)
    
    # Filter data for this date
    day_data = df[df['Time'].str.startswith(date)]
    
    # Convert DataFrame to list of dictionaries and save as NDJSON
    with open(filepath, 'w') as f:
        for record in day_data.to_dict('records'):
            f.write(json.dumps(record) + '\n')
    
    logger.info(f"Saved {len(day_data)} records to {filename} ({'complete' if is_complete else 'partial'})")



def main():
    # Get days window from command line argument, default to 0 (today only)
    import argparse
    parser = argparse.ArgumentParser(description='Fetch market data')
    parser.add_argument('--days', type=int, default=10, 
                      help='Number of trading days to fetch (0=today only, 10=last 10 trading days, etc.)')
    parser.add_argument('--output_dir', type=str, default='data2')
    args = parser.parse_args()
    
    # Create a specific directory for this run
    output_dir = args.output_dir
    
    try:
        fetch_all_available_data(output_dir, args.days)
        logger.info("Successfully processed all market data")
    except Exception as e:
        logger.error(f"Error processing market data: {e}")

if __name__ == "__main__":
    main()