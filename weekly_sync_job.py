import schedule
import time
import os
import logging
from dotenv import load_dotenv

from scraper import fetch_and_parse_data
from google_sheets_writer import write_weekly_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# List of hubs to sync
HUBS = [
    "oskemen.hub", "astana.hub", "almaty_hub", "terriconvalley", "shymkent__hub", 
    "batys.hub", "turkistan.hub", "zhambyl_hub", "jetisu_digital", "sko_hub", 
    "abai_it", "pavlodar.hub", "kyzylordahub", "qostanai.hub", "alatau.hub", 
    "aqmola.hub", "ulytau.hub", "atyrau_it_hub", "aqtobe.hub", "mangystau.hub"
]

def job():
    logging.info("Starting weekly Instagram analytics sync...")
    api_key = os.environ.get("RAPIDAPI_KEY")
    
    if not api_key:
        logging.error("RAPIDAPI_KEY is not set. Aborting sync.")
        return

    for hub in HUBS:
        logging.info(f"Fetching data for {hub}...")
        try:
            result = fetch_and_parse_data(hub, api_key)
            if result.get("error"):
                logging.warning(f"Error fetching {hub}: {result['error']}")
                continue
            
            sync_payload = result["sync_payload"]
            
            logging.info(f"Writing data to Google Sheets for {hub}...")
            write_weekly_data(sync_payload)
            logging.info(f"Successfully synced {hub}.")
            
            # Sleep briefly to avoid hitting API rate limits
            time.sleep(2)
            
        except Exception as e:
            logging.error(f"Failed to process {hub}: {e}")

    logging.info("Weekly sync completed.")

if __name__ == "__main__":
    logging.info("Scheduling weekly sync for every Monday at 10:50 AM (Almaty time).")
    schedule.every().monday.at("9:20", "Asia/Almaty").do(job)

    # Infinite loop to keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60) # Check every minute
