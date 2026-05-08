#!/usr/bin/env python3
"""
Improved volatility calculation with retry logic and better error handling
"""
import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def get_chinext_stocks():
    """Get all ChiNext (创业板) stock codes"""
    try:
        stock_info = ak.stock_info_a_code_name()
        chinext = stock_info[stock_info['code'].str.startswith('300')]
        return chinext['code'].tolist()
    except Exception as e:
        logger.error(f"Error getting stock list: {e}")
        return []

def calculate_volatility_with_retry(stock_code, end_date='2024-05-31', days=10, max_retries=3):
    """Calculate volatility for a stock with retry logic"""
    for attempt in range(max_retries):
        try:
            # Add small delay to avoid overwhelming the API
            time.sleep(0.1 * (attempt + 1))
            
            # Fetch historical data
            df = ak.stock_zh_a_hist(symbol=stock_code, period="daily", adjust="qfq")
            
            if df is None or len(df) == 0:
                continue
                
            df['日期'] = pd.to_datetime(df['日期'])
            
            # Filter data up to end_date
            end = pd.to_datetime(end_date)
            df = df[df['日期'] <= end].sort_values('日期', ascending=False)
            
            # Get last N days
            recent = df.head(days)
            
            if len(recent) < days:
                continue
            
            # Get closing prices
            closes = recent['收盘'].values
            
            # Calculate volatility (coefficient of variation)
            mean_price = np.mean(closes)
            std_price = np.std(closes, ddof=1)
            
            if mean_price == 0:
                continue
            
            volatility = (std_price / mean_price) * 100
            
            # Sanity check: volatility should be reasonable (0-100%)
            if volatility < 0 or volatility > 100:
                logger.warning(f"Unusual volatility for {stock_code}: {volatility:.2f}%")
            
            return {
                'code': stock_code,
                'volatility': volatility,
                'mean_price': mean_price,
                'std_price': std_price
            }
            
        except Exception as e:
            if attempt == max_retries - 1:
                logger.debug(f"Failed {stock_code} after {max_retries} attempts: {e}")
            continue
    
    return None

def main():
    end_date = '2024-05-31'
    days = 10
    
    logger.info(f"Getting ChiNext stock list...")
    stocks = get_chinext_stocks()
    logger.info(f"Found {len(stocks)} ChiNext stocks")
    
    if not stocks:
        logger.error("No stocks found, exiting")
        return
    
    # Calculate volatility for each stock with parallel processing
    results = []
    total = len(stocks)
    success_count = 0
    fail_count = 0
    
    logger.info("Starting parallel processing with retry logic...")
    
    # Use smaller batch size and more workers for better throughput
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(calculate_volatility_with_retry, code, end_date, days): code 
                   for code in stocks}
        
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result is not None:
                results.append(result)
                success_count += 1
            else:
                fail_count += 1
            
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{total}, Success: {success_count}, Failed: {fail_count}")
    
    logger.info(f"\nData collection complete: Success {success_count}, Failed {fail_count}")
    logger.info(f"Success rate: {success_count/total*100:.1f}%")
    
    if len(results) == 0:
        logger.error("No valid data collected!")
        return
    
    # Sort by volatility descending
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('volatility', ascending=False)
    
    # Get top 5
    top5 = results_df.head(5)
    
    logger.info("\nTop 5 stocks by volatility:")
    for _, row in top5.iterrows():
        logger.info(f"  {row['code']}: {row['volatility']:.2f}% (mean={row['mean_price']:.2f}, std={row['std_price']:.2f})")
    
    # Write to file
    output_file = 'volatility_top5.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('股票代码,波动率(%)\n')
        for _, row in top5.iterrows():
            f.write(f"{row['code']},{row['volatility']:.2f}\n")
    
    logger.info(f"\nResults written to {output_file}")
    
    # Additional statistics
    logger.info(f"\nStatistics across all {len(results)} stocks:")
    logger.info(f"  Mean volatility: {results_df['volatility'].mean():.2f}%")
    logger.info(f"  Median volatility: {results_df['volatility'].median():.2f}%")
    logger.info(f"  Max volatility: {results_df['volatility'].max():.2f}%")
    logger.info(f"  Min volatility: {results_df['volatility'].min():.2f}%")

if __name__ == '__main__':
    main()
