import logging
from datetime import datetime
from data_fetch import fetch_btc_usdt_data
from strategy import sma_crossover_strategy

def main():
    """
    Main function to orchestrate the trading bot.
    Fetches data, applies strategy, and prints last 5 recommended actions.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    try:
        logging.info("Starting trading bot...")
        
        data = fetch_btc_usdt_data()
        logging.info(f"Fetched {len(data)} data points")
        
        signals = sma_crossover_strategy(data)
        logging.info(f"Generated {len(signals)} trading signals")
        
        print("\n=== Trading Bot Results ===")
        print(f"Total signals generated: {len(signals)}")
        
        if signals:
            print("\nLast 5 recommended actions:")
            last_5_signals = signals[-5:]
            for i, signal in enumerate(last_5_signals, 1):
                timestamp = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                action = signal['action'].upper()
                print(f"{i}. {timestamp} - {action}")
        else:
            print("No trading signals generated with current data.")
            
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()

