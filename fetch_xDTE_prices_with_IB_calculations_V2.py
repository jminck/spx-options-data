import requests
from datetime import datetime, date, timedelta, time as dt_time
import pandas as pd
import logging
from logging.handlers import TimedRotatingFileHandler
import time
import os
import pytz
import csv

def load_api_key():
    """Load API key from .api_key file in script directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    api_key_path = os.path.join(script_dir, '.api_key')
    
    try:
        with open(api_key_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"API key file not found. Please create {api_key_path} with your Tradier API key")
    except Exception as e:
        raise Exception(f"Error reading API key: {str(e)}")

class MarketDataCollector:
    def __init__(self, api_key, symbol='SPX', max_dte=3, output_dir='data', check_market_hours=True):
        self.api_key = api_key
        self.symbol = symbol
        self.max_dte = max_dte
        self.output_dir = output_dir
        self.check_market_hours = check_market_hours
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Accept': 'application/json'
        }
        self.base_url = 'https://api.tradier.com/v1/markets'
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize CSV files
        self._setup_csv_files()

    def _setup_logging(self):
        """Setup logging to both file and console"""
        today = date.today().strftime('%Y%m%d')
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        log_file = f'{log_dir}/market_data_{today}.log'
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File handler
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        self.logger = logging.getLogger('MarketDataCollector')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicate logs
        self.logger.handlers = []
        
        # Add both handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _setup_csv_files(self):
        """Setup CSV files with headers for each DTE"""
        current_date = date.today().strftime('%Y%m%d')
        headers = [
            'Time', 'Symbol', 'Price', 'VIX', 'VIX1D',
            'Option', 'Type', 'Strike Price',
            'Last Price', 'Bid', 'Ask', 'Mid', 'Width',
            'Expiration', 'DTE', 'Straddle Value', 'ATM',
            '20-Wide IB Value', '40-Wide IB Value',
            '10-Wide Call Spread', '10-Wide Put Spread',
            'Delta', 'Gamma', 'Theta', 'Vega', 'Rho', 'Phi',
            'Description', 'Exchange',
            'Change', 'Volume', 'Open', 'High', 'Low', 'Close',
            'Change Percentage', 'Average Volume', 'Last Volume',
            'Trade Date', 'Prev Close', 'Week 52 High', 'Week 52 Low',
            'Bid Size', 'Bid Exchange', 'Bid Date',
            'Ask Size', 'Ask Exchange', 'Ask Date',
            'Open Interest', 'Contract Size', 'Expiration Type',
            'Root Symbol', 'Intrinsic Value', 'Extrinsic Value'
        ]
        
        for dte in range(0, self.max_dte + 1):
            filename = f"{self.symbol}_{dte}DTE_{current_date}.csv"
            filepath = os.path.join(self.output_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)

    def is_market_open(self):
        """Check if the market is currently open"""
        if not self.check_market_hours:
            print("Market hours check is disabled - collecting data")
            return True
            
        et_tz = pytz.timezone('US/Eastern')
        now = datetime.now(et_tz)
        
        # Check if it's a weekday
        if now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            self.logger.info("Market closed - Weekend")
            return False
            
        # Market hours: 9:30 AM - 4:00 PM ET
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        if market_open <= now <= market_close:
            return True
        else:
            self.logger.info("Market closed - Outside trading hours")
            return False

    def get_market_data(self):
        """Fetch current market data for symbol, VIX, and VIX1D"""
        url = f'{self.base_url}/quotes'
        params = {'symbols': f'{self.symbol},VIX,VIX1D'}
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        quotes = response.json()['quotes']['quote']
        return {quote['symbol']: quote for quote in quotes}

    def get_options_chain(self, expiration_date):
        """Fetch options chain for a specific expiration date"""
        url = f'{self.base_url}/options/chains'
        params = {
            'symbol': self.symbol,
            'expiration': expiration_date.strftime('%Y-%m-%d'),
            'greeks': 'true'
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'options' not in data or data['options'] is None:
                self.logger.error(f"No options data available for {expiration_date}")
                return None
                
            return data['options'].get('option', [])
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error fetching options chain: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"Error parsing options chain: {e}")
            return None

    def calculate_spread_value(self, option_buffer, current_strike, width, option_type='call'):
        """Calculate vertical spread value"""
        try:
            if option_type == 'call':
                higher_strike = current_strike + width
                if (current_strike in option_buffer and 
                    higher_strike in option_buffer and 
                    option_buffer[current_strike]['call'] and 
                    option_buffer[higher_strike]['call']):
                    
                    current_mid = option_buffer[current_strike]['call']['mid']
                    higher_mid = option_buffer[higher_strike]['call']['mid']
                    return round(current_mid - higher_mid, 2)
                    
            elif option_type == 'put':
                lower_strike = current_strike - width
                if (current_strike in option_buffer and 
                    lower_strike in option_buffer and 
                    option_buffer[current_strike]['put'] and 
                    option_buffer[lower_strike]['put']):
                    
                    current_mid = option_buffer[current_strike]['put']['mid']
                    lower_mid = option_buffer[lower_strike]['put']['mid']
                    return round(current_mid - lower_mid, 2)
        except Exception as e:
            self.logger.warning(f"Error calculating spread value: {str(e)}")
        
        return None

    def calculate_ib_value(self, option_buffer, strike_price, width):
        """Calculate iron butterfly value"""
        try:
            if (strike_price in option_buffer and 
                strike_price + width in option_buffer and 
                strike_price - width in option_buffer):
                
                center_call = option_buffer[strike_price]['call']['mid']
                center_put = option_buffer[strike_price]['put']['mid']
                
                wing_call = option_buffer[strike_price + width]['call']['mid']
                wing_put = option_buffer[strike_price - width]['put']['mid']
                
                if all(x is not None for x in [center_call, center_put, wing_call, wing_put]):
                    return round(center_call + center_put - wing_call - wing_put, 2)
        except Exception as e:
            self.logger.warning(f"Error calculating IB value: {str(e)}")
        
        return None

    def safe_float(self, value, default=0.0):
        """Safely convert value to float, handling None and empty strings"""
        if value in [None, 'None', '', 'N/A']:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def safe_int(self, value, default=0):
        """Safely convert value to int, handling None and empty strings"""
        if value in [None, 'None', '', 'N/A']:
            return default
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default
    def process_options_data(self, options_data, market_data, expiration_date):
        """Process options data and calculate metrics"""
        current_time = datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')
        
        # Validate market data
        try:
            current_price = float(market_data[self.symbol]['last'])
            vix = float(market_data.get('VIX', {}).get('last', 0))
            vix1d = float(market_data.get('VIX1D', {}).get('last', 0))
        except (KeyError, TypeError, ValueError) as e:
            self.logger.error(f"Invalid market data: {str(e)}")
            self.logger.debug(f"Market data received: {market_data}")
            return None
            
        if not options_data:
            self.logger.warning(f"No options data available for {expiration_date}")
            return None
        
        # Buffer to store options data
        option_buffer = {}
        straddle_values = {}
        atm_strike = None
        min_diff = float('inf')
        
        # First pass: organize options by strike
        for option in options_data:
            try:
                strike_price = float(option.get('strike', 0))
                option_type = option.get('option_type', '').lower()
                
                if strike_price not in option_buffer:
                    option_buffer[strike_price] = {'put': None, 'call': None}
                
                bid = float(option.get('bid', 0)) if option.get('bid') is not None else 0
                ask = float(option.get('ask', 0)) if option.get('ask') is not None else 0
                mid = round((bid + ask) / 2, 2) if bid > 0 or ask > 0 else 0
                
                option_buffer[strike_price][option_type] = {
                    'option': option,
                    'mid': mid
                }
                
                if abs(strike_price - current_price) < min_diff:
                    min_diff = abs(strike_price - current_price)
                    atm_strike = strike_price
            except Exception as e:
                self.logger.debug(f"Skipping option {option.get('symbol', 'unknown')} in first pass: {str(e)}")
                continue
        
        # Second pass: calculate metrics and prepare rows
        processed_data = []
        for option in options_data:
            try:
                strike_price = float(option.get('strike', 0))
                
                # Calculate various spread values
                ib_value_20 = self.calculate_ib_value(option_buffer, strike_price, 20)
                ib_value_40 = self.calculate_ib_value(option_buffer, strike_price, 40)
                call_spread_10 = self.calculate_spread_value(option_buffer, strike_price, 10, 'call')
                put_spread_10 = self.calculate_spread_value(option_buffer, strike_price, 10, 'put')
                
                # Calculate straddle value
                straddle_value = None
                if strike_price in option_buffer:
                    call_data = option_buffer[strike_price]['call']
                    put_data = option_buffer[strike_price]['put']
                    if call_data and put_data:
                        straddle_value = round(call_data['mid'] + put_data['mid'], 2)
                
                # Calculate mid and width
                bid = float(option.get('bid', 0)) if option.get('bid') is not None else 0
                ask = float(option.get('ask', 0)) if option.get('ask') is not None else 0
                mid = round((bid + ask) / 2, 2) if bid > 0 or ask > 0 else 0
                width = round(ask - bid, 2) if bid > 0 or ask > 0 else 0
                
                # Prepare row data with matching field names
                row_data = {
                    'Time': current_time,
                    'Symbol': self.symbol,
                    'Price': round(current_price, 2),
                    'VIX': round(vix, 2),
                    'VIX1D': round(vix1d, 2),
                    'Option': option.get('symbol', 'N/A'),
                    'Type': option.get('option_type', 'N/A'),
                    'Strike Price': round(strike_price, 2),
                    'Last Price': round(float(option.get('last', 0)) if option.get('last') is not None else 0, 2),
                    'Bid': round(bid, 2),
                    'Ask': round(ask, 2),
                    'Mid': mid,
                    'Width': width,
                    'Expiration': expiration_date.strftime('%Y-%m-%d'),
                    'DTE': (expiration_date - date.today()).days,
                    'Straddle Value': straddle_value if straddle_value is not None else 0.00,
                    'ATM': 1 if strike_price == atm_strike else 0,
                    '20-Wide IB Value': ib_value_20 if ib_value_20 is not None else 0.00,
                    '40-Wide IB Value': ib_value_40 if ib_value_40 is not None else 0.00,
                    '10-Wide Call Spread': call_spread_10 if call_spread_10 is not None else 0.00,
                    '10-Wide Put Spread': put_spread_10 if put_spread_10 is not None else 0.00
                }
                
                # Add greeks with rounding and error handling
                greeks = option.get('greeks', {})
                if greeks:
                    try:
                        row_data.update({
                            'Delta': round(float(greeks.get('delta', 0)), 2),
                            'Gamma': round(float(greeks.get('gamma', 0)), 2),
                            'Theta': round(float(greeks.get('theta', 0)), 2),
                            'Vega': round(float(greeks.get('vega', 0)), 2),
                            'Rho': round(float(greeks.get('rho', 0)), 2),
                            'Phi': round(float(greeks.get('phi', 0)), 2)
                        })
                    except (ValueError, TypeError):
                        row_data.update({
                            'Delta': 0.00,
                            'Gamma': 0.00,
                            'Theta': 0.00,
                            'Vega': 0.00,
                            'Rho': 0.00,
                            'Phi': 0.00
                        })
                else:
                    row_data.update({
                        'Delta': 0.00,
                        'Gamma': 0.00,
                        'Theta': 0.00,
                        'Vega': 0.00,
                        'Rho': 0.00,
                        'Phi': 0.00
                    })
                
                # Add additional fields with matching names and proper rounding
                row_data.update({
                    'Description': option.get('description', 'N/A'),
                    'Exchange': option.get('exchange', 'N/A'),
                    'Change': round(float(option.get('change')) if option.get('change') is not None else 0, 2),
                    'Volume': int(float(option.get('volume')) if option.get('volume') is not None else 0),
                    'Open': round(float(option.get('open')) if option.get('open') is not None else 0, 2),
                    'High': round(float(option.get('high')) if option.get('high') is not None else 0, 2), 
                    'Low': round(float(option.get('low')) if option.get('low') is not None else 0, 2),
                    'Close': round(float(option.get('close')) if option.get('close') is not None else 0, 2),
                    'Change Percentage': round(float(option.get('change_percentage')) if option.get('change_percentage') is not None else 0, 2),
                    'Average Volume': int(float(option.get('average_volume')) if option.get('average_volume') is not None else 0),
                    'Last Volume': int(float(option.get('last_volume')) if option.get('last_volume') is not None else 0),
                    'Trade Date': option.get('trade_date', 'N/A'),
                    'Prev Close': round(float(option.get('prevclose')) if option.get('prevclose') is not None else 0, 2),
                    'Week 52 High': round(float(option.get('week_52_high')) if option.get('week_52_high') is not None else 0, 2),
                    'Week 52 Low': round(float(option.get('week_52_low')) if option.get('week_52_low') is not None else 0, 2),
                    'Bid Size': int(float(option.get('bid_size')) if option.get('bid_size') is not None else 0),
                    'Bid Exchange': option.get('bid_exchange', 'N/A'),
                    'Bid Date': option.get('bid_date', 'N/A'),
                    'Ask Size': int(float(option.get('ask_size')) if option.get('ask_size') is not None else 0),
                    'Ask Exchange': option.get('ask_exchange', 'N/A'),
                    'Ask Date': option.get('ask_date', 'N/A'),
                    'Open Interest': int(float(option.get('open_interest')) if option.get('open_interest') is not None else 0),
                    'Contract Size': int(float(option.get('contract_size')) if option.get('contract_size') is not None else 100),
                    'Expiration Type': option.get('expiration_type', 'N/A'),
                    'Root Symbol': option.get('root_symbol', 'N/A')
                })
                
                # Calculate intrinsic and extrinsic values
                try:
                    intrinsic_value = max(0, current_price - strike_price) if option['option_type'].lower() == 'call' else max(0, strike_price - current_price)
                    mid_price = row_data['Mid'] if isinstance(row_data['Mid'], (int, float)) else 0
                    extrinsic_value = max(0, mid_price - intrinsic_value)
                except (TypeError, ValueError):
                    intrinsic_value = 0
                    extrinsic_value = 0
                
                row_data.update({
                    'Intrinsic Value': round(intrinsic_value, 2),
                    'Extrinsic Value': round(extrinsic_value, 2)
                })
                
                processed_data.append(row_data)
                
            except Exception as e:
                self.logger.debug(f"Error processing option {option.get('symbol', 'unknown')}: {str(e)}")
                continue
        
        if not processed_data:
            self.logger.warning(f"No valid options data processed for {expiration_date}")
            return None
            
        return processed_data  
    def save_data(self, data, dte, current_date):
        """Save processed data to CSV"""
        filename = f"{self.symbol}_{dte}DTE_{current_date.strftime('%Y%m%d')}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            writer.writerows(data)
        
        self.logger.info(f"Saved data to {filepath}")

    def run(self):
        last_date = None
        
        while True:
            try:
                current_date = date.today()
                
                # Check if date has changed and reset logger and CSV files
                if last_date != current_date:
                    self._setup_logging()
                    self._setup_csv_files()
                    last_date = current_date
                
                # Check if market is open
                if not self.is_market_open():
                    time.sleep(60)
                    print("Market is closed - sleeping")
                    continue
                
                # Fetch market data once per loop
                market_data = self.get_market_data()
                self.logger.info(f"Fetched market data: {self.symbol}={market_data[self.symbol]['last']}, "
                            f"VIX={market_data['VIX']['last']}, "
                            f"VIX1D={market_data.get('VIX1D', {}).get('last', 'N/A')}")
                
                # Process each DTE starting from 0
                for dte in range(0, self.max_dte + 1):  # Changed to start from 0
                    try:
                        expiration_date = date.today() + timedelta(days=dte)
                        options_data = self.get_options_chain(expiration_date)
                        
                        if options_data is None:
                            self.logger.warning(f"Skipping DTE {dte} due to missing options data")
                            continue
                            
                        processed_data = self.process_options_data(options_data, market_data, expiration_date)
                        if processed_data:  # Only save if we have data
                            self.save_data(processed_data, dte, current_date)
                    except Exception as e:
                        self.logger.error(f"Error processing DTE {dte}: {str(e)}")
                
                # Wait for next update
                time.sleep(25)  # Adjust frequency as needed
                
            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                time.sleep(25)  # Wait before retrying

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', type=str, default='SPX')
    parser.add_argument('--dte_days', type=int, default=7)
    parser.add_argument('--output_dir', type=str, default='data2')
    parser.add_argument('--check_market_hours', action='store_true', default=False,
                       help='Collect data only when market is open (default: True - will only collect during market hours)')
    
    args = parser.parse_args()
    
    # Load API key from file
    api_key = load_api_key()
    
    collector = MarketDataCollector(
        api_key=api_key,
        symbol=args.symbol,
        max_dte=args.dte_days,
        output_dir=args.output_dir,
        check_market_hours=args.check_market_hours
    )
    
    collector.run()