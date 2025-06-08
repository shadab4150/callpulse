import pandas as pd
import os
import joblib

DICT_CACHE_PATH = "symbol_to_name.joblib"
CSV_PATH = "stock-tickers.csv"

def load_data():
    # Check if serialized dictionary already exists
    if os.path.exists(DICT_CACHE_PATH):
        # Load the dictionary directly
        return joblib.load(DICT_CACHE_PATH)
    else:
        # Create dictionary from CSV and save for future use
        df = pd.read_csv(CSV_PATH)
        symbol_to_name = df.set_index('Symbol')['Name'].to_dict()
        joblib.dump(symbol_to_name, DICT_CACHE_PATH)
        return symbol_to_name

# Load the dictionary just once
symbol_to_name = load_data()

def get_company_name(ticker):
    ticker = ticker.upper()
    return symbol_to_name.get(ticker, ticker)